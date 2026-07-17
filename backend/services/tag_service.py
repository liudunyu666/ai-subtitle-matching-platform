import jieba
import jieba.analyse


def suggest_tags(name, top_k=5):
    """
    Auto-generate tag suggestions from a material name using jieba TF-IDF.
    Returns a list of suggested tag strings.
    """
    if not name or not name.strip():
        return []

    try:
        keywords = jieba.analyse.extract_tags(name, topK=top_k, withWeight=False)
        return [kw for kw in keywords if len(kw) >= 1][:top_k]
    except Exception:
        import re
        words = re.findall(r"[\w]+", name)
        return words[:top_k]
