from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field
import os

from .database import engine
from . import models
from .api import cards, imports
from .config import ADMIN_PASSWORD, SECRET_KEY, SESSION_MAX_AGE, MISACARD_API_TOKEN, MISACARD_API_CONFIGS, DEBUG

models.Base.metadata.create_all(bind=engine)

def check_auth(request: Request):
    return request.session.get("authenticated", False)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # 安全：阻止直接访问敏感文件
        sensitive_extensions = [".db", ".sqlite", ".sqlite3", ".env", ".log"]
        if any(path.endswith(ext) for ext in sensitive_extensions):
            return JSONResponse(
                status_code=404,
                content={"detail": "Not Found"}
            )
        
        # 安全：阻止访问隐藏文件（以 . 开头）
        path_parts = path.strip("/").split("/")
        if any(part.startswith(".") for part in path_parts if part):
            return JSONResponse(
                status_code=404,
                content={"detail": "Not Found"}
            )
        
        # 公开路径（不需要登录）
        public_paths = ["/", "/login", "/api/auth/login", "/health", "/static"]
        is_public = any(path.startswith(p) for p in public_paths)
        
        # /docs 和 /redoc 需要登录才能访问
        if not is_public:
            if not check_auth(request):
                if path.startswith("/api"):
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "未登录，请先登录"}
                    )
                else:
                    # 包括 /docs 和 /redoc 在内的所有非公开页面都重定向到登录页
                    return RedirectResponse(url="/login", status_code=303)
        
        response = await call_next(request)
        return response


app = FastAPI(
    title="MisaCard 管理系统",
    description="卡片管理系统 - 支持卡片查询、激活、批量导入",
    version="2.0.0",
    docs_url=None,  # 禁用自动生成的 /docs
    redoc_url=None  # 禁用自动生成的 /redoc
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuthMiddleware)

app.add_middleware(
    SessionMiddleware, 
    secret_key=SECRET_KEY,
    max_age=SESSION_MAX_AGE,
    same_site="lax",
    https_only=not DEBUG  # 生产环境启用 HTTPS only
)

app.include_router(cards.router, prefix="/api")
app.include_router(imports.router, prefix="/api")

templates_path = os.path.join(os.path.dirname(__file__), "templates")
static_path = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_path, exist_ok=True)

templates = Jinja2Templates(directory=templates_path)
app.mount("/static", StaticFiles(directory=static_path), name="static")


class LoginRequest(BaseModel):
    """
    登录请求模型
    
    用于管理员登录，需要提供正确的管理员密码。
    """
    password: str = Field(..., description="管理员密码（从 .env 文件中的 ADMIN_PASSWORD 配置获取）")


@app.get("/")
async def root(request: Request):
    # 传递 API 配置列表，但不暴露完整 token（仅用于前端识别）
    api_configs_for_frontend = [
        {
            "name": config["name"],
            "base_url": config["base_url"],
            "token": config["token"]  # 前端需要完整 token 用于 API 调用
        }
        for config in MISACARD_API_CONFIGS
    ]
    
    return templates.TemplateResponse("query.html", {
        "request": request,
        "api_token": MISACARD_API_TOKEN,  # 保持向后兼容
        "api_configs": api_configs_for_frontend
    })


@app.get("/admin")
async def admin_dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/login")
async def login_page(request: Request):
    if check_auth(request):
        return RedirectResponse(url="/admin", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/api/auth/login", summary="管理员登录")
async def login(request: Request, login_data: LoginRequest):
    """
    管理员登录接口
    
    使用配置的管理员密码进行登录，登录成功后会在 session 中设置认证状态。
    
    - **password**: 管理员密码（从 .env 文件中的 ADMIN_PASSWORD 配置）
    
    返回登录结果，成功后会设置 session cookie。
    """
    if login_data.password == ADMIN_PASSWORD:
        request.session["authenticated"] = True
        return JSONResponse({
            "success": True,
            "message": "登录成功"
        })
    else:
        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "message": "密码错误，请重试"
            }
        )


@app.post("/api/auth/logout", summary="退出登录")
async def logout(request: Request):
    """
    退出登录接口
    
    清除当前 session，退出登录状态。
    """
    request.session.clear()
    return JSONResponse({
        "success": True,
        "message": "已退出登录"
    })


@app.get("/health", summary="健康检查", tags=["系统"])
async def health_check():
    """
    健康检查端点
    
    用于检查服务是否正常运行，返回服务状态和版本信息。
    """
    return {
        "status": "healthy",
        "service": "MisaCard Backend",
        "version": "2.0.0"
    }


@app.get("/docs", include_in_schema=False)
async def get_documentation(request: Request):
    """Swagger UI 文档页面（需要登录）"""
    if not check_auth(request):
        return RedirectResponse(url="/login", status_code=303)
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )


@app.get("/redoc", include_in_schema=False)
async def get_redoc_documentation(request: Request):
    """ReDoc 文档页面（需要登录）"""
    if not check_auth(request):
        return RedirectResponse(url="/login", status_code=303)
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
    )


@app.get("/api/info", summary="API 信息", tags=["系统"])
async def api_info():
    """
    API 信息端点
    
    返回 API 的基本信息，包括名称、版本和主要端点列表。
    """
    return {
        "name": "MisaCard API",
        "version": "2.0.0",
        "endpoints": {
            "cards": "/api/cards",
            "import": "/api/import",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
