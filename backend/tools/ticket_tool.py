"""票务查询工具 — 当前使用模拟数据"""

from .base import BaseTool, ToolResult


class TicketTool(BaseTool):
    """查询车票/机票信息"""

    name = "ticket_query"
    description = "查询从出发地到目的地的交通票务信息，包括机票和火车票的价格、时间"

    parameters = {
        "from_city": {
            "type": "string",
            "description": "出发城市，如 '北京'",
        },
        "to_city": {
            "type": "string",
            "description": "目的地城市，如 '杭州'",
        },
        "date": {
            "type": "string",
            "description": "出发日期，格式 YYYY-MM-DD",
        },
        "transport_type": {
            "type": "string",
            "description": "交通类型：'flight'（飞机）、'train'（火车）、'all'（全部）",
        },
    }

    def __init__(self, use_mock: bool = True):
        self.use_mock = use_mock

    async def execute(
        self,
        from_city: str,
        to_city: str,
        date: str,
        transport_type: str = "all",
        **kwargs,
    ) -> ToolResult:
        """查询票务"""
        return self._mock_tickets(from_city, to_city, date, transport_type)

    def _mock_tickets(
        self,
        from_city: str,
        to_city: str,
        date: str,
        transport_type: str,
    ) -> ToolResult:
        """生成模拟票务数据"""
        import random

        flights = []
        trains = []

        if transport_type in ("flight", "all"):
            airlines = ["中国国航", "南方航空", "东方航空", "海南航空", "春秋航空"]
            for i in range(4):
                hour = random.randint(7, 21)
                flights.append({
                    "type": "飞机",
                    "flight_no": f"{random.choice(['CA', 'CZ', 'MU', 'HU'])}{random.randint(1000, 9999)}",
                    "airline": random.choice(airlines),
                    "departure_time": f"{date} {hour:02d}:{random.choice(['00', '15', '30', '45'])}",
                    "arrival_time": f"{date} {hour + 2:02d}:{random.choice(['00', '15', '30', '45'])}",
                    "duration": f"{random.randint(2, 3)}h{random.choice([15, 30, 45])}m",
                    "price": random.randint(350, 1800),
                    "discount": f"{random.choice([3, 4, 5, 6, 7, 8, 9])}折",
                })

        if transport_type in ("train", "all"):
            train_types = ["G-高铁", "D-动车", "K-快速", "Z-直达"]
            for i in range(4):
                hour = random.randint(6, 20)
                trains.append({
                    "type": "火车",
                    "train_no": f"{random.choice(['G', 'D', 'K', 'Z'])}{random.randint(100, 9999)}",
                    "train_type": random.choice(train_types),
                    "departure_time": f"{date} {hour:02d}:{random.choice(['00', '15', '30', '45'])}",
                    "arrival_time": f"{date} {hour + random.randint(4, 8):02d}:{random.choice(['00', '15', '30', '45'])}",
                    "duration": f"{random.randint(4, 8)}h{random.choice([15, 30, 45])}m",
                    "price": random.randint(200, 900),
                    "seat_type": random.choice(["二等座", "一等座", "硬卧", "软卧"]),
                })

        return ToolResult(
            success=True,
            data={
                "from": from_city,
                "to": to_city,
                "date": date,
                "flights": flights,
                "trains": trains,
                "recommendation": self._pick_best(flights + trains),
            },
            metadata={"source": "模拟数据", "is_mock": True},
        )

    def _pick_best(self, items: list) -> dict | None:
        """选择推荐项：价格和时间平衡"""
        if not items:
            return None
        # 按价格排序取前 2 个性价比最高的
        sorted_items = sorted(items, key=lambda x: x["price"])
        return sorted_items[0]
