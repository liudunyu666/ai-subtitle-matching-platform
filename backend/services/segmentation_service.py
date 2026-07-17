import os
import jieba
import jieba.analyse


def extract_keywords_tfidf(text, topK=5):
    if not text or not text.strip():
        return []
    try:
        keywords = jieba.analyse.extract_tags(text, topK=topK, withWeight=False)
        return keywords[:topK]
    except Exception:
        import re
        words = re.findall(r"[\w]+", text)
        return list(set(words))[:topK]


def split_by_punctuation(text):
    import re
    sentences = re.split(r"[。！？；.!?;]", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    segments = []
    for i in range(0, len(sentences), 3):
        chunk = "".join(sentences[i : i + 3])
        if chunk.strip():
            keywords = extract_keywords_tfidf(chunk)
            segments.append(
                {"id": f"seg_{i // 3}", "text": chunk, "keywords": keywords}
            )
    return segments
