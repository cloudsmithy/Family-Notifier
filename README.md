# 家庭任务通知 (Family Notifier)

这是一个简单的家庭任务分配和通知应用。家庭成员可以注册账户，互相分配任务，并在完成或删除任务时留下审计记录。应用支持本地账户密码登录和 OIDC 单点登录。

## ✨ 主要功能

- **用户系统**: 支持本地用户名密码注册和登录。
- **OIDC 集成**: 支持通过 OIDC 提供商（如 Casdoor）进行单点登录和自动注册。
- **任务分配**: 用户可以为家庭中的任何其他成员创建和分配任务。
- **任务管理**: 用户可以查看分配给自己的任务，并将其标记为“完成”或“删除”。
- **历史记录**: 查看自己已完成的任务列表。
- **审计日志**: 记录所有任务的“完成”和“删除”操作，便于追溯。
- **现代化界面**: 简洁、美观且对移动端友好的响应式界面。
- **容器化**: 提供 `Dockerfile` 和 `docker-compose.yml`，便于快速部署。

## 🛠️ 技术栈

- **后端**: Flask, Flask-SQLAlchemy, Flask-Login
- **认证**: Authlib (用于 OIDC)
- **数据库**: SQLite
- **前端**: HTML, Bootstrap, Custom CSS & JS
- **部署**: Docker, Docker Compose, Gunicorn

---

## 🚀 快速开始

有两种方式可以运行此应用：本地直接运行或通过 Docker 运行。

### 1. 本地开发环境运行

**a. 准备工作**

- 安装 Python 3.10+
- 创建并激活一个虚拟环境（推荐）:
  ```bash
  python -m venv venv
  source venv/bin/activate  # on Windows, use `venv\Scripts\activate`
  ```

**b. 安装依赖**

```bash
pip install -r requirements.txt
```

**c. 配置环境变量**

为了使用 OIDC 登录功能，您需要设置以下环境变量。如果不需要 OIDC，可以跳过此步骤。

```bash
export FLASK_SECRET_KEY='a_super_secret_key_for_flask_sessions'
export LAZYCAT_AUTH_OIDC_CLIENT_ID='YOUR_OIDC_CLIENT_ID'
export LAZYCAT_AUTH_OIDC_CLIENT_SECRET='YOUR_OIDC_CLIENT_SECRET'
export LAZYCAT_AUTH_OIDC_AUTH_URI='YOUR_OIDC_AUTH_URI'
export LAZYCAT_AUTH_OIDC_TOKEN_URI='YOUR_OIDC_TOKEN_URI'
export LAZYCAT_AUTH_OIDC_USERINFO_URI='YOUR_OIDC_USERINFO_URI'
export OIDC_JWKS_URI='YOUR_OIDC_JWKS_URI'
export OIDC_REDIRECT_URI='http://localhost:5001/oidc/callback' # 本地测试用
```

**d. 运行应用**

首次运行前，请删除可能存在的旧数据库文件 `instance/tasks.db`，以确保应用新的数据表结构。

```bash
python family_notifier/app.py
```

应用将在 `http://127.0.0.1:5001` 上可用。

### 2. 使用 Docker Compose 运行 (推荐)

这是最简单的启动方式，推荐用于生产或快速测试。

**a. 准备工作**

- 安装 [Docker](https://www.docker.com/get-started) 和 [Docker Compose](https://docs.docker.com/compose/install/)。

**b. 配置环境变量**

在项目根目录下创建一个 `.env` 文件，并填入您的 OIDC 配置信息。`docker-compose` 会自动加载这个文件。

**.env 文件示例:**
```env
FLASK_SECRET_KEY=a_very_strong_and_random_secret_key

# OIDC Configuration
LAZYCAT_AUTH_OIDC_CLIENT_ID=YOUR_OIDC_CLIENT_ID
LAZYCAT_AUTH_OIDC_CLIENT_SECRET=YOUR_OIDC_CLIENT_SECRET
LAZYCAT_AUTH_OIDC_AUTH_URI=YOUR_OIDC_AUTH_URI
LAZYCAT_AUTH_OIDC_TOKEN_URI=YOUR_OIDC_TOKEN_URI
LAZYCAT_AUTH_OIDC_USERINFO_URI=YOUR_OIDC_USERINFO_URI
OIDC_JWKS_URI=YOUR_OIDC_JWKS_URI
OIDC_REDIRECT_URI=http://localhost:5001/oidc/callback
```

**c. 构建并启动服务**

```bash
docker-compose up --build
```

应用将在 `http://localhost:5001` 上可用。数据库文件会通过 Docker 卷持久化存储在 `./instance` 目录中。

## 📂 项目结构

```
.
├── family_notifier/         # Flask 应用模块
│   ├── static/              # CSS, JS 文件
│   ├── templates/           # HTML 模板
│   └── app.py               # 应用主逻辑
├── instance/                # 数据库文件存放目录 (自动生成)
├── .dockerignore            # Docker 构建时忽略的文件
├── .gitignore               # Git 版本控制忽略的文件
├── docker-compose.yml       # Docker Compose 配置文件
├── Dockerfile               # Docker 镜像构建文件
├── README.md                # 项目说明文件
└── requirements.txt         # Python 依赖列表
```
