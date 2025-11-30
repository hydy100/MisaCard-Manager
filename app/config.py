import os
import secrets
from dotenv import load_dotenv

load_dotenv()

MISACARD_API_BASE_URL = os.getenv(
    "MISACARD_API_BASE_URL",
    "https://api.misacard.com/api/card"
)

MISACARD_API_TOKEN = os.getenv("MISACARD_API_TOKEN")
if not MISACARD_API_TOKEN:
    raise ValueError("MISACARD_API_TOKEN 环境变量未设置！请在 .env 文件中配置")

MISACARD_API_HEADERS = {
    "Authorization": f"Bearer {MISACARD_API_TOKEN}",
    "Origin": "https://misacard.com",
    "Referer": "https://misacard.com/",
    "Accept": "application/json, text/plain, */*",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
}

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cards.db")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    raise ValueError("ADMIN_PASSWORD 环境变量未设置！请在 .env 文件中配置")

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = secrets.token_urlsafe(32)
        print("⚠️  警告: SECRET_KEY 未设置，已生成临时密钥（仅用于开发）")
    else:
        raise ValueError("生产环境必须设置 SECRET_KEY 环境变量！")

SESSION_MAX_AGE = int(os.getenv("SESSION_MAX_AGE", 86400))