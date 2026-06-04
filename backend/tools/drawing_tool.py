"""绘图工具 — 基于 Folium 生成交互式旅行路线图"""

from pathlib import Path
from .base import BaseTool, ToolResult


# 中国主要旅游城市知名景点真实坐标库
FAMOUS_SPOTS: dict[str, list[dict]] = {
    "杭州": [
        {"name": "西湖", "lng": 120.141, "lat": 30.238, "type": "自然风光"},
        {"name": "断桥残雪", "lng": 120.155, "lat": 30.259, "type": "景点"},
        {"name": "雷峰塔", "lng": 120.148, "lat": 30.231, "type": "景点"},
        {"name": "灵隐寺", "lng": 120.103, "lat": 30.248, "type": "寺庙"},
        {"name": "飞来峰", "lng": 120.102, "lat": 30.247, "type": "景点"},
        {"name": "西溪湿地", "lng": 120.067, "lat": 30.269, "type": "自然风光"},
        {"name": "宋城", "lng": 120.098, "lat": 30.172, "type": "主题公园"},
        {"name": "河坊街", "lng": 120.170, "lat": 30.243, "type": "美食街"},
        {"name": "南宋御街", "lng": 120.172, "lat": 30.245, "type": "历史街区"},
        {"name": "龙井村", "lng": 120.118, "lat": 30.219, "type": "茶园"},
        {"name": "六和塔", "lng": 120.143, "lat": 30.198, "type": "古迹"},
        {"name": "岳王庙", "lng": 120.139, "lat": 30.254, "type": "古迹"},
        {"name": "浙江省博物馆", "lng": 120.165, "lat": 30.253, "type": "博物馆"},
        {"name": "中国丝绸博物馆", "lng": 120.159, "lat": 30.225, "type": "博物馆"},
        {"name": "钱塘江大桥", "lng": 120.131, "lat": 30.187, "type": "景点"},
        {"name": "湖滨银泰", "lng": 120.168, "lat": 30.254, "type": "购物"},
        {"name": "杭州酒家", "lng": 120.169, "lat": 30.251, "type": "餐饮"},
        {"name": "外婆家(湖滨店)", "lng": 120.168, "lat": 30.250, "type": "餐饮"},
    ],
    "北京": [
        {"name": "故宫", "lng": 116.397, "lat": 39.916, "type": "古迹"},
        {"name": "天安门广场", "lng": 116.398, "lat": 39.906, "type": "景点"},
        {"name": "颐和园", "lng": 116.278, "lat": 39.997, "type": "园林"},
        {"name": "八达岭长城", "lng": 116.021, "lat": 40.355, "type": "古迹"},
        {"name": "天坛", "lng": 116.413, "lat": 39.882, "type": "古迹"},
        {"name": "鸟巢", "lng": 116.394, "lat": 39.993, "type": "现代建筑"},
        {"name": "南锣鼓巷", "lng": 116.407, "lat": 39.940, "type": "历史街区"},
        {"name": "798艺术区", "lng": 116.502, "lat": 39.981, "type": "艺术区"},
        {"name": "簋街", "lng": 116.432, "lat": 39.938, "type": "美食街"},
    ],
    "上海": [
        {"name": "外滩", "lng": 121.490, "lat": 31.240, "type": "景点"},
        {"name": "东方明珠", "lng": 121.499, "lat": 31.240, "type": "现代建筑"},
        {"name": "豫园", "lng": 121.493, "lat": 31.229, "type": "园林"},
        {"name": "南京路步行街", "lng": 121.479, "lat": 31.236, "type": "购物"},
        {"name": "迪士尼乐园", "lng": 121.662, "lat": 31.144, "type": "主题公园"},
        {"name": "田子坊", "lng": 121.470, "lat": 31.210, "type": "文艺街区"},
        {"name": "新天地", "lng": 121.478, "lat": 31.219, "type": "商业区"},
    ],
    "成都": [
        {"name": "宽窄巷子", "lng": 104.059, "lat": 30.667, "type": "历史街区"},
        {"name": "锦里", "lng": 104.053, "lat": 30.647, "type": "美食街"},
        {"name": "武侯祠", "lng": 104.052, "lat": 30.647, "type": "古迹"},
        {"name": "大熊猫繁育基地", "lng": 104.146, "lat": 30.733, "type": "动物园"},
        {"name": "杜甫草堂", "lng": 104.031, "lat": 30.661, "type": "古迹"},
        {"name": "春熙路", "lng": 104.083, "lat": 30.654, "type": "购物"},
        {"name": "青城山", "lng": 103.590, "lat": 30.900, "type": "自然风光"},
        {"name": "都江堰", "lng": 103.617, "lat": 30.982, "type": "古迹"},
    ],
    "西安": [
        {"name": "兵马俑", "lng": 109.284, "lat": 34.384, "type": "古迹"},
        {"name": "大雁塔", "lng": 108.964, "lat": 34.218, "type": "古迹"},
        {"name": "回民街", "lng": 108.947, "lat": 34.262, "type": "美食街"},
        {"name": "西安城墙", "lng": 108.947, "lat": 34.260, "type": "古迹"},
        {"name": "钟楼", "lng": 108.946, "lat": 34.261, "type": "古建筑"},
        {"name": "大唐不夜城", "lng": 108.965, "lat": 34.212, "type": "商业区"},
    ],
    "三亚": [
        {"name": "亚龙湾", "lng": 109.639, "lat": 18.223, "type": "海滩"},
        {"name": "天涯海角", "lng": 109.348, "lat": 18.288, "type": "景点"},
        {"name": "南山寺", "lng": 109.206, "lat": 18.304, "type": "寺庙"},
        {"name": "蜈支洲岛", "lng": 109.758, "lat": 18.307, "type": "海岛"},
        {"name": "大东海", "lng": 109.522, "lat": 18.224, "type": "海滩"},
    ],
    "重庆": [
        {"name": "洪崖洞", "lng": 106.586, "lat": 29.564, "type": "景点"},
        {"name": "解放碑", "lng": 106.578, "lat": 29.558, "type": "商业区"},
        {"name": "磁器口", "lng": 106.449, "lat": 29.579, "type": "古镇"},
        {"name": "长江索道", "lng": 106.588, "lat": 29.558, "type": "交通/景点"},
    ],
}


class DrawingTool(BaseTool):
    """生成旅行路线图 — 基于 Folium + OpenStreetMap 底图"""

    name = "draw_route_map"
    description = "根据景点名称和城市生成交互式旅行路线图（HTML），带真实地图底图"

    parameters = {
        "spots": {
            "type": "array",
            "description": "景点列表，每项必须包含: name(景点名), day(第几天,数字), time(时间范围如'08:00-11:30'), activity(活动描述如'环湖游览'), transport(交通方式如'步行'), cost(费用如'免费'或'¥40')",
        },
        "city": {
            "type": "string",
            "description": "目的地城市名称，如'杭州'",
        },
        "title": {
            "type": "string",
            "description": "地图标题",
        },
    }

    def __init__(self, output_dir: Path | None = None):
        self.output_dir = output_dir or Path("./data/images")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def execute(
        self,
        spots: list[dict],
        city: str = "",
        output_dir: str = "",
        title: str = "旅行路线图",
        **kwargs,
    ) -> ToolResult:
        """生成路线图"""
        try:
            output_dir = Path(output_dir) if output_dir else self.output_dir
            output_dir.mkdir(parents=True, exist_ok=True)

            # 生成 map_json（前端用）
            map_json = self.to_map_json(spots, city)

            # 用坐标库补全经纬度
            spots_with_coords = self._enrich_coords(spots, city)

            # 生成 Folium HTML（备用）
            html_path = None
            if spots_with_coords:
                html_path = self._make_folium_map(spots_with_coords, title, output_dir)

            return ToolResult(
                success=True,
                data={
                    "interactive_map": str(html_path) if html_path else "",
                    "map_json": map_json,
                    "spot_count": map_json.get("spots", []).__len__(),
                    "days": len(set(s.get("day", 1) for s in spots_with_coords if spots_with_coords)),
                    "title": title,
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    # ---- 颜色 ----
    COLORS = ["#E74C3C", "#3498DB", "#2ECC71", "#9B59B6", "#F39C12", "#1ABC9C", "#E67E22", "#34495E"]

    def to_map_json(self, spots: list[dict], city: str) -> dict:
        """导出前端 Leaflet 渲染所需的 MapData JSON"""
        spots_with_coords = self._enrich_coords(spots, city)
        if not spots_with_coords:
            return {"city": city, "center": [39.9, 116.4], "spots": [], "routes": []}

        map_spots = []
        for i, s in enumerate(spots_with_coords):
            day = s.get("day", 1)
            # 优先用原始 spot 的字段（LLM 提供），坐标用匹配的
            original = next((x for x in spots if x.get("name") == s["name"]), {})
            map_spots.append({
                "name": s["name"],
                "lng": s["lng"],
                "lat": s["lat"],
                "day": day,
                "order": i + 1,
                "time": original.get("time") or s.get("time", ""),
                "activity": original.get("activity") or s.get("activity", ""),
                "transport": original.get("transport") or s.get("transport", ""),
                "cost": original.get("cost") or s.get("cost", ""),
            })

        # 按天路线
        max_day = max(s["day"] for s in spots_with_coords)
        routes = []
        for day in range(1, max_day + 1):
            day_spots = [s for s in spots_with_coords if s["day"] == day]
            if len(day_spots) >= 2:
                routes.append({
                    "day": day,
                    "color": self.COLORS[(day - 1) % len(self.COLORS)],
                    "coords": [[s["lat"], s["lng"]] for s in day_spots],
                })

        lats = [s["lat"] for s in spots_with_coords]
        lngs = [s["lng"] for s in spots_with_coords]

        return {
            "city": city,
            "center": [sum(lats) / len(lats), sum(lngs) / len(lngs)],
            "spots": map_spots,
            "routes": routes,
        }

    def _enrich_coords(self, spots: list[dict], city: str) -> list[dict]:
        """用知名景点坐标库匹配经纬度"""
        # 构建匹配库：优先匹配指定城市，无城市时搜索全部
        city_spots = {}
        for cn, spots_list in FAMOUS_SPOTS.items():
            if not city or city in cn or cn in city:
                for s in spots_list:
                    city_spots[s["name"]] = s
        # 没匹配到则搜全部
        if not city_spots:
            for cn, spots_list in FAMOUS_SPOTS.items():
                for s in spots_list:
                    if s["name"] not in city_spots:
                        city_spots[s["name"]] = s

        result = []
        for spot in spots:
            name = spot.get("name", "").strip()
            coords = city_spots.get(name)

            if coords:
                result.append({
                    "name": name,
                    "lng": coords["lng"],
                    "lat": coords["lat"],
                    "day": spot.get("day", 1),
                })
            else:
                # 模糊匹配：检查景点名是否包含坐标库中的名称
                for known_name, coords in city_spots.items():
                    if known_name in name or name in known_name:
                        result.append({
                            "name": name,
                            "lng": coords["lng"],
                            "lat": coords["lat"],
                            "day": spot.get("day", 1),
                        })
                        break

        return result

    def _make_folium_map(self, spots: list[dict], title: str, output_dir: Path) -> str | None:
        """生成 Folium 交互式 HTML 地图（OpenStreetMap 底图）"""
        try:
            import folium

            # 计算中心点和缩放级别
            lats = [s["lat"] for s in spots]
            lngs = [s["lng"] for s in spots]
            center = [sum(lats) / len(lats), sum(lngs) / len(lngs)]

            # 动态计算 zoom：范围越大，zoom 越小
            lat_range = max(lats) - min(lats)
            lng_range = max(lngs) - min(lngs)
            max_range = max(lat_range, lng_range)
            if max_range > 5:
                zoom = 8
            elif max_range > 2:
                zoom = 10
            elif max_range > 0.5:
                zoom = 11
            elif max_range > 0.2:
                zoom = 12
            elif max_range > 0.1:
                zoom = 13
            else:
                zoom = 14

            # 创建地图 — 使用高德地图瓦片（国内访问快，中文标注）
            m = folium.Map(
                location=center,
                zoom_start=zoom,
                tiles="https://webrd01.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}",
                attr="高德地图",
                control_scale=True,
            )

            # 颜色
            colors = ["#E74C3C", "#3498DB", "#2ECC71", "#9B59B6", "#F39C12", "#1ABC9C", "#E67E22", "#34495E"]

            # 按天分组
            day_groups: dict[int, list] = {}
            for s in spots:
                d = s.get("day", 1)
                day_groups.setdefault(d, []).append(s)

            max_day = max(day_groups.keys()) if day_groups else 1

            # 为每天创建 FeatureGroup（可独立开关）
            for day in range(1, max_day + 1):
                if day not in day_groups:
                    continue

                day_spots = day_groups[day]
                color = colors[(day - 1) % len(colors)]

                fg = folium.FeatureGroup(name=f"第{day}天", show=True)

                # 添加标记（用 CircleMarker 更清晰）
                for spot in day_spots:
                    folium.CircleMarker(
                        location=[spot["lat"], spot["lng"]],
                        radius=8,
                        popup=folium.Popup(
                            f"<b>{spot['name']}</b><br>第{day}天",
                            max_width=200,
                        ),
                        tooltip=f"第{day}天: {spot['name']}",
                        color=color,
                        fill=True,
                        fill_color=color,
                        fill_opacity=0.7,
                        weight=2,
                    ).add_to(fg)

                    # 景点名称标注（使用 DivIcon，不重叠）
                    folium.Marker(
                        location=[spot["lat"], spot["lng"]],
                        icon=folium.DivIcon(
                            html=f"""
                            <div style="
                                font-size: 11px;
                                font-weight: bold;
                                color: {color};
                                background: rgba(255,255,255,0.85);
                                padding: 2px 6px;
                                border-radius: 3px;
                                white-space: nowrap;
                                border: 1px solid {color};
                                margin-left: -20px;
                                margin-top: -28px;
                            ">{spot['name']}</div>
                            """,
                            icon_size=(0, 0),
                        ),
                    ).add_to(fg)

                # 当天路线连线
                if len(day_spots) >= 2:
                    coords = [[s["lat"], s["lng"]] for s in day_spots]
                    folium.PolyLine(
                        coords,
                        color=color,
                        weight=3,
                        opacity=0.6,
                        dash_array="10" if day > 1 else None,
                        popup=f"第{day}天路线",
                    ).add_to(fg)

                fg.add_to(m)

            # 图例
            legend_html = """
            <div style="position: fixed; bottom: 50px; left: 50px; z-index: 1000;
                        background: white; padding: 10px 14px; border-radius: 8px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.2); font-size: 13px;">
            <b>图例</b><br>
            """
            for day in range(1, max_day + 1):
                if day in day_groups:
                    color = colors[(day - 1) % len(colors)]
                    legend_html += f'<span style="color:{color};">●</span> 第{day}天<br>'
            legend_html += "</div>"
            m.get_root().html.add_child(folium.Element(legend_html))

            # 图层控制
            folium.LayerControl().add_to(m)

            # 标题
            title_html = f"""
            <div style="position: fixed; top: 10px; left: 50%; transform: translateX(-50%);
                        z-index: 1000; background: rgba(255,255,255,0.9); padding: 8px 20px;
                        border-radius: 6px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                        font-size: 16px; font-weight: bold;">
            {title}
            </div>
            """
            m.get_root().html.add_child(folium.Element(title_html))

            # 保存
            safe_name = title.replace(" ", "_").replace("/", "_")
            filepath = output_dir / f"route_{safe_name}.html"
            m.save(str(filepath))
            return str(filepath)

        except ImportError:
            return None
