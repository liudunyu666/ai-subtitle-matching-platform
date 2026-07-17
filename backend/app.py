import json
import os
import uuid
import hashlib
import time
import threading
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from config import Config
from models.db import db, Task, Material
from services.segmentation_service import split_by_punctuation, extract_keywords_tfidf
from services.matching_service import match_materials
from services.asr_service import transcribe as asr_transcribe

app = Flask(__name__, static_folder="static")
app.config.from_object(Config)
CORS(app)
db.init_app(app)

executor = ThreadPoolExecutor(max_workers=Config.MAX_WORKERS)
_active_futures = {}

ALLOWED_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "mp3", "wav", "m4a", "ogg", "jpg", "jpeg", "png", "gif", "webp"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def file_md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def json_response(code=0, data=None, msg=""):
    return jsonify({"code": code, "data": data, "msg": msg})


def process_task_background(task_id):
    deadline = time.time() + Config.TASK_TIMEOUT

    def check_timeout():
        if time.time() > deadline:
            raise TimeoutError(f"Task timed out after {Config.TASK_TIMEOUT}s")

    with app.app_context():
        task = db.session.get(Task, task_id)
        if not task:
            return
        try:
            task.status = "processing"
            task.progress = 10
            task.error_msg = None
            db.session.commit()
            check_timeout()

            if task.file_path and os.path.exists(task.file_path):
                api_key = Config.OPENAI_API_KEY
                if api_key:
                    try:
                        text = asr_transcribe(task.file_path, api_key)
                    except Exception as e:
                        app.logger.warning(f"ASR failed, switching to fallback: {e}")
                        text = ""
                else:
                    text = ""
                task.progress = 40
            else:
                text = ""
            check_timeout()

            raw = task.raw_text or ""
            final_text = text or raw
            if not final_text.strip():
                raise ValueError("No subtitle text available. Use the paste-text option.")

            task.progress = 50
            db.session.commit()
            check_timeout()

            segments = split_by_punctuation(final_text)

            if not segments or len(segments) == 0:
                segments = [
                    {
                        "id": f"seg_0",
                        "text": final_text[:200],
                        "keywords": extract_keywords_tfidf(final_text),
                    }
                ]

            task.progress = 70
            db.session.commit()
            check_timeout()

            for seg in segments:
                candidates = match_materials(seg.get("keywords", []), top_k=3)
                seg["candidates"] = candidates
                seg["selected_material_id"] = None
            check_timeout()

            task.progress = 90
            db.session.commit()

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
            db.session.commit()

        except Exception as e:
            task.status = "failed"
            task.error_msg = str(e)
            db.session.commit()


# ─── Routes ────────────────────────────────────────────────────────────────

@app.route("/api/tasks", methods=["POST"])
def create_task():
    raw_text = request.form.get("text", "")
    file = request.files.get("file")

    if not file and not raw_text.strip():
        return json_response(code=1, msg="Please upload a file or paste subtitle text"), 400

    task = Task()
    task.status = "pending"
    task.raw_text = raw_text

    if file and allowed_file(file.filename):
        ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else ""
        safe_name = f"{uuid.uuid4().hex}.{ext}"
        upload_path = os.path.join(Config.UPLOAD_FOLDER, safe_name)
        file.save(upload_path)
        task.file_name = file.filename
        task.file_path = upload_path
        task.file_md5 = file_md5(upload_path)
    elif file and not allowed_file(file.filename):
        return json_response(code=1, msg=f"File type not allowed: {file.filename}"), 400

    if raw_text.strip():
        task.text_md5 = hashlib.md5(raw_text.encode("utf-8")).hexdigest()

    existing = Task.query.filter(
        db.or_(
            Task.file_md5.isnot(None) & (Task.file_md5 == task.file_md5),
            Task.text_md5.isnot(None) & (Task.text_md5 == task.text_md5),
        ),
        Task.status == "completed",
    ).first()
    if existing:
        return json_response(data={"task_id": existing.id})

    db.session.add(task)
    db.session.commit()

    future = executor.submit(process_task_background, task.id)
    _active_futures[task.id] = future

    return json_response(data={"task_id": task.id})


@app.route("/api/tasks/<task_id>", methods=["GET"])
def get_task(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        return json_response(code=1, msg="Task not found"), 404
    result_data = task.to_dict()
    if result_data["result"] and isinstance(result_data["result"], str):
        try:
            result_data["result"] = json.loads(result_data["result"])
        except (json.JSONDecodeError, TypeError):
            pass
    return json_response(data=result_data)


@app.route("/api/tasks", methods=["GET"])
def list_tasks():
    tasks = Task.query.order_by(Task.created_at.desc()).all()
    result = []
    for t in tasks:
        d = t.to_dict()
        if d["result"] and isinstance(d["result"], str):
            try:
                d["result"] = json.loads(d["result"])
            except (json.JSONDecodeError, TypeError):
                pass
        result.append(d)
    return json_response(data=result)


@app.route("/api/tasks/<task_id>/retry", methods=["POST"])
def retry_task(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        return json_response(code=1, msg="Task not found"), 404
    if task.status not in ("failed", "timeout"):
        return json_response(code=1, msg="Only failed tasks can be retried"), 400

    task.status = "pending"
    task.progress = 0
    task.error_msg = None
    task.result = None
    db.session.commit()

    future = executor.submit(process_task_background, task.id)
    _active_futures[task.id] = future

    return json_response(data={"task_id": task.id})


@app.route("/api/tasks/<task_id>/segments", methods=["PUT"])
def update_segments(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        return json_response(code=1, msg="Task not found"), 404
    data = request.get_json()
    if not data or "segments" not in data:
        return json_response(code=1, msg="Missing segments data"), 400
    task.result = json.dumps(data["segments"], ensure_ascii=False)
    db.session.commit()
    return json_response(data={"updated": True})


@app.route("/api/tasks/<task_id>/segments/<seg_id>/select", methods=["POST"])
def select_material(task_id, seg_id):
    task = db.session.get(Task, task_id)
    if not task:
        return json_response(code=1, msg="Task not found"), 404
    data = request.get_json()
    material_id = data.get("material_id")
    if material_id is None:
        return json_response(code=1, msg="Missing material_id"), 400

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
    db.session.commit()
    return json_response(data={"updated": True})


@app.route("/api/materials/suggest-tags", methods=["GET"])
def suggest_material_tags():
    name = request.args.get("name", "").strip()
    if not name:
        return json_response(data={"tags": []})
    from services.tag_service import suggest_tags
    tags = suggest_tags(name)
    joined = "，".join(tags) if tags else ""
    return json_response(data={"tags": joined, "tag_list": tags})


@app.route("/api/materials", methods=["GET"])
def list_materials():
    keyword = request.args.get("keyword", "").strip()
    query = Material.query
    if keyword:
        query = query.filter(
            db.or_(
                Material.name.ilike(f"%{keyword}%"),
                Material.tags.ilike(f"%{keyword}%"),
            )
        )
    materials = query.order_by(Material.upload_time.desc()).all()
    return json_response(data=[m.to_dict() for m in materials])


@app.route("/api/materials", methods=["POST"])
def upload_material():
    name = request.form.get("name", "")
    tags = request.form.get("tags", "")
    file = request.files.get("file")

    if not file:
        return json_response(code=1, msg="No file provided"), 400
    if not name:
        name = file.filename.rsplit(".", 1)[0] if file.filename else "Untitled"

    ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else "jpg"
    safe_name = f"mat_{uuid.uuid4().hex}.{ext}"
    upload_path = os.path.join(Config.UPLOAD_FOLDER, safe_name)
    file.save(upload_path)

    mime_type = file.content_type or ""
    mat_type = "video" if mime_type.startswith("video") else "image"

    mat = Material(name=name, file_path=safe_name, tags=tags, type=mat_type)
    db.session.add(mat)
    db.session.commit()
    return json_response(data=mat.to_dict())


@app.route("/api/materials/<int:material_id>", methods=["DELETE"])
def delete_material(material_id):
    mat = db.session.get(Material, material_id)
    if not mat:
        return json_response(code=1, msg="Material not found"), 404
    file_path = os.path.join(Config.UPLOAD_FOLDER, mat.file_path)
    if os.path.exists(file_path):
        os.remove(file_path)
    db.session.delete(mat)
    db.session.commit()
    return json_response(data={"deleted": True})


@app.route("/api/parse-subtitle", methods=["POST"])
def parse_subtitle():
    data = request.get_json()
    text = (data or {}).get("text", "").strip()
    if not text:
        return json_response(code=1, msg="No text provided"), 400

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

    return json_response(data={"segments": segments})


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(Config.UPLOAD_FOLDER, filename)


@app.route("/health")
def health():
    return json_response(data={"status": "ok"})


def init_db():
    with app.app_context():
        db.create_all()
        if Material.query.count() == 0:
            seed_materials()


def seed_materials():
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
        db.session.add(mat)
    db.session.commit()

    import shutil
    src = os.path.join(Config.STATIC_FOLDER) if hasattr(Config, "STATIC_FOLDER") else os.path.join(os.path.dirname(__file__), "static")
    placeholder = os.path.join(src or os.path.dirname(__file__), "placeholder.jpg")
    if not os.path.exists(placeholder):
        placeholder = os.path.join(os.path.dirname(__file__), "static", "placeholder.jpg")
    os.makedirs(os.path.dirname(placeholder), exist_ok=True)
    if not os.path.exists(placeholder):
        from PIL import Image
        img = Image.new("RGB", (400, 300), color=(200, 200, 200))
        img.save(placeholder)

    for idx in range(len(samples)):
        dst = os.path.join(Config.UPLOAD_FOLDER, f"seed_{idx}.jpg")
        if not os.path.exists(dst):
            shutil.copy2(placeholder, dst)


if __name__ == "__main__":
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), "static"), exist_ok=True)
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
