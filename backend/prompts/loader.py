"""Prompt 加载器 — 从 YAML 文件加载提示词，支持 Jinja2 模板渲染"""

from pathlib import Path
from typing import Any

import yaml
from jinja2 import Template


class PromptLoader:
    """加载和管理提示词"""

    def __init__(self, prompts_dir: Path):
        self.prompts_dir = Path(prompts_dir)
        self._cache: dict[str, dict] = {}

    def _load_yaml(self, name: str) -> dict:
        """加载单个 YAML 文件"""
        if name in self._cache:
            return self._cache[name]

        file_path = self.prompts_dir / f"{name}.yaml"
        if not file_path.exists():
            raise FileNotFoundError(f"Prompt 文件不存在: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self._cache[name] = data
        return data

    def get_system_prompt(self, name: str) -> str:
        """获取系统提示词"""
        data = self._load_yaml(name)
        return data.get("system", "").strip()

    def render(self, name: str, **kwargs) -> str:
        """加载模板并渲染

        示例:
            loader.render("travel_planner", destination="杭州", budget=5000)
        """
        data = self._load_yaml(name)

        # 优先使用 user_template，否则用 system
        template_str = data.get("user_template") or data.get("system", "")

        template = Template(template_str)
        return template.render(**kwargs)

    def get_few_shots(self, name: str) -> list[dict]:
        """获取 few-shot 示例"""
        data = self._load_yaml(name)
        return data.get("few_shots", [])

    def get_metadata(self, name: str) -> dict[str, Any]:
        """获取 prompt 元数据（版本、更新时间等）"""
        data = self._load_yaml(name)
        return {
            "version": data.get("version", "unknown"),
            "updated": data.get("updated", "unknown"),
            "model": data.get("model", "unknown"),
        }

    def reload(self) -> None:
        """清空缓存，下次访问时重新加载"""
        self._cache.clear()

    def list_prompts(self) -> list[str]:
        """列出所有可用的 prompt 名称"""
        return [
            p.stem
            for p in self.prompts_dir.glob("*.yaml")
            if p.is_file()
        ]
