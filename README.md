# MisaCard 管理系统

一个功能完善、安全可靠的虚拟卡管理系统，用于管理 MisaCard 虚拟信用卡，支持卡片激活、查询、批量导入、退款管理等功能。

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115.5-green.svg)
![Docker](https://img.shields.io/badge/Docker-支持-brightgreen.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ 功能特性

### 🔓 公共查询（无需登录）
- 卡密查询、查询并激活、卡号查询
- 实时余额和消费记录
- 一键复制卡片信息

### 🔐 安全特性
- 分级访问、登录鉴权、Session 加密
- 文件访问保护、非 root 运行

### 📋 核心功能
- 卡片管理、激活、批量导入
- 过期检测、退款管理、消费记录

### 🎨 用户界面
- 现代化响应式设计、实时数据统计、批量操作

#### 界面预览
![公共页面](static/query.png)
![管理员登录](static/login.png)
![系统概览](static/overview.png)
![卡片列表](static/list.png)

### 🔧 技术特性
- RESTful API、异步处理、自动文档、Docker 支持

## 📦 技术栈

- **后端框架**: FastAPI 0.115.5
- **数据库**: SQLite + SQLAlchemy 2.0.36 ORM
- **服务器**: Uvicorn (ASGI)
- **数据验证**: Pydantic 2.10.3
- **HTTP 客户端**: httpx 0.28.1
- **模板引擎**: Jinja2 3.1.4
- **Session 管理**: Starlette SessionMiddleware + itsdangerous
- **前端样式**: Tailwind CSS

## 🚀 快速开始

### 方式一：Docker 部署（推荐）

#### 环境要求
- Docker 20.10+
- Docker Compose 1.29+

#### 部署步骤

1. **克隆项目**
```bash
git clone https://github.com/hydy100/MisaCard-Manager.git
cd MisaCard-Manager
```

2. **配置环境变量**
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，设置必要的配置
nano .env  # 或使用其他编辑器
```

**重要：必须配置以下环境变量：**
- `MISACARD_API_TOKEN` - 你的 MisaCard API Token
- `ADMIN_PASSWORD` - 管理员登录密码（建议使用强密码）
- `SECRET_KEY` - Session 加密密钥（使用 `python -c "import secrets; print(secrets.token_urlsafe(32))"` 生成）

3. **设置文件权限**
```bash
mkdir -p data
chmod 700 data
chown -R 1000:1000 data 2>/dev/null || true
```

4. **启动服务**
```bash
# 启动容器
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 停止并删除数据
docker-compose down -v
```

5. **访问系统**
- 打开浏览器访问: http://localhost:8000
- 使用 .env 中配置的 `ADMIN_PASSWORD` 登录

### 方式二：本地部署

#### 环境要求
- Python 3.12 或更高版本
- pip (Python 包管理器)

#### 安装步骤

**1. 克隆项目**
```bash
git clone https://github.com/hydy100/MisaCard-Manager.git
cd MisaCard-Manager
```

**2. 创建虚拟环境（推荐）**
```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

**3. 安装依赖**
```bash
pip install -r requirements.txt
```

**4. 配置环境变量**
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
nano .env  # 或使用其他编辑器
```

**必须配置：** `MISACARD_API_TOKEN`、`ADMIN_PASSWORD`、`SECRET_KEY`

**5. 初始化数据库**
```bash
python3 init_db.py init
```

**6. 启动服务**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**7. 访问系统**
- 公共查询: http://localhost:8000
- 管理后台: http://localhost:8000/admin

## 🔒 安全说明

### 已实施的安全措施

- ✅ API 认证保护：所有管理 API 需要登录
- ✅ 文件访问保护：自动阻止访问数据库和敏感文件
- ✅ Session 加密：使用 SECRET_KEY 加密，生产环境自动启用 HTTPS only
- ✅ 非 root 运行：Docker 容器以非 root 用户运行

### 安全加固建议

**必须执行：**
```bash
# 设置文件权限
chmod 700 data/
chmod 600 data/cards.db .env

# 使用 Nginx 反向代理（推荐）
# 配置规则阻止直接访问 .db、.env 等文件
```

**强烈建议：**
- 启用 HTTPS
- 配置防火墙
- 定期备份数据库

### 密钥生成

```bash
# 生成 SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 📖 使用说明

### 公共查询（无需登录）

访问首页 http://localhost:8000 即可使用：

- **查询**：输入卡密查询信息（不会自动激活）
- **查询并激活**：输入卡密，如果未激活会自动激活
- **查询卡号**：输入16位卡号查看余额和交易记录

### 管理后台登录

访问 http://localhost:8000/admin 或点击首页右上角"管理员登录"：

1. 输入在 `.env` 中配置的 `ADMIN_PASSWORD`
2. 登录成功后进入完整管理系统
3. 会话保持状态（默认24小时）
4. 点击侧边栏底部的"退出登录"按钮可退出

### 卡片管理

- **批量导入**：在「批量导入」页面粘贴卡密数据（格式：`卡密: mio-xxxxx 额度: 1 有效期: 1小时`）
- **激活卡片**：在卡片列表点击「激活」按钮，或使用「查询未激活卡密」批量查询
- **退款管理**：点击「标记退款」或使用「复制未退款卡号」功能
- **查看详情**：点击「详情」查看完整信息和交易记录

## 📚 API 文档

- **Swagger UI（需要登录）**: http://localhost:8000/docs
- **ReDoc（需要登录）**: http://localhost:8000/redoc

**主要端点：**
- `POST /api/auth/login` - 登录
- `GET /api/cards/` - 卡片列表
- `POST /api/cards/{card_id}/activate` - 激活卡片
- `POST /api/import/text` - 批量导入
- `GET /health` - 健康检查（公开）

**注意：** 除 `/api/auth/login` 和 `/health` 外，所有 API 都需要登录。

## 🐳 Docker 配置

数据库文件存储在 `./data/cards.db`，通过 volume 挂载。

**常用命令：**
```bash
docker compose up -d          # 启动
docker compose logs -f        # 查看日志
docker compose down           # 停止
docker compose restart        # 重启
```

## 🛠️ 开发

**项目结构：** `app/` - 应用代码，`data/` - 数据目录，`templates/` - 页面模板

**运行测试：** `pytest`

### 自定义 Favicon

要添加自定义网站图标（favicon），请按以下步骤操作：

1. **放置 favicon 文件**
   - 将 `favicon.ico` 文件放在 `app/static/` 目录下
   - 文件路径：`app/static/favicon.ico`

2. **在模板中引用**
   - 在所有 HTML 模板的 `<head>` 部分添加以下代码：
   ```html
   <link rel="icon" type="image/x-icon" href="/static/favicon.ico">
   ```
   - 需要修改的模板文件：
     - `app/templates/query.html`
     - `app/templates/index.html`
     - `app/templates/login.html`

3. **Docker 部署**
   - Dockerfile 中的 `COPY app/ ./app/` 会自动包含 `app/static/` 目录
   - 无需额外配置，favicon 在 Docker 部署中会自动生效

**注意：** 静态文件通过 `/static/` 路径访问，FastAPI 会自动处理静态文件服务。

## ⚙️ 环境变量

| 变量名 | 必需 | 说明 |
|--------|------|------|
| `MISACARD_API_TOKEN` | ✅ | MisaCard API 令牌 |
| `ADMIN_PASSWORD` | ✅ | 管理员密码 |
| `SECRET_KEY` | ✅ | Session 加密密钥 |
| `DEBUG` | ❌ | 调试模式（默认 `true`） |
| `SESSION_MAX_AGE` | ❌ | Session 过期时间（默认 86400 秒） |

## 🔄 数据库管理

```bash
python init_db.py init    # 初始化
python init_db.py check   # 检查状态
cp data/cards.db data/cards.db.backup  # 备份
```

## 🚨 故障排除

**环境变量未设置：** 确保 `.env` 文件存在且包含 `ADMIN_PASSWORD`、`SECRET_KEY`、`MISACARD_API_TOKEN`

**登录后跳转回登录页：** 检查 `SECRET_KEY` 是否设置且固定，清除浏览器 Cookie 后重试

**数据库权限错误：** 执行 `chmod 700 data && chown -R 1000:1000 data`

**无法访问 API：** 检查 `MISACARD_API_TOKEN` 和网络连接

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📮 联系方式

如有问题或建议，请通过以下方式联系：
- GitHub Issues: [提交 Issue](https://github.com/hydy100/MisaCard-Manager/issues)

## 🙏 致谢

感谢所有贡献者和使用本项目的用户！

---

**生产环境部署建议：** 设置文件权限、使用 Nginx 反向代理、启用 HTTPS、定期备份数据。