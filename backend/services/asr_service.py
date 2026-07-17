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

    # Debug: print the full response structure
    import sys
    print(f"DashScope output keys: {list(result.output.keys())}", flush=True)
    print(f"DashScope full output: {result.output}", flush=True)

    # The results may be directly in output or nested differently
    results = result.output.get("results")
    if results is None:
        # Maybe results are in output directly as sentences
        sentences = result.output.get("sentences")
        if sentences:
            text = "".join(s.get("text", "") for s in sentences)
            if text.strip():
                return text
        raise ValueError(f"DashScope: no results in output. Keys: {list(result.output.keys())}")

    # Try direct text extraction from results
    if isinstance(results, list) and len(results) > 0:
        # Some APIs return sentences directly
        text = "".join(s.get("text", "") for s in results if isinstance(s, dict))
        if text.strip():
            return text

        # Maybe it's a URL-based result
        try:
            url = results[0] if isinstance(results[0], str) else results[0].get("transcription_url", "")
            if url:
                data = json.loads(request.urlopen(url).read().decode("utf-8"))
                transcripts = data.get("transcripts", [])
                text = "".join(t.get("text", "") for t in transcripts)
                if text.strip():
                    return text
        except Exception as e:
            raise ValueError(f"DashScope URL result failed: {e}")

    raise ValueError(f"DashScope: unexpected result format: {results}")
