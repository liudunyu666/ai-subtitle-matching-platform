import os


def transcribe(file_path, api_key=""):
    if not api_key:
        raise ValueError("OPENAI_API_KEY not configured")

    import openai

    client = openai.OpenAI(api_key=api_key)
    with open(file_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1", file=audio_file, response_format="text"
        )
    return transcript
