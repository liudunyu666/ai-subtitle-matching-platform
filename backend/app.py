import json
import os
import uuid
import hashlib
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from config import Config
from models.db import SessionLocal, engine, Base, Task, Material, init_db
from services.segmentation_service import split_by_punctuation, extract_keywords_tfidf
from services.matching_service import match_materials
from services.asr_service import transcribe as asr_transcribe

# ─── Lifespan ──────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), "static"), exist_ok=True)
    seed_materials_if_empty()
    yield

app = FastAPI(title="AI 字幕分析与素材匹配平台", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

executor = ThreadPoolExecutor(max_workers=Config.MAX_WORKERS)
_active_futures = {}

ALLOWED_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "mp3", "wav", "m4a", "ogg", "jpg", "jpeg", "png", "gif", "webp"}

# ─── Helpers ───────────────────────────────────────────────────────────


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def file_md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def json_resp(code=0, data=None, msg=""):
    return {"code": code, "data": data, "msg": msg}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def process_task_background(task_id):
    deadline = time.time() + Config.TASK_TIMEOUT

    def check_timeout():
        if time.time() > deadline:
            raise TimeoutError(f"Task timed out after {Config.TASK_TIMEOUT}s")

    try:
        session = SessionLocal()
        task = session.get(Task, task_id)
        if not task:
            session.close()
            return

        task.status = "processing"
        task.progress = 10
        task.error_msg = None
        session.commit()
        check_timeout()

        if task.file_path and os.path.exists(task.file_path):
            try:
                text = asr_transcribe(task.file_path, Config.OPENAI_API_KEY, Config.DASHSCOPE_API_KEY, Config.PUBLIC_BASE_URL)
            except Exception as e:
                print(f"ASR failed, switching to fallback: {e}")
                task.error_msg = str(e)
                session.commit()
                text = ""
            task.progress = 40
        else:
            text = ""
        check_timeout()

        raw = task.raw_text or ""
        final_text = text or raw
        if not final_text.strip():
            msg = task.error_msg or "No subtitle text available. Use the paste-text option."
            raise ValueError(msg)

        task.progress = 50
        session.commit()
        check_timeout()

        segments = split_by_punctuation(final_text)
        if not segments or len(segments) == 0:
            segments = [
                {
                    "id": "seg_0",
                    "text": final_text[:200],
                    "keywords": extract_keywords_tfidf(final_text),
                }
            ]

        task.progress = 70
        session.commit()
        check_timeout()

        for seg in segments:
            candidates = match_materials(seg.get("keywords", []), top_k=3)
            seg["candidates"] = candidates
            seg["selected_material_id"] = None
        check_timeout()

        task.progress = 90
        session.commit()

        try:
            from services.llm_service import llm_segmentation

            llm_result = llm_segmentation(final_text, Config.OPENAI_API_KEY)
            if llm_result and len(llm_result) > 1:
                for seg in llm_result:
                    candidates = match_materials(seg.get("keywords", []), top_k=3)
                    seg["candidates"] = candidates
                    seg["selected_material_id"] = None
                segments = llm_result
        except Exception:
            pass
        check_timeout()

        task.result = json.dumps(segments, ensure_ascii=False)
        task.status = "completed"
        task.progress = 100
        session.commit()
        session.close()

    except Exception as e:
        try:
            session = SessionLocal()
            task = session.get(Task, task_id)
            if task:
                task.status = "failed"
                task.error_msg = str(e)
                session.commit()
            session.close()
        except Exception:
            pass


# ─── Routes ────────────────────────────────────────────────────────────


@app.post("/api/tasks")
async def create_task(text: str = Form(""), file: UploadFile = File(None)):
    if not file and not text.strip():
        return JSONResponse(status_code=400, content=json_resp(1, msg="Please upload a file or paste subtitle text"))

    task = Task()
    task.status = "pending"
    task.raw_text = text

    if file and allowed_file(file.filename):
        ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else ""
        safe_name = f"{uuid.uuid4().hex}.{ext}"
        upload_path = os.path.join(Config.UPLOAD_FOLDER, safe_name)
        content = await file.read()
        with open(upload_path, "wb") as f:
            f.write(content)
        task.file_name = file.filename
        task.file_path = upload_path
        task.file_md5 = file_md5(upload_path)
    elif file and not allowed_file(file.filename):
        return JSONResponse(status_code=400, content=json_resp(1, msg=f"File type not allowed: {file.filename}"))

    if text.strip():
        task.text_md5 = hashlib.md5(text.encode("utf-8")).hexdigest()

    session = SessionLocal()
    try:
        existing = session.query(Task).filter(
            Task.status == "completed",
            ((Task.file_md5.isnot(None)) & (Task.file_md5 == task.file_md5)) |
            ((Task.text_md5.isnot(None)) & (Task.text_md5 == task.text_md5)),
        ).first()
        if existing:
            return json_resp(data={"task_id": existing.id})

        session.add(task)
        session.commit()
        task_id = task.id
    finally:
        session.close()

    future = executor.submit(process_task_background, task_id)
    _active_futures[task_id] = future

    return json_resp(data={"task_id": task_id})


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str):
    session = SessionLocal()
    try:
        task = session.get(Task, task_id)
        if not task:
            return JSONResponse(status_code=404, content=json_resp(1, msg="Task not found"))
        result_data = task.to_dict()
        if result_data["result"] and isinstance(result_data["result"], str):
            try:
                result_data["result"] = json.loads(result_data["result"])
            except (json.JSONDecodeError, TypeError):
                pass
        return json_resp(data=result_data)
    finally:
        session.close()


@app.get("/api/tasks")
def list_tasks():
    session = SessionLocal()
    try:
        tasks = session.query(Task).order_by(Task.created_at.desc()).all()
        result = []
        for t in tasks:
            d = t.to_dict()
            if d["result"] and isinstance(d["result"], str):
                try:
                    d["result"] = json.loads(d["result"])
                except (json.JSONDecodeError, TypeError):
                    pass
            result.append(d)
        return json_resp(data=result)
    finally:
        session.close()


@app.post("/api/tasks/{task_id}/retry")
def retry_task(task_id: str):
    session = SessionLocal()
    try:
        task = session.get(Task, task_id)
        if not task:
            return JSONResponse(status_code=404, content=json_resp(1, msg="Task not found"))
        if task.status not in ("failed", "timeout"):
            return json_resp(1, msg="Only failed tasks can be retried")

        task.status = "pending"
        task.progress = 0
        task.error_msg = None
        task.result = None
        session.commit()
        task_id_val = task.id
    finally:
        session.close()

    future = executor.submit(process_task_background, task_id_val)
    _active_futures[task_id_val] = future

    return json_resp(data={"task_id": task_id_val})


@app.put("/api/tasks/{task_id}/segments")
async def update_segments(task_id: str, request: Request):
    body = await request.json()
    session = SessionLocal()
    try:
        task = session.get(Task, task_id)
        if not task:
            return JSONResponse(status_code=404, content=json_resp(1, msg="Task not found"))
        if "segments" not in body:
            return JSONResponse(status_code=400, content=json_resp(1, msg="Missing segments data"))
        task.result = json.dumps(body["segments"], ensure_ascii=False)
        session.commit()
        return json_resp(data={"updated": True})
    finally:
        session.close()


@app.post("/api/tasks/{task_id}/segments/{seg_id}/select")
async def select_material(task_id: str, seg_id: str, request: Request):
    body = await request.json()
    material_id = body.get("material_id")
    if material_id is None:
        return JSONResponse(status_code=400, content=json_resp(1, msg="Missing material_id"))

    session = SessionLocal()
    try:
        task = session.get(Task, task_id)
        if not task:
            return JSONResponse(status_code=404, content=json_resp(1, msg="Task not found"))

        segments = []
        if task.result:
            try:
                segments = json.loads(task.result) if isinstance(task.result, str) else task.result
            except (json.JSONDecodeError, TypeError):
                segments = []

        for seg in segments:
            if seg.get("id") == seg_id:
                seg["selected_material_id"] = material_id
                break

        task.result = json.dumps(segments, ensure_ascii=False)
        session.commit()
        return json_resp(data={"updated": True})
    finally:
        session.close()


@app.get("/api/materials/suggest-tags")
def suggest_material_tags(name: str = ""):
    if not name.strip():
        return json_resp(data={"tags": []})
    from services.tag_service import suggest_tags
    tags = suggest_tags(name)
    joined = "，".join(tags) if tags else ""
    return json_resp(data={"tags": joined, "tag_list": tags})


@app.get("/api/materials")
def list_materials(keyword: str = ""):
    session = SessionLocal()
    try:
        query = session.query(Material)
        if keyword:
            query = query.filter(
                (Material.name.ilike(f"%{keyword}%")) | (Material.tags.ilike(f"%{keyword}%"))
            )
        materials = query.order_by(Material.upload_time.desc()).all()
        return json_resp(data=[m.to_dict() for m in materials])
    finally:
        session.close()


@app.post("/api/materials")
async def upload_material(name: str = Form(""), tags: str = Form(""), file: UploadFile = File(...)):
    if not name:
        name = file.filename.rsplit(".", 1)[0] if file.filename else "Untitled"

    ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else "jpg"
    safe_name = f"mat_{uuid.uuid4().hex}.{ext}"
    upload_path = os.path.join(Config.UPLOAD_FOLDER, safe_name)
    content = await file.read()
    with open(upload_path, "wb") as f:
        f.write(content)

    mime_type = file.content_type or ""
    mat_type = "video" if mime_type.startswith("video") else "image"

    session = SessionLocal()
    try:
        mat = Material(name=name, file_path=safe_name, tags=tags, type=mat_type)
        session.add(mat)
        session.commit()
        return json_resp(data=mat.to_dict())
    finally:
        session.close()


@app.delete("/api/materials/{material_id}")
def delete_material(material_id: int):
    session = SessionLocal()
    try:
        mat = session.get(Material, material_id)
        if not mat:
            return JSONResponse(status_code=404, content=json_resp(1, msg="Material not found"))
        file_path = os.path.join(Config.UPLOAD_FOLDER, mat.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)
        session.delete(mat)
        session.commit()
        return json_resp(data={"deleted": True})
    finally:
        session.close()


@app.post("/api/parse-subtitle")
async def parse_subtitle(request: Request):
    body = await request.json()
    text = (body or {}).get("text", "").strip()
    if not text:
        return JSONResponse(status_code=400, content=json_resp(1, msg="No text provided"))

    segments = split_by_punctuation(text)
    for seg in segments:
        candidates = match_materials(seg.get("keywords", []), top_k=3)
        seg["candidates"] = candidates
        seg["selected_material_id"] = None

    try:
        from services.llm_service import llm_segmentation

        llm_result = llm_segmentation(text, Config.OPENAI_API_KEY)
        if llm_result and len(llm_result) > 1:
            for seg in llm_result:
                candidates = match_materials(seg.get("keywords", []), top_k=3)
                seg["candidates"] = candidates
                seg["selected_material_id"] = None
            segments = llm_result
    except Exception:
        pass

    return json_resp(data={"segments": segments})


@app.get("/health")
def health():
    return json_resp(data={"status": "ok"})


# ─── Seed Materials ────────────────────────────────────────────────────


def seed_materials_if_empty():
    session = SessionLocal()
    try:
        if session.query(Material).count() > 0:
            return

        samples = [
            {"name": "春天花园", "tags": "春天,花园,花朵,自然,植物"},
            {"name": "城市夜景", "tags": "城市,夜景,灯光,建筑,都市"},
            {"name": "科技产品展示", "tags": "科技,产品,展示,数码,创新"},
            {"name": "海滩日落", "tags": "海滩,日落,海洋,自然,风景"},
            {"name": "咖啡时光", "tags": "咖啡,饮品,生活,休闲,美食"},
            {"name": "山间徒步", "tags": "山,徒步,自然,户外,风景"},
            {"name": "工作会议", "tags": "工作,会议,办公,团队,商务"},
            {"name": "美食烹饪", "tags": "美食,烹饪,食物,厨房,生活"},
            {"name": "运动健身", "tags": "运动,健身,健康,跑步,户外"},
            {"name": "音乐演奏", "tags": "音乐,演奏,乐器,艺术,表演"},
            {"name": "星空摄影", "tags": "星空,摄影,夜景,自然,天文"},
            {"name": "宠物日常", "tags": "宠物,动物,日常,生活,可爱"},
        ]
        for idx, s in enumerate(samples):
            mat = Material(
                name=s["name"],
                file_path=f"seed_{idx}.jpg",
                tags=s["tags"],
                type="image",
            )
            session.add(mat)
        session.commit()
    finally:
        session.close()

    # Create colorful placeholder images with text labels
    os.makedirs(os.path.join(os.path.dirname(__file__), "static"), exist_ok=True)

    sample_colors = [
        (76, 175, 80),    # 春天花园 - green
        (33, 33, 33),     # 城市夜景 - dark gray
        (33, 150, 243),   # 科技产品展示 - blue
        (255, 152, 0),    # 海滩日落 - orange
        (121, 85, 72),    # 咖啡时光 - brown
        (56, 142, 60),    # 山间徒步 - forest
        (69, 90, 100),    # 工作会议 - bluegray
        (244, 67, 54),    # 美食烹饪 - red
        (76, 175, 80),    # 运动健身 - green
        (156, 39, 176),   # 音乐演奏 - purple
        (48, 63, 159),    # 星空摄影 - indigo
        (255, 193, 7),    # 宠物日常 - amber
    ]

    try:
        from PIL import Image, ImageDraw, ImageFont

        for idx, s in enumerate(samples):
            dst = os.path.join(Config.UPLOAD_FOLDER, f"seed_{idx}.jpg")
            if os.path.exists(dst):
                continue

            color = sample_colors[idx % len(sample_colors)]
            img = Image.new("RGB", (400, 300), color=color)
            draw = ImageDraw.Draw(img)

            try:
                font = ImageFont.truetype("simhei.ttf", 36)
            except (OSError, IOError):
                try:
                    font = ImageFont.truetype("msyh.ttc", 36)
                except (OSError, IOError):
                    font = ImageFont.load_default()

            text = s["name"]
            bbox = draw.textbbox((0, 0), text, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            x = (400 - tw) / 2
            y = (300 - th) / 2
            draw.text((x, y), text, fill=(255, 255, 255), font=font)
            img.save(dst, "JPEG", quality=85)
    except ImportError:
        import shutil
        ps = os.path.join(os.path.dirname(__file__), "static", "placeholder.jpg")
        if not os.path.exists(ps):
            gray = Image.new("RGB", (400, 300), color=(200, 200, 200))
            gray.save(ps)
        for idx in range(len(samples)):
            dst = os.path.join(Config.UPLOAD_FOLDER, f"seed_{idx}.jpg")
            if not os.path.exists(dst):
                shutil.copy2(ps, dst)
    except Exception:
        pass


# ─── Static Files ──────────────────────────────────────────────────────

os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=Config.UPLOAD_FOLDER), name="uploads")
