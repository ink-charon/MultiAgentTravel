"""文档处理流水线 — 一站式处理：加载 → 分割 → 向量化 → 存储"""

import uuid
from datetime import datetime, timezone

from .loader import DocumentLoader
from .splitter import TextSplitter
from .embedder import Embedder


class DocumentPipeline:
    """文档处理流水线

    将搜索到的文本处理后存入知识库，减少网络查询开销。
    """

    def __init__(
        self,
        splitter: TextSplitter | None = None,
        embedder: Embedder | None = None,
        vector_store=None,  # ChromaDB 实例，后注入
    ):
        self.splitter = splitter or TextSplitter()
        self.embedder = embedder
        self.vector_store = vector_store

    def set_vector_store(self, vector_store):
        """注入向量存储（避免循环依赖）"""
        self.vector_store = vector_store

    async def process_search_result(self, search_data: dict) -> list[str]:
        """处理搜索结果：分割 → 向量化 → 存储

        Returns:
            存储的文档 ID 列表
        """
        # 1. 加载
        docs = DocumentLoader.from_search_result(search_data)
        if not docs:
            return []

        # 2. 分割
        chunks = self.splitter.split_batch(docs)
        if not chunks:
            return []

        # 3. 向量化
        if self.embedder:
            vectors, metadatas = self.embedder.embed_docs(chunks)
        else:
            # 无 embedder 时交由向量存储自行处理
            vectors = None
            metadatas = [c.metadata for c in chunks]

        # 4. 存储
        ids = []
        if self.vector_store:
            for i, chunk in enumerate(chunks):
                doc_id = f"search_{uuid.uuid4().hex[:12]}"
                self.vector_store.add(
                    doc_id=doc_id,
                    text=chunk.content,
                    metadata={
                        **chunk.metadata,
                        "ingested_at": datetime.now(timezone.utc).isoformat(),
                        "access_count": 0,
                        "importance_score": 0.5,
                    },
                )
                ids.append(doc_id)

        return ids

    async def process_chat_message(
        self,
        content: str,
        role: str,
        session_id: str,
        metadata: dict | None = None,
    ) -> str | None:
        """处理聊天消息：摘要后存入知识库

        Returns:
            存储的文档 ID
        """
        if not self.vector_store:
            return None

        doc_id = f"chat_{session_id}_{uuid.uuid4().hex[:8]}"
        self.vector_store.add(
            doc_id=doc_id,
            text=content,
            metadata={
                "role": role,
                "session_id": session_id,
                "source": "chat",
                "ingested_at": datetime.now(timezone.utc).isoformat(),
                "access_count": 0,
                "importance_score": 0.5,
                **(metadata or {}),
            },
        )
        return doc_id
