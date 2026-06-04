"""向量存储 — ChromaDB 封装"""

import uuid
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings


class VectorStore:
    """ChromaDB 向量存储封装

    管理三个 collection:
    - chat_history: 聊天记录
    - travel_docs: 旅游资料
    - user_prefs: 用户偏好
    """

    COLLECTIONS = ["chat_history", "travel_docs", "user_prefs"]

    def __init__(
        self,
        persist_dir: str | Path = "./data/chroma_db",
        embedding_function=None,
    ):
        self.persist_dir = str(persist_dir)
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.embedding_fn = embedding_function
        self._collections: dict[str, Any] = {}

        # 初始化 collections
        self._init_collections()

    def _init_collections(self):
        """初始化所有 collection"""
        for name in self.COLLECTIONS:
            self._collections[name] = self.client.get_or_create_collection(
                name=name,
                embedding_function=self.embedding_fn,
                metadata={"hnsw:space": "cosine"},
            )

    def get_collection(self, name: str):
        """获取指定 collection"""
        if name not in self._collections:
            raise ValueError(f"未知 collection: {name}，可选: {self.COLLECTIONS}")
        return self._collections[name]

    def add(
        self,
        doc_id: str | None = None,
        text: str = "",
        metadata: dict | None = None,
        collection: str = "travel_docs",
    ) -> str:
        """添加文档到向量库"""
        doc_id = doc_id or f"doc_{uuid.uuid4().hex[:16]}"
        col = self.get_collection(collection)
        col.add(
            ids=[doc_id],
            documents=[text],
            metadatas=[metadata or {}],
        )
        return doc_id

    def query(
        self,
        query_text: str,
        collection: str = "travel_docs",
        n_results: int = 5,
        where: dict | None = None,
    ) -> dict:
        """查询相似文档"""
        col = self.get_collection(collection)
        results = col.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where,
        )
        return results

    def update_metadata(self, doc_id: str, metadata: dict, collection: str = "travel_docs"):
        """更新文档元数据（如访问次数）"""
        col = self.get_collection(collection)
        col.update(ids=[doc_id], metadatas=[metadata])

    def delete(self, doc_ids: list[str], collection: str = "travel_docs"):
        """删除文档"""
        col = self.get_collection(collection)
        col.delete(ids=doc_ids)

    def get_all_with_metadata(self, collection: str = "travel_docs") -> list[dict]:
        """获取所有文档及其元数据"""
        col = self.get_collection(collection)
        results = col.get()
        return [
            {"id": i, "document": d, "metadata": m}
            for i, d, m in zip(
                results.get("ids", []),
                results.get("documents", []),
                results.get("metadatas", []),
            )
        ]

    def count(self, collection: str = "travel_docs") -> int:
        """文档数量"""
        col = self.get_collection(collection)
        return col.count()
