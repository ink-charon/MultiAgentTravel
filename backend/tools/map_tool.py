"""地图工具 — 高德地图 API 封装"""

import httpx
from .base import BaseTool, ToolResult


class MapTool(BaseTool):
    """高德地图 API 工具"""

    name = "map_query"
    description = "使用高德地图进行地理编码、POI搜索、路线规划等操作"

    parameters = {
        "action": {
            "type": "string",
            "description": "操作类型：'geocode'（地址转经纬度）、'poi_search'（搜索周边POI）、'route'（路线规划）",
        },
        "address": {
            "type": "string",
            "description": "地址或地名（geocode 时使用）",
        },
        "keywords": {
            "type": "string",
            "description": "搜索关键词（poi_search 时使用），如 '酒店'、'餐厅'、'景点'",
        },
        "city": {
            "type": "string",
            "description": "城市名称（poi_search 时使用）",
        },
        "origin": {
            "type": "string",
            "description": "起点经纬度，格式 'lng,lat'（route 时使用）",
        },
        "destination": {
            "type": "string",
            "description": "终点经纬度，格式 'lng,lat'（route 时使用）",
        },
    }

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.base_url = "https://restapi.amap.com/v3"

    async def execute(self, action: str, **kwargs) -> ToolResult:
        """执行地图操作"""
        try:
            if action == "geocode":
                return await self._geocode(kwargs.get("address", ""))
            elif action == "poi_search":
                return await self._poi_search(
                    kwargs.get("keywords", ""),
                    kwargs.get("city", ""),
                )
            elif action == "route":
                return await self._route_plan(
                    kwargs.get("origin", ""),
                    kwargs.get("destination", ""),
                )
            else:
                return ToolResult(success=False, error=f"未知操作: {action}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def _geocode(self, address: str) -> ToolResult:
        """地理编码"""
        if not self.api_key:
            return self._mock_geocode(address)

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/geocode/geo",
                params={"key": self.api_key, "address": address},
                timeout=10.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "1" and data.get("geocodes"):
                    geo = data["geocodes"][0]
                    location = geo["location"].split(",")
                    return ToolResult(
                        success=True,
                        data={
                            "address": address,
                            "lng": float(location[0]),
                            "lat": float(location[1]),
                            "formatted_address": geo.get("formatted_address", address),
                        },
                    )

        return self._mock_geocode(address)

    async def _poi_search(self, keywords: str, city: str) -> ToolResult:
        """POI 搜索"""
        if not self.api_key:
            return self._mock_poi(keywords, city)

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/place/text",
                params={
                    "key": self.api_key,
                    "keywords": keywords,
                    "city": city,
                    "offset": 10,
                },
                timeout=10.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "1":
                    pois = []
                    for p in data.get("pois", []):
                        loc = p["location"].split(",")
                        pois.append({
                            "name": p.get("name"),
                            "address": p.get("address"),
                            "lng": float(loc[0]),
                            "lat": float(loc[1]),
                            "type": p.get("type"),
                            "rating": p.get("biz_ext", {}).get("rating", "N/A"),
                        })
                    return ToolResult(success=True, data=pois)

        return self._mock_poi(keywords, city)

    async def _route_plan(self, origin: str, destination: str) -> ToolResult:
        """路线规划"""
        if not self.api_key:
            return self._mock_route(origin, destination)

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/direction/driving",
                params={
                    "key": self.api_key,
                    "origin": origin,
                    "destination": destination,
                },
                timeout=10.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "1":
                    route = data["route"]["paths"][0]
                    return ToolResult(
                        success=True,
                        data={
                            "distance": int(route["distance"]),
                            "duration": int(route["duration"]),
                            "cost": round(int(route["distance"]) / 1000 * 1.5, 1),
                        },
                    )

        return self._mock_route(origin, destination)

    # ---- 模拟数据 ----

    def _mock_geocode(self, address: str) -> ToolResult:
        import hashlib
        import random

        random.seed(int(hashlib.md5(address.encode()).hexdigest()[:8], 16))
        return ToolResult(
            success=True,
            data={
                "address": address,
                "lng": round(random.uniform(120.0, 121.5), 6),
                "lat": round(random.uniform(30.0, 30.5), 6),
                "formatted_address": f"浙江省杭州市{address}",
            },
            metadata={"source": "模拟数据", "is_mock": True},
        )

    def _mock_poi(self, keywords: str, city: str) -> ToolResult:
        import random

        pois = [
            {"name": f"{city}西湖景区", "address": f"{city}市西湖区龙井路1号", "lng": 120.141, "lat": 30.238, "type": "风景名胜", "rating": "4.9"},
            {"name": f"{city}灵隐寺", "address": f"{city}市西湖区法云弄1号", "lng": 120.103, "lat": 30.248, "type": "寺庙", "rating": "4.7"},
            {"name": f"{city}如家酒店(西湖店)", "address": f"{city}市上城区延安路100号", "lng": 120.165, "lat": 30.255, "type": "酒店", "rating": "4.3"},
            {"name": f"{city}外婆家(湖滨店)", "address": f"{city}市上城区湖滨路25号", "lng": 120.168, "lat": 30.250, "type": "餐饮", "rating": "4.5"},
        ]
        filtered = [p for p in pois if keywords in p.get("type", "") or keywords in p.get("name", "")]
        if not filtered:
            filtered = pois[:3]

        return ToolResult(success=True, data=filtered, metadata={"source": "模拟数据", "is_mock": True})

    def _mock_route(self, origin: str, destination: str) -> ToolResult:
        import random

        distance = random.randint(3000, 15000)
        return ToolResult(
            success=True,
            data={
                "distance": distance,
                "duration": distance // 50 + random.randint(5, 20),
                "cost": round(distance / 1000 * 1.5, 1),
            },
            metadata={"source": "模拟数据", "is_mock": True},
        )
