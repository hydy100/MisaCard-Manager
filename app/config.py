import os
import secrets
import json
from dotenv import load_dotenv

load_dotenv()

# 多 API 配置支持
# 格式: MISACARD_API_CONFIGS='[{"name":"主站","base_url":"https://api.misacard.com","token":"xxx"},{"name":"备用","base_url":"https://api2.misacard.com","token":"yyy"}]'
MISACARD_API_CONFIGS_RAW = os.getenv("MISACARD_API_CONFIGS")
MISACARD_API_CONFIGS = []

if MISACARD_API_CONFIGS_RAW:
    # 使用多 API 配置
    try:
        configs = json.loads(MISACARD_API_CONFIGS_RAW)
        if not isinstance(configs, list) or len(configs) == 0:
            raise ValueError("MISACARD_API_CONFIGS 必须是非空数组")
        
        for idx, config in enumerate(configs):
            if not isinstance(config, dict):
                raise ValueError(f"MISACARD_API_CONFIGS[{idx}] 必须是对象")
            if "name" not in config or "token" not in config:
                raise ValueError(f"MISACARD_API_CONFIGS[{idx}] 必须包含 name 和 token 字段")
            
            # 设置默认 base_url
            if "base_url" not in config:
                config["base_url"] = "https://api.misacard.com"
            
            MISACARD_API_CONFIGS.append({
                "name": config["name"],
                "base_url": config["base_url"].rstrip("/"),  # 移除尾部斜杠
                "token": config["token"]
            })
        
        print(f"✅ 已加载 {len(MISACARD_API_CONFIGS)} 个 API 配置")
    except json.JSONDecodeError as e:
        raise ValueError(f"MISACARD_API_CONFIGS 格式错误：{e}")
    except Exception as e:
        raise ValueError(f"解析 MISACARD_API_CONFIGS 失败：{e}")
else:
    # 向后兼容：使用单个 API 配置
    MISACARD_API_BASE_URL = os.getenv(
        "MISACARD_API_BASE_URL",
        "https://api.misacard.com"
    ).rstrip("/")
    
    MISACARD_API_TOKEN = os.getenv("MISACARD_API_TOKEN")
    if not MISACARD_API_TOKEN:
        raise ValueError("MISACARD_API_TOKEN 或 MISACARD_API_CONFIGS 环境变量未设置！请在 .env 文件中配置")
    
    # 验证 token 是否可能被截断
    if len(MISACARD_API_TOKEN) < 20:
        import warnings
        warnings.warn(f"⚠️  MISACARD_API_TOKEN 长度异常（{len(MISACARD_API_TOKEN)}字符），可能包含特殊字符导致被截断。请确保在 .env 文件中用引号包裹token值。")
    
    # 构建单个配置
    MISACARD_API_CONFIGS = [{
        "name": "默认",
        "base_url": MISACARD_API_BASE_URL,
        "token": MISACARD_API_TOKEN
    }]

# 使用第一个配置作为默认配置（用于管理后台）
MISACARD_API_BASE_URL = MISACARD_API_CONFIGS[0]["base_url"]
MISACARD_API_TOKEN = MISACARD_API_CONFIGS[0]["token"]

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