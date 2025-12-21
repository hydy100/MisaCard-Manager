import os
import secrets
import json
from datetime import timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

# ============================================
# 时区配置
# ============================================
# 支持格式: "Asia/Shanghai", "UTC", "+8", "-5" 等
TZ_CONFIG = os.getenv("TZ", "UTC")

def parse_timezone(tz_str: str) -> timezone:
    """解析时区字符串，返回 timezone 对象"""
    tz_str = tz_str.strip()
    
    # 处理 UTC
    if tz_str.upper() == "UTC":
        return timezone.utc
    
    # 处理数字偏移格式: +8, -5, +08:00, -05:30
    if tz_str.startswith(('+', '-')) or tz_str.lstrip('-').replace(':', '').isdigit():
        try:
            # 移除可能的冒号
            clean = tz_str.replace(':', '')
            if len(clean) <= 3:  # +8, -5, +08
                hours = int(clean)
                minutes = 0
            else:  # +0800, -0530
                sign = -1 if clean.startswith('-') else 1
                clean = clean.lstrip('+-')
                hours = sign * int(clean[:2])
                minutes = int(clean[2:4]) if len(clean) >= 4 else 0
            return timezone(timedelta(hours=hours, minutes=minutes))
        except ValueError:
            pass
    
    # 处理常见时区名称
    tz_mapping = {
        "Asia/Shanghai": timezone(timedelta(hours=8)),
        "Asia/Tokyo": timezone(timedelta(hours=9)),
        "Asia/Hong_Kong": timezone(timedelta(hours=8)),
        "Asia/Singapore": timezone(timedelta(hours=8)),
        "America/New_York": timezone(timedelta(hours=-5)),
        "America/Los_Angeles": timezone(timedelta(hours=-8)),
        "Europe/London": timezone.utc,
        "Europe/Paris": timezone(timedelta(hours=1)),
        "Europe/Berlin": timezone(timedelta(hours=1)),
    }
    
    if tz_str in tz_mapping:
        return tz_mapping[tz_str]
    
    # 默认返回 UTC
    print(f"⚠️  无法识别的时区 '{tz_str}'，使用 UTC")
    return timezone.utc

# 解析时区
APP_TIMEZONE = parse_timezone(TZ_CONFIG)
print(f"✅ 时区设置: {TZ_CONFIG} (UTC{'+' if APP_TIMEZONE.utcoffset(None).total_seconds() >= 0 else ''}{int(APP_TIMEZONE.utcoffset(None).total_seconds() // 3600)}:{abs(int(APP_TIMEZONE.utcoffset(None).total_seconds() % 3600 // 60)):02d})")


def get_current_time():
    """获取当前时间（使用配置的时区）"""
    from datetime import datetime
    return datetime.now(APP_TIMEZONE)


def format_datetime(dt, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """格式化时间（转换到配置的时区）"""
    if dt is None:
        return "-"
    # 如果是 naive datetime，假定为 UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    # 转换到配置的时区
    local_dt = dt.astimezone(APP_TIMEZONE)
    return local_dt.strftime(format_str)

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

# 同步API签名密钥（用于防止伪造请求）
# 如果未设置，使用 SECRET_KEY 的哈希作为默认值
SYNC_API_SECRET = os.getenv("SYNC_API_SECRET")
if not SYNC_API_SECRET:
    import hashlib
    SYNC_API_SECRET = hashlib.sha256(f"sync_{SECRET_KEY}".encode()).hexdigest()[:32]
