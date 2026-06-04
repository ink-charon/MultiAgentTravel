"""工具注册表 — 统一管理所有工具"""

from .base import BaseTool


class ToolRegistry:
    """工具注册表

    用法:
        registry = ToolRegistry()
        registry.register(WeatherTool())
        tools = registry.get_all()
    """

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """注册一个工具"""
        self._tools[tool.name] = tool

    def get_all(self) -> list[BaseTool]:
        """获取所有工具"""
        return list(self._tools.values())

    def get_by_name(self, name: str) -> BaseTool | None:
        """按名称获取工具"""
        return self._tools.get(name)

    def __len__(self) -> int:
        return len(self._tools)

    def list_names(self) -> list[str]:
        return list(self._tools.keys())
