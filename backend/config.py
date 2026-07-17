import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///smp.db")
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
    MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 200MB
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
    PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "")
    TASK_TIMEOUT = 120
    MAX_WORKERS = 2
