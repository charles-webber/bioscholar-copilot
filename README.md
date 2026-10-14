# BioScholar Copilot

一个把 BioAgent 封装为 Web 产品的 AI 全栈练习项目。

## Week 1 功能

- FastAPI 健康检查与 Chat API
- Demo/现有 Biomedical Agent 可切换适配器
- Next.js 聊天表单、加载状态和错误状态
- 后端接口测试

## 启动

请分别启动 `apps/api` 和 `apps/web`，环境变量模板见各目录的
启动命令：
前端：
cd apps/api/web
npm run dev 
后端：cd C:\Users\admin\Documents\code\bioscholar-copilot\apps\api
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --port 8000
`.env.example` 与 `.env.local.example`。

## 截图

![Week 1 chat](docs/images/week1-chat.png)