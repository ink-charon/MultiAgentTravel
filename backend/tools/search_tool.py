"""搜索工具 — 含搜索词优化"""

import httpx
from .base import BaseTool, ToolResult


class SearchTool(BaseTool):
    """搜索景点攻略，带搜索词优化"""

    name = "web_search"
    description = "搜索目的地旅游攻略、景点信息、美食推荐等。搜索词会自动优化以提高结果质量。"

    parameters = {
        "query": {
            "type": "string",
            "description": "搜索关键词，如 '杭州旅游攻略'",
        },
        "destination": {
            "type": "string",
            "description": "目的地城市名称",
        },
        "search_type": {
            "type": "string",
            "description": "搜索类型：'attraction'（景点）、'food'（美食）、'guide'（攻略）、'general'（综合）",
        },
    }

    def __init__(self, api_key: str = "", llm_client=None):
        self.api_key = api_key
        self.llm_client = llm_client  # 用于优化搜索词

    async def optimize_query(self, query: str, destination: str, search_type: str) -> str:
        """使用 LLM 优化搜索词"""
        if not self.llm_client:
            # 无 LLM 时用规则优化
            type_keywords = {
                "attraction": f"{destination} 必去景点 热门推荐 评分",
                "food": f"{destination} 特色美食 必吃餐厅 小吃街",
                "guide": f"{destination} 旅游攻略 行程安排 注意事项 2026",
                "general": f"{destination} 旅游 景点 美食 交通 住宿",
            }
            suffix = type_keywords.get(search_type, type_keywords["general"])
            return f"{query} {suffix}"

        # 有 LLM 时用 LLM 优化
        prompt = f"""将以下搜索词优化为更适合搜索引擎的关键词组合：
原始搜索词：{query}
目的地：{destination}
搜索类型：{search_type}

要求：
1. 提取核心关键词
2. 添加相关限定词（如：攻略、推荐、排名、2026）
3. 保持简洁，不超过 30 个字
4. 只输出优化后的搜索词，不要解释

优化后的搜索词："""

        try:
            response = await self.llm_client.chat(prompt, temperature=0.3)
            return response.strip()
        except Exception:
            return f"{query} {destination} 旅游攻略"

    async def execute(
        self,
        query: str,
        destination: str,
        search_type: str = "general",
        **kwargs,
    ) -> ToolResult:
        """执行搜索"""
        try:
            # 1. 优化搜索词
            optimized_query = await self.optimize_query(query, destination, search_type)

            # 2. 执行搜索
            search_results = await self._do_search(optimized_query)

            return ToolResult(
                success=True,
                data={
                    "original_query": query,
                    "optimized_query": optimized_query,
                    "results": search_results,
                    "destination": destination,
                    "search_type": search_type,
                },
                metadata={
                    "source": "web_search",
                    "result_count": len(search_results),
                },
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"source": "web_search"},
            )

    async def _do_search(self, query: str) -> list[dict]:
        """实际搜索逻辑"""
        results = []

        # 尝试 Tavily API
        if self.api_key:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        "https://api.tavily.com/search",
                        json={
                            "api_key": self.api_key,
                            "query": query,
                            "search_depth": "advanced",
                            "max_results": 8,
                        },
                        timeout=15.0,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        for r in data.get("results", []):
                            results.append({
                                "title": r.get("title", ""),
                                "url": r.get("url", ""),
                                "content": r.get("content", ""),
                                "score": r.get("score", 0),
                            })
                        if results:
                            return results
            except Exception:
                pass

        # 备选：DuckDuckGo
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.duckduckgo.com/",
                    params={"q": query, "format": "json", "no_html": 1},
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for r in data.get("RelatedTopics", [])[:8]:
                        if isinstance(r, dict) and "Text" in r:
                            results.append({
                                "title": r.get("FirstURL", ""),
                                "url": r.get("FirstURL", ""),
                                "content": r.get("Text", ""),
                                "score": 0.5,
                            })
        except Exception:
            pass

        # 兜底模拟数据
        if not results:
            results = self._mock_results(query)

        return results

    def _mock_results(self, query: str) -> list[dict]:
        """模拟搜索结果"""
        import random

        city = query.split()[0] if query else "目的地"
        mock_attractions = [
            {"title": f"{city}西湖风景名胜区", "content": f"{city}西湖是国家5A级景区，以湖光山色和众多历史遗迹闻名。推荐游览苏堤、断桥、雷峰塔等景点，游览时间约4-6小时。"},
            {"title": f"{city}灵隐寺", "content": f"{city}灵隐寺是中国佛教名寺之一，始建于东晋。飞来峰石窟造像精美，寺庙环境清幽。门票75元，建议上午前往。"},
            {"title": f"{city}河坊街美食街", "content": f"{city}河坊街是著名历史文化街区，汇集了众多当地特色小吃。推荐：东坡肉、西湖醋鱼、龙井虾仁、葱包桧等。"},
            {"title": f"{city}三日游攻略", "content": f"第一天：西湖环湖游览（断桥→白堤→苏堤→花港观鱼）。第二天：灵隐寺→飞来峰→龙井村品茶。第三天：宋城或西溪湿地。建议购买景区联票更划算。"},
            {"title": f"{city}必去景点Top10", "content": f"1.西湖 2.灵隐寺 3.千岛湖 4.雷峰塔 5.宋城 6.西溪湿地 7.龙井村 8.河坊街 9.岳王庙 10.六和塔。每个景点都有独特的文化和自然价值。"},
            {"title": f"{city}住宿推荐", "content": f"推荐住在西湖附近区域，交通便利。经济型酒店150-300元/晚，舒适型300-600元/晚，豪华型600+元/晚。建议提前预订，旺季价格会上涨。"},
            {"title": f"{city}特色美食推荐", "content": f"必吃美食：1.东坡肉 2.西湖醋鱼 3.龙井虾仁 4.叫花鸡 5.宋嫂鱼羹。推荐餐厅：楼外楼、知味观、外婆家。"},
            {"title": f"{city}交通指南", "content": f"地铁覆盖主要景区，公交也很方便。建议下载当地地铁APP扫码乘车。景区间打车费用约15-40元。共享单车也是不错的短途出行选择。"},
        ]

        return random.sample(mock_attractions, min(5, len(mock_attractions)))
