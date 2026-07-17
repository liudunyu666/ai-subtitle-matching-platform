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

    # The file must be accessible via HTTP URL
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

    # Wait for result (blocking, no manual polling needed)
    result = Transcription.wait(task=task_response.output.task_id)
    if result.status_code != 200:
        raise ValueError(f"DashScope transcription failed: {result}")

    # Try direct results first (sentences with text field)
    sentences = result.output.get("results", [])
    if sentences:
        text = "".join(s.get("text", "") for s in sentences)
        if text.strip():
            return text

    # Fallback: download from transcription_url
    try:
        transcription_url = result.output["results"][0]["transcription_url"]
        transcription_data = json.loads(request.urlopen(transcription_url).read().decode("utf-8"))
        transcripts = transcription_data.get("transcripts", [])
        text = "".join(t.get("text", "") for t in transcripts)
        if text.strip():
            return text
    except (KeyError, IndexError, json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ValueError(f"DashScope transcription result parsing failed: {e}")

    raise ValueError("DashScope transcription returned no text")
