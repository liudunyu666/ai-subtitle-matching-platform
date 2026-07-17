import re
from models.db import Material, SessionLocal


def _tokenize(text):
    tokens = []
    if not text:
        return tokens
    text = text.lower().strip()
    parts = re.split(r'[,，、\s]+', text)
    for p in parts:
        p = p.strip()
        if p and len(p) >= 1:
            tokens.append(p)
    return tokens


def _calculate_score(keywords, name, tags_str):
    if not keywords:
        return 0, [], ""

    kw_lower = [k.lower().strip() for k in keywords if k.strip()]
    name_lower = name.lower().strip() if name else ""
    tag_list = [t.strip().lower() for t in tags_str.split(",")] if tags_str else []

    matched = set()
    score = 0.0

    for kw in kw_lower:
        best_match = 0
        for tag in tag_list:
            if kw == tag:
                best_match = 1.0
                matched.add(tag)
            elif kw in tag or tag in kw:
                best_match = max(best_match, 0.6)
                matched.add(tag)
        if kw in name_lower or name_lower in kw:
            best_match = max(best_match, 0.5)
        score += best_match

    total = len(kw_lower)
    if total > 0:
        score = score / total

    matched_keywords = list(matched)
    if matched_keywords:
        reason = f"匹配到关键词：{'、'.join(matched_keywords)}"
    else:
        reason = "无匹配关键词"

    return round(score, 4), matched_keywords, reason


def match_materials(keywords, top_k=3):
    session = SessionLocal()
    try:
        materials = session.query(Material).all()
    finally:
        session.close()

    scored = []
    for mat in materials:
        tags_str = mat.tags or ""
        score, matched_kw, reason = _calculate_score(keywords, mat.name, tags_str)
        scored.append({
            "material": mat.to_dict(),
            "score": score,
            "matched_keywords": matched_kw,
            "reason": reason,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)

    deduped = []
    seen_ids = set()
    for s in scored:
        mid = s["material"]["id"]
        if mid not in seen_ids:
            seen_ids.add(mid)
            deduped.append(s)

    return deduped[:top_k]
