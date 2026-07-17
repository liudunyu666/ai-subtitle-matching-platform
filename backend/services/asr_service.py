import os


def transcribe(file_path, openai_api_key="", dashscope_api_key="", public_base_url=""):
    """
    Transcribe audio/video file to text.
    Uses DashScope (Alibaba) if dashscope_api_key is set, otherwise OpenAI Whisper.
    """
    if dashscope_api_key:
        return _dashscope_transcribe(file_path, dashscope_api_key, public_base_url)
    elif openai_api_key:
        return _openai_transcribe(file_path, openai_api_key)
    else:
        raise ValueError("No ASR API key configured. Set OPENAI_API_KEY or DASHSCOPE_API_KEY.")


def _openai_transcribe(file_path, api_key):
    import openai

    client = openai.OpenAI(api_key=api_key)
    with open(file_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1", file=audio_file, response_format="text"
        )
    return transcript


def _dashscope_transcribe(file_path, api_key, public_base_url):
    from dashscope.audio.asr import Transcription
    import json
    from urllib import request

    if not public_base_url:
        raise ValueError("PUBLIC_BASE_URL is required for DashScope ASR")

    file_name = os.path.basename(file_path)
    file_url = f"{public_base_url}/uploads/{file_name}"

    task_response = Transcription.async_call(
        model="paraformer-v1",
        file_urls=[file_url],
        language_hints=["zh"],
    )
    if task_response.status_code != 200:
        raise ValueError(f"DashScope transcription failed: {task_response}")

    result = Transcription.wait(task=task_response.output.task_id)
    if result.status_code != 200:
        raise ValueError(f"DashScope transcription failed: {result}")

    # Check task status
    task_status = result.output.get("task_status")
    if task_status == "FAILED":
        err_msg = result.output.get("message", "unknown error")
        raise ValueError(f"DashScope transcription failed: {err_msg}")

    # Try direct results from output
    sentences = result.output.get("results") or result.output.get("sentences")
    if sentences and isinstance(sentences, list):
        text = "".join(s.get("text", "") for s in sentences if isinstance(s, dict))
        if text.strip():
            return text

    # Fallback: download from transcription_url
    try:
        results_list = result.output.get("results", [])
        if results_list and isinstance(results_list[0], dict):
            url = results_list[0].get("transcription_url", "")
            if url:
                data = json.loads(request.urlopen(url).read().decode("utf-8"))
                transcripts = data.get("transcripts", [])
                text = "".join(t.get("text", "") for t in transcripts)
                if text.strip():
                    return text
    except Exception as e:
        raise ValueError(f"DashScope result parse failed: {e}")

    raise ValueError("DashScope transcription returned no text")
