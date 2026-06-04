"""天气查询工具 — 和风天气 API（Bearer 认证）"""

import logging
import httpx
from .base import BaseTool, ToolResult

logger = logging.getLogger("weather_tool")

# 中国主要城市 LocationID 映射（避免额外 API 调用）
CITY_IDS: dict[str, str] = {
    "北京": "101010100", "朝阳": "101010300", "海淀": "101010200",
    "上海": "101020100", "浦东": "101020600",
    "广州": "101280101", "深圳": "101280601",
    "杭州": "101210101", "宁波": "101210401", "温州": "101210701",
    "成都": "101270101", "重庆": "101040100",
    "南京": "101190101", "苏州": "101190401", "无锡": "101190201",
    "武汉": "101200101", "长沙": "101250101",
    "西安": "101110101", "郑州": "101180101",
    "青岛": "101120201", "济南": "101120101",
    "厦门": "101230201", "福州": "101230101",
    "大连": "101070201", "沈阳": "101070101",
    "昆明": "101290101", "大理": "101290201", "丽江": "101291401",
    "三亚": "101310201", "海口": "101310101",
    "哈尔滨": "101050101", "长春": "101060101",
    "贵阳": "101260101", "南宁": "101300101", "桂林": "101300501",
    "拉萨": "101140101", "乌鲁木齐": "101130101",
    "天津": "101030100", "合肥": "101220101", "南昌": "101240101",
    "石家庄": "101090101", "太原": "101100101", "呼和浩特": "101080101",
    "兰州": "101160101", "西宁": "101150101", "银川": "101170101",
    "珠海": "101280701", "佛山": "101280800", "东莞": "101281601",
    "黄山": "101221001", "张家界": "101251101", "洛阳": "101180901",
    "扬州": "101190601", "绍兴": "101210501", "舟山": "101211101",
    "秦皇岛": "101091101", "烟台": "101120501", "威海": "101121301",
    "北海": "101301301", "西双版纳": "101291601", "香格里拉": "101291501",
}


class WeatherTool(BaseTool):
    """查询指定城市天气（和风天气 API v7）"""

    name = "weather_query"
    description = "查询指定城市未来7天的天气，含温度、天气状况、风力、湿度、紫外线等"

    parameters = {
        "city": {"type": "string", "description": "城市名称，如 '杭州'"},
        "start_date": {"type": "string", "description": "开始日期 YYYY-MM-DD"},
        "end_date": {"type": "string", "description": "结束日期 YYYY-MM-DD"},
    }

    def __init__(self, api_key: str = "", api_host: str = ""):
        self.api_key = api_key
        self.api_host = api_host or "devapi.qweather.com"

    async def execute(self, city: str, start_date: str, end_date: str, **kwargs) -> ToolResult:
        if not self.api_key:
            logger.info("和风天气 Key 未配置，使用模拟数据")
            return self._mock_weather(city, start_date, end_date)

        location_id = self._find_location_id(city)

        if not location_id:
            logger.warning(f"未找到城市 '{city}' 的 LocationID，使用模拟数据")
            return self._mock_weather(city, start_date, end_date)

        try:
            async with httpx.AsyncClient() as client:
                logger.info(f"查询天气: {city}({location_id}) @ {self.api_host}")
                resp = await client.get(
                    f"https://{self.api_host}/v7/weather/7d",
                    params={"location": location_id, "key": self.api_key},
                    timeout=10.0,
                )

                if resp.status_code != 200:
                    logger.error(f"天气 API 返回 HTTP {resp.status_code}: {resp.text[:200]}")
                    return self._mock_weather(city, start_date, end_date)

                data = resp.json()
                if data.get("code") != "200":
                    logger.error(f"天气 API 错误: code={data.get('code')}")
                    return self._mock_weather(city, start_date, end_date)

                daily = data.get("daily", [])
                days = []
                for d in daily:
                    days.append({
                        "date": d.get("fxDate", ""),
                        "condition_day": d.get("textDay", ""),
                        "condition_night": d.get("textNight", ""),
                        "high_temp": int(d.get("tempMax", 0)),
                        "low_temp": int(d.get("tempMin", 0)),
                        "humidity": d.get("humidity", ""),
                        "wind": f"{d.get('windDirDay', '')} {d.get('windScaleDay', '')}级",
                        "precip": d.get("precip", "0"),
                        "uvIndex": d.get("uvIndex", ""),
                    })

                logger.info(f"获取到 {len(days)} 天真实天气数据")
                return ToolResult(
                    success=True,
                    data=days,
                    metadata={"city": city, "source": "和风天气", "location_id": location_id},
                )

        except httpx.TimeoutException:
            logger.error("和风天气 API 超时")
            return self._mock_weather(city, start_date, end_date)
        except Exception as e:
            logger.error(f"天气查询异常: {e}")
            return self._mock_weather(city, start_date, end_date)

    def _find_location_id(self, city: str) -> str | None:
        """查找城市的 LocationID"""
        # 精确匹配
        if city in CITY_IDS:
            return CITY_IDS[city]

        # 模糊匹配（如"杭州城区"匹配"杭州"）
        city_clean = city.replace("市", "").replace("区", "").replace("县", "").strip()
        for name, lid in CITY_IDS.items():
            if city_clean in name or name in city_clean:
                return lid

        return None

    def _mock_weather(self, city: str, start_date: str, end_date: str) -> ToolResult:
        from datetime import datetime, timedelta
        import random

        conditions = ["晴", "多云", "阴", "小雨", "阵雨"]
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        days = []
        current = start
        while current <= end:
            c = random.choice(conditions)
            days.append({
                "date": current.strftime("%Y-%m-%d"),
                "condition_day": c,
                "condition_night": random.choice(["多云", "晴"]),
                "high_temp": random.randint(22, 35),
                "low_temp": random.randint(15, 25),
                "humidity": str(random.randint(40, 90)),
                "wind": f"{random.choice(['东北风', '西南风', '北风', '东南风'])} {random.randint(1, 4)}级",
                "precip": str(random.randint(0, 60)),
                "uvIndex": str(random.randint(1, 8)),
            })
            current += timedelta(days=1)

        return ToolResult(
            success=True,
            data=days,
            metadata={"city": city, "source": "模拟数据", "is_mock": True},
        )
