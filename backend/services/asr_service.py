import os
import time


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

    # The file must be accessible via HTTP URL
    if not public_base_url:
        raise ValueError("PUBLIC_BASE_URL is required for DashScope ASR")

    file_name = os.path.basename(file_path)
    file_url = f"{public_base_url}/uploads/{file_name}"

    result = Transcription.async_call(
        model="paraformer-v1",
        audio_url=file_url,
        language="zh",
    )
    if result.status_code != 200:
        raise ValueError(f"DashScope transcription failed: {result}")

    transcribe_id = result.output["task_id"]

    # Poll for result
    for _ in range(60):
        time.sleep(2)
        result = Transcription.fetch(task_id=transcribe_id)
        if result.status_code != 200:
            continue
        status = result.output.get("status")
        if status == "SUCCEEDED":
            sentences = result.output.get("results", [])
            text = "".join(s.get("text", "") for s in sentences)
            return text
        elif status == "FAILED":
            raise ValueError(f"DashScope transcription failed: {result.output.get('error', '')}")

    raise TimeoutError("DashScope transcription timed out")
