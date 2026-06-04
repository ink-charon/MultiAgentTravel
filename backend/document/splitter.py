"""文本分割策略 — 智能分割中文文本"""

from langchain_text_splitters import RecursiveCharacterTextSplitter
from .loader import Document


class TextSplitter:
    """中文文本分割器

    结合递归字符分割和语义感知，确保分割后的 chunk 保持上下文连贯。
    """

    # 中文专用分隔符优先级
    CHINESE_SEPARATORS = [
        "\n\n",    # 段落
        "\n",      # 换行
        "。",      # 中文句号
        "！",      # 感叹号
        "？",      # 问号
        "；",      # 分号
        "，",      # 逗号
        ".",       # 英文句号
        "!",       # 英文感叹号
        "?",       # 英文问号
        ";",       # 英文分号
        " ",       # 空格（最后手段）
    ]

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 80):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._splitter = RecursiveCharacterTextSplitter(
            separators=self.CHINESE_SEPARATORS,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )

    def split(self, doc: Document) -> list[Document]:
        """分割文档为多个 chunk"""
        chunks = self._splitter.split_text(doc.content)

        result = []
        for i, chunk in enumerate(chunks):
            result.append(Document(
                content=chunk,
                source=doc.source,
                metadata={
                    **doc.metadata,
                    "chunk_index": i,
                    "chunk_count": len(chunks),
                },
            ))
        return result

    def split_batch(self, docs: list[Document]) -> list[Document]:
        """批量分割"""
        all_chunks = []
        for doc in docs:
            all_chunks.extend(self.split(doc))
        return all_chunks
