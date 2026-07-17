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

    # Dump the full output as JSON to see the structure
    raw = json.dumps({k: str(v) for k, v in dict(result.output).items()}, ensure_ascii=False)
    raise ValueError(f"DashScope RAW output for debugging: {raw}")
