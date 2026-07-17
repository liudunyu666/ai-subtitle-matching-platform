import json
import re


def llm_segmentation(text, api_key=""):
    if not api_key:
        raise ValueError("OPENAI_API_KEY not configured")

    import openai

    client = openai.OpenAI(api_key=api_key)

    prompt = (
        "请将以下字幕按语义划分为若干片段，为每个片段提取3~5个关键词。"
        "返回JSON数组格式：\n"
        '[{"text":"片段文本","keywords":["关键词1","关键词2"]}]\n\n'
        "字幕内容：\n" + text
    )

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content.strip()

    json_match = re.search(r"\[.*\]", content, re.DOTALL)
    if json_match:
        content = json_match.group()

    try:
        segments = json.loads(content)
        if isinstance(segments, dict) and "segments" in segments:
            segments = segments["segments"]
        if isinstance(segments, list):
            for i, seg in enumerate(segments):
                if "id" not in seg:
                    seg["id"] = f"seg_{i}"
            return segments
    except (json.JSONDecodeError, TypeError):
        pass

    raise ValueError("Failed to parse LLM response")
