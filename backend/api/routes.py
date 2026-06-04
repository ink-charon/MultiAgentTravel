"""API 路由"""

import uuid
import logging
from fastapi import APIRouter, HTTPException

from .schemas import (
    ChatRequest, ChatResponse, KnowledgeStats, KnowledgeSearchRequest,
)

router = APIRouter(prefix="/api", tags=["travel"])
logger = logging.getLogger("api")

_services: dict = {}


def init_services(services: dict):
    global _services
    _services = services


# ========== 聊天 ==========


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    travel_agent = _services.get("travel_agent")
    if not travel_agent:
        raise HTTPException(status_code=500, detail="服务未初始化")

    session_id = request.session_id or f"session_{uuid.uuid4().hex[:12]}"

    try:
        result = await travel_agent.run(request.message)
        plan = result.get("plan", "")
        map_json = result.get("map_json")

        return ChatResponse(
            session_id=session_id,
            plan=plan,
            map_json=map_json,
            route_image=result.get("route_image", ""),
            need_input=not bool(plan),
            error=None,
        )
    except Exception as e:
        logger.error(f"Agent 执行失败: {e}", exc_info=True)
        return ChatResponse(session_id=session_id, error=str(e))


# ========== 知识库 ==========


@router.get("/knowledge/stats", response_model=KnowledgeStats)
async def knowledge_stats():
    vs = _services.get("vector_store")
    if not vs:
        return KnowledgeStats()
    return KnowledgeStats(
        chat_history=vs.count("chat_history"),
        travel_docs=vs.count("travel_docs"),
    )


@router.post("/knowledge/cleanup")
async def knowledge_cleanup():
    forgetting = _services.get("forgetting_manager")
    if not forgetting:
        raise HTTPException(status_code=500, detail="遗忘管理器未初始化")
    result = await forgetting.check_and_clean()
    return {"status": "ok", "stats": result}


@router.post("/knowledge/search")
async def knowledge_search(request: KnowledgeSearchRequest):
    retriever = _services.get("retriever")
    if not retriever:
        raise HTTPException(status_code=500, detail="知识库未初始化")

    results = retriever.search(
        query=request.query,
        collection="travel_docs",
        top_k=request.top_k,
    )
    return {"results": results}


# ========== 健康检查 ==========


@router.get("/health")
async def health():
    llm_model = ""
    tool_count = 0
    agent = _services.get("travel_agent")
    if agent:
        llm_model = getattr(agent, "model_name", "") or "deepseek"
        tool_count = len(agent.tools) if hasattr(agent, "tools") else 5

    return {
        "status": "ok",
        "llm": llm_model,
        "tools": tool_count,
    }
