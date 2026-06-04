"""文档加载器 — 清洗和提取原始文本"""

import re
from dataclasses import dataclass, field


@dataclass
class Document:
    """标准化文档"""

    content: str
    metadata: dict = field(default_factory=dict)
    source: str = ""


class DocumentLoader:
    """从不同来源加载和清洗文本"""

    @staticmethod
    def from_text(text: str, source: str = "raw_text", **metadata) -> Document:
        """从纯文本加载"""
        cleaned = DocumentLoader._clean(text)
        return Document(content=cleaned, source=source, metadata=metadata)

    @staticmethod
    def from_search_result(search_data: dict) -> list[Document]:
        """从搜索结果加载（多个文档）"""
        docs = []
        results = search_data.get("results", [])
        destination = search_data.get("destination", "")

        for r in results:
            content = r.get("content", "")
            if not content:
                continue
            cleaned = DocumentLoader._clean(content)
            docs.append(Document(
                content=cleaned,
                source="web_search",
                metadata={
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "destination": destination,
                    "search_type": search_data.get("search_type", "general"),
                },
            ))
        return docs

    @staticmethod
    def _clean(text: str) -> str:
        """通用文本清洗"""
        # 合并空白
        text = re.sub(r"\s+", " ", text)
        # 去除特殊字符
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        # 去除首尾空白
        text = text.strip()
        return text
