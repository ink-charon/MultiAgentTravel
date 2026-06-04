"""检索策略 — 相似度检索 + 元数据过滤"""

from datetime import datetime, timezone


class Retriever:
    """知识检索器

    提供多种检索策略:
    - 相似度检索: 基于向量相似度
    - 混合检索: 相似度 + 关键词匹配
    - 按目的地过滤: 只检索相关城市的资料
    """

    def __init__(self, vector_store):
        self.vs = vector_store

    def search(
        self,
        query: str,
        collection: str = "travel_docs",
        top_k: int = 5,
        destination: str | None = None,
        search_type: str | None = None,
    ) -> list[dict]:
        """检索相关文档

        Args:
            query: 查询文本
            collection: 目标 collection
            top_k: 返回数量
            destination: 按目的地过滤（可选）
            search_type: 按搜索类型过滤（可选）
        """
        # 构建过滤条件
        where = {}
        if destination:
            where["destination"] = destination
        if search_type:
            where["search_type"] = search_type

        results = self.vs.query(
            query_text=query,
            collection=collection,
            n_results=top_k,
            where=where if where else None,
        )

        docs = []
        if results and results.get("documents"):
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                distance = results["distances"][0][i] if results.get("distances") else 0

                docs.append({
                    "id": results["ids"][0][i],
                    "content": doc,
                    "metadata": metadata,
                    "score": 1 - distance,  # 转为相似度分数
                })

        # 更新访问记录
        self._update_access(docs, collection)

        return docs

    def search_by_destination(
        self,
        destination: str,
        query: str = "",
        top_k: int = 10,
    ) -> list[dict]:
        """按目的地检索"""
        return self.search(
            query=query or destination,
            collection="travel_docs",
            top_k=top_k,
            destination=destination,
        )

    def search_chat_history(
        self,
        query: str,
        top_k: int = 5,
        session_id: str | None = None,
    ) -> list[dict]:
        """检索聊天历史"""
        return self.search(
            query=query,
            collection="chat_history",
            top_k=top_k,
        )

    def _update_access(self, docs: list[dict], collection: str):
        """更新文档访问记录"""
        now = datetime.now(timezone.utc).isoformat()
        for doc in docs:
            doc_id = doc.get("id")
            if not doc_id:
                continue
            metadata = doc.get("metadata", {}).copy()
            metadata["access_count"] = metadata.get("access_count", 0) + 1
            metadata["last_accessed"] = now
            # 被访问时略微提升重要性
            metadata["importance_score"] = min(
                1.0,
                metadata.get("importance_score", 0.5) + 0.01,
            )
            try:
                self.vs.update_metadata(doc_id, metadata, collection)
            except Exception:
                pass
