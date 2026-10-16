# BioScholar Copilot

基于 **React + FastAPI + Biomedical Agent** 的 AI 全栈实习练习项目。

## 技术栈

- **前端**：React + TypeScript + Vite
- **后端**：FastAPI + Pydantic
- **数据库**：PostgreSQL + SQLAlchemy + Alembic
- **AI**：Biomedical Agent
- **测试**：Pytest

## Week 1 功能

- FastAPI 健康检查与 Chat API
- Demo / Biomedical Agent 可切换适配器
- React 聊天页面：输入、发送、Loading、错误提示及回答展示
- 后端接口测试

## 本地启动

### 后端

```powershell
cd apps/api
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --port 8000
```

API 文档：http://localhost:8000/docs

### 前端

新开终端：

```powershell
cd apps/web
npm install
npm run dev
```

访问：http://localhost:5173

首次使用需参考 `apps/api/.env.example` 配置环境变量。

## 测试

```powershell
cd apps/api
python -m pytest -q
```

```powershell
cd apps/web
npm run lint
npm run build
```

## 截图

![Week 1 Chat](docs/images/week1-chat.png)

> 仅用于生物医学学习，不提供临床诊断或治疗建议。
