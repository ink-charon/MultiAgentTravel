"""Pydantic 数据模型"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """聊天请求"""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "帮我规划6月10日到6月15日从北京去杭州的旅行，预算5000元",
                }
            ]
        }
    }

    message: str = Field(
        ...,
        description="旅行需求描述",
        min_length=1,
        examples=["帮我规划从北京去杭州的旅行"],
    )
    session_id: str | None = Field(None, description="会话ID，新会话为空")


class MapSpot(BaseModel):
    """地图节点"""
    name: str
    lng: float
    lat: float
    day: int
    order: int = 1
    time: str = ""
    activity: str = ""
    transport: str = ""
    cost: str = ""


class DayRoute(BaseModel):
    """单天路线"""
    day: int
    color: str = "#E74C3C"
    coords: list[list[float]] = []


class MapData(BaseModel):
    """路线图数据"""
    city: str = ""
    center: list[float] = [39.9, 116.4]
    spots: list[MapSpot] = []
    routes: list[DayRoute] = []


class ChatResponse(BaseModel):
    """聊天响应"""
    session_id: str
    plan: str | None = None
    map_json: MapData | None = None
    route_image: str | None = None
    need_input: bool = False
    error: str | None = None


class KnowledgeStats(BaseModel):
    """知识库统计"""
    chat_history: int = 0
    travel_docs: int = 0


class KnowledgeSearchRequest(BaseModel):
    """知识库检索请求"""
    query: str = Field(..., min_length=1)
    top_k: int = Field(5, ge=1, le=20)
