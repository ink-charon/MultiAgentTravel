"""FastAPI 入口 — 智能旅行规划助手"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import config
from utils.logger import get_logger

config.ensure_dirs()
logger = get_logger("travel_planner", log_dir=config.LOGS_DIR, level=config.LOG_LEVEL)

_services: dict = {}


def init_services():
    logger.info("正在初始化服务...")

    # Prompt
    from prompts import PromptLoader
    prompt_loader = PromptLoader(config.PROMPTS_DIR)
    logger.info(f"已加载 {len(prompt_loader.list_prompts())} 个提示词模板")

    # 工具
    from tools import (
        WeatherTool, TicketTool, SearchTool, MapTool, DrawingTool, ToolRegistry,
    )
    tool_registry = ToolRegistry()
    weather_tool = WeatherTool(api_key=config.WEATHER_API_KEY, api_host=config.WEATHER_API_HOST)
    ticket_tool = TicketTool(use_mock=config.USE_MOCK_TICKET)
    search_tool = SearchTool(api_key=config.TAVILY_API_KEY)
    map_tool = MapTool(api_key=config.AMAP_API_KEY)
    drawing_tool = DrawingTool(output_dir=config.IMAGES_DIR)

    tools = [weather_tool, ticket_tool, search_tool, map_tool, drawing_tool]
    for t in tools:
        tool_registry.register(t)
    logger.info(f"已注册 {len(tool_registry)} 个工具: {tool_registry.list_names()}")

    # 嵌入模型（先加载，传给 ChromaDB）
    from document import Embedder
    embedder = None
    try:
        embedder = Embedder(model_name=config.EMBEDDING_MODEL, cache_dir=config.MODELS_DIR, device="cpu")
        logger.info(f"嵌入模型已加载: {config.EMBEDDING_MODEL}")
    except Exception as e:
        logger.warning(f"嵌入模型加载失败: {e}")

    # 知识库（传入 embedder 确保检索可用）
    from knowledge import VectorStore, MemoryManager, ForgettingManager, Retriever

    vector_store = VectorStore(persist_dir=config.CHROMA_DIR, embedding_function=embedder)
    retriever = Retriever(vector_store)
    memory_manager = MemoryManager(vector_store)
    forgetting_manager = ForgettingManager(
        vector_store,
        decay_days=config.FORGETTING_DECAY_DAYS,
        importance_threshold=config.FORGETTING_THRESHOLD,
        retention_days=config.FORGETTING_RETENTION_DAYS,
        max_docs_per_destination=config.MAX_DOCS_PER_DESTINATION,
    )

    # 文档处理
    from document import TextSplitter, DocumentPipeline
    splitter = TextSplitter(chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP)
    doc_pipeline = DocumentPipeline(splitter=splitter, embedder=embedder, vector_store=vector_store)

    # Agent
    from agent import MultiTravelAgent
    travel_agent = MultiTravelAgent(
        tools=tools,
        prompt_loader=prompt_loader,
        debug=False,
        vector_store=vector_store,
        doc_pipeline=doc_pipeline,
        memory_manager=memory_manager,
    )

    logger.info("所有服务初始化完成")
    return {
        "prompt_loader": prompt_loader,
        "tool_registry": tool_registry,
        "vector_store": vector_store,
        "retriever": retriever,
        "memory_manager": memory_manager,
        "forgetting_manager": forgetting_manager,
        "doc_pipeline": doc_pipeline,
        "travel_agent": travel_agent,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _services
    try:
        _services = init_services()
        from api.routes import init_services as init_route_services
        init_route_services(_services)
    except Exception as e:
        logger.error(f"服务初始化失败: {e}")
        raise
    logger.info(f"服务已启动: http://{config.HOST}:{config.PORT}")
    yield
    logger.info("服务已关闭")


app = FastAPI(
    title="智能旅行规划助手",
    description="多 Agent 智能旅行规划系统",
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

config.IMAGES_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(config.IMAGES_DIR)), name="static")

# 前端静态文件
_frontend_dir = config.BASE_DIR.parent / "frontend"
if _frontend_dir.exists():
    app.mount("/app", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")

from api.routes import router
app.include_router(router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    from fastapi.exceptions import RequestValidationError
    from fastapi.responses import JSONResponse

    if isinstance(exc, RequestValidationError):
        return JSONResponse(status_code=422, content={
            "error": "请求格式错误",
            "detail": "请确保请求体是有效的 JSON，使用英文双引号",
        })
    logger.error(f"未处理异常: {exc}\n{traceback.format_exc()}")
    return JSONResponse(status_code=500, content={"error": str(exc)})


@app.get("/")
async def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=config.HOST, port=config.PORT, log_level=config.LOG_LEVEL.lower(), reload=True)
