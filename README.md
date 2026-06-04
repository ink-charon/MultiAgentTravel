# ✈️ 智能旅行规划助手

> 基于 LangChain 多 Agent 协作的智能旅行规划系统 | Python 3.12 + FastAPI + ChromaDB

## 功能简介

- 🤖 **多 Agent 协作**: Supervisor + 3 个专业子 Agent（天气/票务/景点）
- 🌤️ **真实 API**: 和风天气、高德地图、Tavily 搜索
- 🗺️ **交互式地图**: 基于 Leaflet + 高德瓦片，节点可点击查看详情
- 📚 **RAG 知识库**: ChromaDB 向量存储，跨会话检索，三级遗忘机制
- 💬 **多轮对话**: 终端 + Web 双界面，iOS 风格前端
- 📊 **Markdown 表格输出**: 每日行程表格化展示

## 快速启动

### 1. 创建环境 + 安装依赖

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 配置 API Key

复制 `.env.example` 为 `.env`，填入 API Key：

| 变量 | 说明 | 必需 |
|------|------|------|
| `LLM_API_KEY` | DeepSeek API Key | ✅ 是 |
| `LLM_BASE_URL` | API 地址 | 默认 DeepSeek |
| `LLM_MODEL` | 模型名称 | 默认 deepseek-chat |
| `WEATHER_API_KEY` | 和风天气 Key | 否(有模拟数据) |
| `WEATHER_API_HOST` | 和风天气 API Host | 否 |
| `AMAP_API_KEY` | 高德地图 Key | 否(有内置坐标库) |
| `TAVILY_API_KEY` | Tavily 搜索 Key | 否(有模拟数据) |

### 3. 启动

```bash
# Web 前端
python main.py
# 浏览器打开 → http://127.0.0.1:8000/app/

# 终端版本
python cli.py
```

## 项目结构

```
├── backend/
│   ├── agent/          # 🧠 多 Agent 系统
│   ├── tools/          # 🔧 5 个工具 (天气/票务/搜索/地图/绘图)
│   ├── knowledge/      # 📚 向量知识库 + 遗忘机制
│   ├── document/       # 📄 文档处理管线
│   ├── prompts/        # 💬 YAML 提示词模板
│   ├── api/            # 🌐 FastAPI 路由
│   ├── main.py         # Web 入口
│   └── cli.py          # 终端入口
├── frontend/
│   ├── index.html      # iOS 风格 SPA
│   ├── css/ios.css     # Cupertino 样式
│   └── js/             # 面板逻辑 (chat/map/knowledge)
└── data/               # ChromaDB / 图片 / 日志
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat` | 发送旅行规划请求 |
| GET | `/api/knowledge/stats` | 知识库统计 |
| POST | `/api/knowledge/cleanup` | 手动遗忘清理 |
| POST | `/api/knowledge/search` | 知识库检索 |
| GET | `/api/health` | 健康检查 |

## 文档

| 文件 | 用途 |
|------|------|
| [TECH_DOC.md](TECH_DOC.md) | 📝 技术答辩文档 (PPT 参考) |
| [ARCHITECTURE_PLAN.md](ARCHITECTURE_PLAN.md) | 🏗️ 架构设计文档 |
| [API_AND_FRONTEND_INTEGRATION.md](API_AND_FRONTEND_INTEGRATION.md) | 🔌 API 接口 & 前端接入 |

