"""多 Agent 协作 — LangChain 原生实现（Supervisor + 专业子 Agent）"""

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
import re

from langchain_core.tools import StructuredTool
from langchain_core.messages import HumanMessage

from config import config


def _make_args_schema(tool_instance):
    """根据工具的 parameters 动态生成 Pydantic args_schema"""
    from pydantic import BaseModel, Field, create_model

    if not hasattr(tool_instance, "parameters") or not tool_instance.parameters:
        return None

    fields = {}
    for name, info in tool_instance.parameters.items():
        ptype = info.get("type", "string")
        desc = info.get("description", "")
        default = ...  # required

        if ptype == "string":
            fields[name] = (str, Field(description=desc))
        elif ptype == "number":
            fields[name] = (float, Field(description=desc))
        elif ptype == "integer":
            fields[name] = (int, Field(description=desc))
        elif ptype == "array":
            fields[name] = (list, Field(description=desc, default_factory=list))
        elif ptype == "object":
            fields[name] = (dict, Field(description=desc, default_factory=dict))

    if not fields:
        return None

    return create_model(f"{tool_instance.name}_args", **fields)


def _wrap_tool(tool_instance) -> StructuredTool:
    """自定义工具 → LangChain StructuredTool（带完整参数 schema）"""
    schema = _make_args_schema(tool_instance)

    # 构建参数描述（文本形式，兜底）
    param_desc = ""
    if hasattr(tool_instance, "parameters") and tool_instance.parameters:
        params = []
        for name, info in tool_instance.parameters.items():
            ptype = info.get("type", "string")
            params.append(f"  - {name} ({ptype}): {info.get('description', '')}")
        if params:
            param_desc = "\n参数:\n" + "\n".join(params)

    return StructuredTool.from_function(
        name=tool_instance.name,
        description=tool_instance.description + param_desc,
        coroutine=tool_instance.execute,
        args_schema=schema,
    )


def _make_llm(temp: float = 0.7) -> ChatOpenAI:
    return ChatOpenAI(
        model=config.LLM_MODEL,
        api_key=config.LLM_API_KEY,
        base_url=config.LLM_BASE_URL,
        temperature=temp,
        max_tokens=4096,
    )


class MultiTravelAgent:
    """多 Agent 协作旅行规划系统

    架构：Supervisor 调度 → 3 个专业子 Agent（并行工具调用）
    - WeatherAgent: 天气分析
    - TicketAgent: 票务查询
    - AttractionAgent: 景点搜索
    → 最终由 Supervisor 综合生成计划
    """

    def __init__(
        self,
        tools: list,
        prompt_loader=None,
        debug: bool = False,
        vector_store=None,
        doc_pipeline=None,
        memory_manager=None,
    ):
        self.tools = tools
        self.prompt_loader = prompt_loader
        self.debug = debug
        self.vector_store = vector_store
        self.doc_pipeline = doc_pipeline
        self.memory_manager = memory_manager

        # 按功能分发工具给子 Agent
        tool_map = {t.name: t for t in tools}
        self._tool_map = tool_map

        # 子 Agent 的 LangChain 工具
        self._weather_tools = [_wrap_tool(tool_map["weather_query"])]
        self._ticket_tools = [_wrap_tool(tool_map["ticket_query"])]
        self._search_tools = [_wrap_tool(tool_map["web_search"]), _wrap_tool(tool_map["map_query"])]
        self._draw_tool = _wrap_tool(tool_map["draw_route_map"])

        # 所有子 Agent 输出的工具（供 Supervisor 调用）
        self._all_sub_tools = self._weather_tools + self._ticket_tools + self._search_tools + [self._draw_tool]

        # 构建 Agent 图
        self._build_agents(debug)

    def _load_prompt(self, name: str, fallback: str) -> str:
        if self.prompt_loader:
            try:
                return self.prompt_loader.get_system_prompt(name)
            except Exception:
                pass
        return fallback

    def _build_agents(self, debug: bool):
        """构建 Supervisor + 子 Agent"""
        from datetime import date
        today = date.today().strftime("%Y-%m-%d")

        # ---- 子 Agent 1: 天气分析 ----
        weather_prompt = self._load_prompt("weather", "你是天气分析助手。")
        weather_prompt += f"\n\n当前日期：{today}\n调用 weather_query 获取数据后，用中文总结天气趋势、穿衣建议、活动建议。"

        self.weather_agent = create_agent(
            model=_make_llm(0.3),
            tools=self._weather_tools,
            system_prompt=weather_prompt,
            debug=debug,
        )

        # ---- 子 Agent 2: 票务查询 ----
        ticket_prompt = self._load_prompt("ticket", "你是票务查询助手。")
        ticket_prompt += f"\n\n当前日期：{today}\n调用 ticket_query 获取数据后，用中文总结交通选项，推荐最优方案。"

        self.ticket_agent = create_agent(
            model=_make_llm(0.3),
            tools=self._ticket_tools,
            system_prompt=ticket_prompt,
            debug=debug,
        )

        # ---- 子 Agent 3: 景点搜索 ----
        attraction_prompt = self._load_prompt("attraction", "你是景点推荐助手。")
        attraction_prompt += f"\n\n当前日期：{today}\n调用 web_search 搜索攻略，调用 map_query 查位置。总结推荐景点和美食。"

        self.attraction_agent = create_agent(
            model=_make_llm(0.5),
            tools=self._search_tools,
            system_prompt=attraction_prompt,
            debug=debug,
        )

        # ---- Supervisor Agent（调度所有子 Agent + 生成最终计划）----
        supervisor_prompt = self._load_prompt("travel_planner", "你是旅行规划主管。")
        supervisor_prompt += f"""

当前日期：{today}
今天是{today}。

## ⚠️ 知识库优先（RAG）- 重要！
用户消息中如果包含「📚 知识库」「📄 已有攻略缓存」说明向量库中有历史数据：
- **优先复用缓存**，不要再重复调用 weather_query / web_search
- 在回复中明确告知用户：如「根据知识库，约X天前你问过类似问题」
- 只有当缓存与当前需求**明显不匹配**时才重新调用工具
- 用户偏好（👤 部分）用于个性化推荐

## 你管理的子 Agent（通过工具调用）
- **weather_query** → Weather Agent：查询并分析目的地天气
- **ticket_query** → Ticket Agent：查询交通票务并推荐最优方案
- **web_search** → Attraction Agent：搜索景点攻略和美食推荐
- **map_query** → 查询地理位置坐标
- **draw_route_map** → 生成路线地图。**必须**从每日行程表格中提取每个景点的完整信息传入：
  参数 spots: [{{"name":"西湖","day":1,"time":"08:00-11:30","activity":"环湖游览","transport":"步行","cost":"免费"}}, ...]
  参数 city: 目的地城市名
  参数 title: 地图标题
  **不要遗漏 time/activity/transport/cost 字段**

## 工作流程
1. **先检查知识库缓存**，有则复用并在回复中告知用户（如：「根据X天前的记录...」）
2. 提取目的地、日期、预算，缺失的信息用合理默认值（出发地默认用户当前所在城市附近，预算默认3000元）
3. **仅当缓存不匹配时**才调用 weather_query / ticket_query / web_search
4. 根据数据规划每日行程
5. **必须调用 draw_route_map** 生成路线图（从行程中提取景点列表传入）
6. 输出完整旅行计划，包含路线图路径

## 重要规则
- 尽量一次性完成规划，不要反复追问用户
- 缺失出发地时假设为「广州」等省会城市，预算默认3000元
- 每次都必须调用 draw_route_map 工具画路线图

## 输出要求
- 每日行程用 **Markdown 表格**: | 时间 | 活动 | 地点 | 费用 |
- 预算总览用表格
- 路线图路径写为 `/static/route_xxx.html` 格式，不要写成绝对路径
- 附天气提示和注意事项"""

        self.supervisor_agent = create_agent(
            model=_make_llm(0.7),
            tools=self._all_sub_tools,
            system_prompt=supervisor_prompt,
            debug=debug,
        )

    async def _search_knowledge(self, query: str) -> dict:
        """检索知识库：查找相似对话和攻略，分析用户偏好

        Returns:
            {
                "similar_conversations": [{"content", "score", "timestamp", "chunk_id"}],
                "similar_docs": [{"content", "score", "chunk_id"}],
                "user_prefs": {"destinations": [...], "styles": [...], "budget_range": [...]},
            }
        """
        result = {
            "similar_conversations": [],
            "similar_docs": [],
            "user_prefs": {},
        }
        if not self.vector_store:
            return result

        try:
            # 1. 搜索相似对话（chat_history collection）
            chat_results = self.vector_store.query(
                query_text=query,
                collection="chat_history",
                n_results=5,
            )
            if chat_results and chat_results.get("documents"):
                for i, doc in enumerate(chat_results["documents"][0]):
                    score = 1 - chat_results["distances"][0][i]
                    meta = chat_results["metadatas"][0][i] if chat_results.get("metadatas") else {}
                    chunk_id = chat_results["ids"][0][i]
                    if score >= 0.5:
                        result["similar_conversations"].append({
                            "content": doc[:500],
                            "score": round(score, 3),
                            "timestamp": meta.get("timestamp", "未知"),
                            "chunk_id": chunk_id,
                        })

            # 2. 搜索相似攻略（travel_docs collection）
            doc_results = self.vector_store.query(
                query_text=query,
                collection="travel_docs",
                n_results=5,
            )
            if doc_results and doc_results.get("documents"):
                for i, doc in enumerate(doc_results["documents"][0]):
                    score = 1 - doc_results["distances"][0][i]
                    chunk_id = doc_results["ids"][0][i]
                    if score >= 0.5:
                        result["similar_docs"].append({
                            "content": doc[:500],
                            "score": round(score, 3),
                            "chunk_id": chunk_id,
                        })

            # 3. 分析用户历史偏好
            prefs = await self._analyze_preferences(query)
            result["user_prefs"] = prefs

        except Exception as e:
            import logging
            logging.getLogger("travel_agent").warning(f"知识库检索异常: {e}")

        return result

    async def _analyze_preferences(self, query: str) -> dict:
        """从历史对话中分析用户偏好"""
        prefs = {"destinations": [], "styles": [], "budget_range": ""}
        if not self.vector_store:
            return prefs

        try:
            all_chats = self.vector_store.get_all_with_metadata("chat_history")
            if not all_chats:
                return prefs

            # 提取历史目的地和偏好关键词
            dest_count = {}
            style_keywords = {
                "自然风光": ["自然", "山水", "风景", "湖", "山", "海", "湿地", "森林"],
                "美食": ["美食", "小吃", "吃", "餐厅", "特色"],
                "历史文化": ["历史", "文化", "古", "寺庙", "博物馆", "古迹"],
                "购物": ["购物", "买", "商场", "街"],
                "休闲度假": ["度假", "放松", "海", "温泉", "慢"],
            }
            style_count = {k: 0 for k in style_keywords}
            budgets = []

            import re
            for doc in all_chats:
                text = doc.get("document", "") + str(doc.get("metadata", {}))
                # 提取目的地
                for city in ["杭州", "北京", "上海", "成都", "西安", "三亚", "重庆", "丽江", "厦门", "珠海"]:
                    if city in text:
                        dest_count[city] = dest_count.get(city, 0) + 1
                # 提取风格
                for style, kws in style_keywords.items():
                    for kw in kws:
                        if kw in text:
                            style_count[style] += 1
                            break
                # 提取预算
                budget_match = re.search(r"(?:预算|花费).*?(\d+)", text)
                if budget_match:
                    budgets.append(int(budget_match.group(1)))

            # 取前 3 目的地
            prefs["destinations"] = [d for d, _ in sorted(dest_count.items(), key=lambda x: -x[1])[:3]]
            # 取前 2 偏好
            prefs["styles"] = [s for s, _ in sorted(style_count.items(), key=lambda x: -x[1])[:3] if style_count[s] > 0]
            # 预算范围
            if budgets:
                prefs["budget_range"] = f"{min(budgets)}-{max(budgets)}元"

        except Exception:
            pass

        return prefs

    def _build_knowledge_context(self, kb: dict) -> str:
        """构建知识库上下文（注入给 Agent）"""
        parts = []

        # 相似对话
        if kb.get("similar_conversations"):
            parts.append("## 📚 知识库：相似历史对话（高于相似度阈值 0.5）")
            for i, conv in enumerate(kb["similar_conversations"][:3], 1):
                time_str = conv.get("timestamp", "未知时间")
                parts.append(
                    f"**相似对话 {i}** (chunk: `{conv['chunk_id']}`, "
                    f"相似度: {conv['score']}, 时间: {time_str})\n"
                    f"> {conv['content'][:300]}"
                )
                # 告知用户多久前
                try:
                    from datetime import datetime, timezone
                    ts = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                    delta = datetime.now(timezone.utc) - ts
                    days = delta.days
                    if days > 0:
                        parts.append(f"  ⏰ 约 {days} 天前询问过\n")
                    else:
                        hours = delta.seconds // 3600
                        parts.append(f"  ⏰ 约 {hours} 小时前询问过\n")
                except Exception:
                    pass

        # 相似攻略
        if kb.get("similar_docs"):
            parts.append("## 📄 知识库：已有攻略缓存（可复用，减少搜索）")
            for i, doc in enumerate(kb["similar_docs"][:3], 1):
                parts.append(
                    f"**缓存 {i}** (chunk: `{doc['chunk_id']}`, 相似度: {doc['score']})\n"
                    f"> {doc['content'][:300]}"
                )

        # 用户偏好
        prefs = kb.get("user_prefs", {})
        if prefs.get("destinations") or prefs.get("styles"):
            parts.append("## 👤 用户历史偏好分析")
            if prefs.get("destinations"):
                parts.append(f"- 常去目的地: {', '.join(prefs['destinations'])}")
            if prefs.get("styles"):
                parts.append(f"- 旅行偏好: {', '.join(prefs['styles'])}")
            if prefs.get("budget_range"):
                parts.append(f"- 历史预算范围: {prefs['budget_range']}")

        return "\n".join(parts) if parts else ""

    async def run(self, user_input: str, chat_history: list | None = None) -> dict:
        """执行多 Agent 协作旅行规划

        流程:
        1. 检索知识库（相似对话 + 攻略缓存 + 用户偏好）
        2. 相似度 > 0.5 的内容注入上下文
        3. Agent 执行工具调用
        4. 结果自动存入知识库
        """
        # Step 1: 检索知识库
        kb = await self._search_knowledge(user_input)
        kb_context = self._build_knowledge_context(kb)

        # Step 2: 构建消息（注入知识库上下文）
        enhanced_input = user_input
        if kb_context:
            enhanced_input = (
                f"{kb_context}\n\n"
                f"---\n"
                f"**当前用户新需求**: {user_input}\n\n"
                f"## 🔴 重要：即使有缓存数据，也必须完成以下全部步骤\n"
                f"1. 调用 weather_query 获取最新天气（天气会变，缓存不可信）\n"
                f"2. 调用 ticket_query 查最新票务\n"
                f"3. 调用 web_search 或复用缓存攻略\n"
                f"4. 生成完整旅行计划（含每日详细行程表格、预算表）\n"
                f"5. 必须调用 draw_route_map 生成路线图\n"
                f"6. 如缓存来自之前对话，在计划中注明「参考了知识库中的历史记录」\n"
                f"7. 输出必须和没有缓存时一样详细完整，不能因为已有缓存就简略回复\n"
            )

        messages = list(chat_history or []) + [HumanMessage(content=enhanced_input)]
        result = await self.supervisor_agent.ainvoke({"messages": messages})

        # 提取最终计划
        output_msgs = result.get("messages", [])
        plan = ""
        route_image = ""
        search_results = []  # 收集搜索结果

        for msg in reversed(output_msgs):
            if (hasattr(msg, "content") and msg.content
                    and getattr(msg, "type", "") not in ("tool", "human")):
                plan = str(msg.content)
                break

        # 收集工具调用结果（含存储用的搜索文本）
        import logging
        _log = logging.getLogger("travel_agent")
        for msg in output_msgs:
            if hasattr(msg, "content") and getattr(msg, "type", "") == "tool":
                content = str(msg.content)
                # 提取路线图
                m = re.search(r"route_[^\s\"'}\\\\]+\.html", content)
                if m:
                    route_image = f"/static/{m.group(0)}"
                # 收集工具返回内容 → 清洗后存储
                if len(content) > 50:
                    # 提取 ToolResult 中的 data 字段（纯文本内容）
                    clean = content
                    try:
                        import json as _json
                        obj = _json.loads(content)
                        if isinstance(obj, dict) and "data" in obj:
                            data = obj["data"]
                            if isinstance(data, dict):
                                clean = data.get("results", data.get("daily", str(data)))
                            if isinstance(clean, list):
                                clean = " ".join(
                                    str(r.get("content", r)) if isinstance(r, dict) else str(r)
                                    for r in clean[:5]
                                )
                            clean = str(clean)
                    except Exception:
                        pass
                    search_results.append(clean[:2000])
                    _log.info(f"捕获工具结果: {getattr(msg, 'name', '?')} ({len(content)}字)")

        # 从工具调用结果中提取 map_json（Agent 调用 draw_route_map 时返回）
        map_json = None
        for msg in output_msgs:
            if hasattr(msg, "content") and getattr(msg, "type", "") == "tool":
                content = str(msg.content)
                if "map_json" in content and getattr(msg, "name", "") == "draw_route_map":
                    try:
                        import json as _json
                        obj = _json.loads(content)
                        if isinstance(obj, dict) and "data" in obj:
                            map_json = obj["data"].get("map_json")
                        elif isinstance(obj, dict) and "spots" in obj:
                            map_json = obj
                    except Exception:
                        pass
                    if map_json:
                        break

        # 兜底：正则解析
        if not map_json and plan:
            map_json = self._build_map_json(plan)

        # ---- 存入向量知识库 ----
        await self._store_to_knowledge(user_input, plan, search_results)

        return {"plan": plan, "route_image": route_image, "map_json": map_json}

    def _parse_spots_from_table(self, plan: str) -> tuple[list[dict], str]:
        """用正则从 Markdown 行程表格中可靠提取景点（无需 LLM）"""
        spots = []
        current_day = 1

        # 匹配城市名 — 多策略
        city = ""
        city_patterns = [
            r'#[^#\n]*?([一-鿿]{2,4})\s*(?:旅游|旅行|游|行|攻略|计划|之旅|自由行)',  # 标题中的城市
            r"(?:目的地|城市)[：:]\s*([一-鿿]{2,4})",
            r"(?:去|前往|到)\s*([一-鿿]{2,4})\s*(?:旅游|旅行|玩)",
            r"\*\*目的地\*\*[：:]\s*([一-鿿]{2,4})",
            r'([一-鿿]{2,3})\s*→\s*[一-鿿]{2,3}',  # 北京→杭州 取后者
            r'→\s*([一-鿿]{2,3})',  # →杭州
        ]
        for pat in city_patterns:
            m = re.search(pat, plan[:500])
            if m:
                city = m.group(1) if m.lastindex else ''
                city = re.sub(r'[\s#旅游旅行攻略计划之旅自由行]', '', city)
                if len(city) >= 2:
                    break

        if not city:
            # 从标题匹配：跳过 emoji
            clean_title = re.sub(r'[^一-鿿\w\s]', '', plan[:200])
            m = re.search(r'([一-鿿]{2,3})\s*(?:旅游|旅行|\d+日|游|行)', clean_title)
            if m:
                city = m.group(1)

        # 匹配每天标题: "Day 1" / "第1天" / "### Day1"
        day_sections = re.split(r'(?:###?\s*)?(?:Day\s*|第)\s*(\d+)\s*(?:天|日)', plan)
        if len(day_sections) > 1:
            # 跳过第一个（标题之前的文本），然后成对处理
            pass

        # 解析表格行: | time | activity | spot_name | transport | cost |
        # 匹配格式: | 08:00-11:30 | 活动描述 | **地点名** 或 地点名 | 交通 | 费用 |
        table_row = re.compile(
            r'\|\s*'
            r'(\d{1,2}:\d{2}\s*[-–—~～]\s*\d{1,2}:\d{2})'  # 时间
            r'\s*\|(.*?)\|'                                     # 活动+地点（合并）
            r'\s*(.*?)\s*\|'                                    # 交通
            r'\s*(.*?)'                                         # 费用
            r'\s*\|',
            re.DOTALL,
        )

        # 更简单的匹配：逐行扫描表格
        lines = plan.split('\n')
        in_table = False

        for line in lines:
            # 检测 Day 标题
            day_match = re.match(r'.*(?:Day\s*|第)\s*(\d+)\s*(?:天|日)?', line, re.IGNORECASE)
            if day_match:
                current_day = int(day_match.group(1))
                continue

            # 检测表格行
            if '|' in line and re.search(r'\d{1,2}:\d{2}', line):
                cells = [c.strip() for c in line.split('|') if c.strip()]
                if len(cells) >= 3:
                    # 去掉粗体标记 ** __ 再检测时间
                    time_cell = re.sub(r'\*{1,2}|_{1,2}', '', cells[0]).strip()
                    if not re.match(r'\d{1,2}:\d{2}', time_cell):
                        continue

                    # 从所有列中提取景点名（**粗体**优先）
                    all_text = ' '.join(cells[1:])  # 活动+地点+费用 全部搜索
                    spot_name = ""

                    # 1. 优先从粗体 **xxx** 提取
                    bold_match = re.search(r'\*\*(.+?)\*\*', all_text)
                    if bold_match:
                        spot_name = bold_match.group(1).strip()

                    # 2. 从每列中查找纯中文地名
                    if not spot_name:
                        for cell in cells[1:]:
                            clean = re.sub(r'\*{1,2}|_{1,2}|\d+元?|免费|¥\s*\d+', '', cell).strip()
                            name_match = re.match(r'([一-鿿]{2,6}(?:[园寺塔湖山河街岛村馆宫]|景区|公园|湿地|广场|寺庙)?)', clean)
                            if name_match and len(name_match.group(1)) >= 2:
                                spot_name = name_match.group(1)
                                break

                    # 3. 从活动描述中取前几个字
                    if not spot_name and len(cells) > 1:
                        clean = re.sub(r'\*{1,2}|\d+', '', cells[1]).strip()
                        if len(clean) >= 2:
                            spot_name = clean[:8]

                    if not spot_name or len(spot_name) < 2:
                        continue

                    # 活动描述 = 非地点列的内容
                    activity_text = cells[1] if len(cells) > 1 else ''
                    if '**' in activity_text:
                        activity_text = re.sub(r'\*\*.+?\*\*', '', activity_text).strip()
                    transport = cells[-2] if len(cells) >= 4 else ''
                    cost = cells[-1] if len(cells) >= 3 else ''

                    # 去重
                    if not any(s['name'] == spot_name for s in spots):
                        spots.append({
                            "name": spot_name,
                            "day": current_day,
                            "time": time_cell,
                            "activity": re.sub(r'\*{1,2}', '', activity_text).strip()[:60],
                            "transport": re.sub(r'\*{1,2}', '', transport).strip(),
                            "cost": re.sub(r'\*{1,2}', '', cost).strip(),
                        })

        return spots, city

    def _build_map_json(self, plan: str) -> dict | None:
        """同步版本 — 从计划的 Markdown 表格中提取景点 → DrawingTool.to_map_json()"""
        import logging
        _log = logging.getLogger("travel_agent")

        if not plan:
            _log.warning("_build_map_json: plan 为空")
            return None

        spots, city = self._parse_spots_from_table(plan)
        _log.info(f"_build_map_json: 表格解析得到 {len(spots)} 个景点, 城市={city}")

        if not spots:
            _log.warning("_build_map_json: 未从表格中提取到景点，尝试备用匹配")
            # 备用：直接搜索景点关键词
            for name in ["西湖", "灵隐寺", "雷峰塔", "断桥", "苏堤", "西溪", "宋城",
                        "外滩", "东方明珠", "故宫", "颐和园", "长城",
                        "宽窄巷子", "洪崖洞", "兵马俑", "亚龙湾"]:
                if name in plan:
                    spots.append({"name": name, "day": 1, "time": "", "activity": "", "transport": "", "cost": ""})
            _log.info(f"_build_map_json: 备用匹配得到 {len(spots)} 个景点")

        if not spots:
            return None

        draw_tool = self._tool_map.get("draw_route_map")
        if draw_tool:
            result = draw_tool.to_map_json(spots, city or "")
            _log.info(f"_build_map_json: to_map_json 返回 {len(result.get('spots',[]))} spots, {len(result.get('routes',[]))} routes")
            return result

        return None

    async def _llm_chat(self, prompt: str, temperature: float = 0.5) -> str:
        """简短 LLM 调用（提取信息用）"""
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model=config.LLM_MODEL,
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_BASE_URL,
            temperature=temperature,
            max_tokens=2048,
        )
        from langchain_core.messages import HumanMessage
        resp = await llm.ainvoke([HumanMessage(content=prompt)])
        return resp.content or ""

    async def _store_to_knowledge(self, user_input: str, plan: str, search_results: list):
        """将对话和搜索结果存入 ChromaDB"""
        from datetime import datetime, timezone

        # 存入对话历史
        if self.memory_manager and plan:
            try:
                summary = plan[:800] if len(plan) > 800 else plan
                await self.memory_manager.save_to_long_term(
                    session_id=f"cli_{datetime.now(timezone.utc).timestamp():.0f}",
                    summary=f"用户: {user_input[:200]}\n助手: {summary}",
                    metadata={"source": "conversation", "type": "travel_plan"},
                )
            except Exception:
                pass

        # 存入搜索结果
        if self.doc_pipeline and self.vector_store and search_results:
            for i, text in enumerate(search_results):
                try:
                    self.vector_store.add(
                        doc_id=f"search_{datetime.now(timezone.utc).timestamp():.0f}_{i}",
                        text=text,
                        metadata={
                            "source": "web_search",
                            "ingested_at": datetime.now(timezone.utc).isoformat(),
                            "access_count": 0,
                            "importance_score": 0.6,
                        },
                        collection="travel_docs",
                    )
                except Exception:
                    pass

    def run_sync(self, user_input: str) -> dict:
        import asyncio
        return asyncio.run(self.run(user_input))
