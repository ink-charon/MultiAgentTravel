"""对话记忆管理 — 短期记忆 + 长期记忆"""

from datetime import datetime, timezone


class MemoryManager:
    """管理用户与 Agent 的对话记忆

    短期记忆: 当前会话的对话历史（LangGraph checkpoint 管理，此处不负责）
    长期记忆: 跨会话的关键信息摘要（存入 ChromaDB）
    """

    def __init__(self, vector_store, llm_client=None):
        self.vs = vector_store
        self.llm = llm_client

    async def save_to_long_term(
        self,
        session_id: str,
        summary: str,
        metadata: dict | None = None,
    ) -> str:
        """保存对话摘要到长期记忆"""
        doc_id = f"mem_{session_id}"
        self.vs.add(
            doc_id=doc_id,
            text=summary,
            metadata={
                "source": "conversation_summary",
                "session_id": session_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "access_count": 0,
                "importance_score": 0.7,
                **(metadata or {}),
            },
            collection="chat_history",
        )
        return doc_id

    async def recall(self, query: str, n_results: int = 5) -> list[dict]:
        """检索相关长期记忆"""
        results = self.vs.query(
            query_text=query,
            collection="chat_history",
            n_results=n_results,
        )

        memories = []
        if results and results.get("documents"):
            for i, doc in enumerate(results["documents"][0]):
                memories.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                    "distance": results["distances"][0][i] if results.get("distances") else 0,
                })

        # 更新访问计数
        for mem in memories:
            doc_id = mem["metadata"].get("id")
            if doc_id:
                meta = mem["metadata"].copy()
                meta["access_count"] = meta.get("access_count", 0) + 1
                meta["last_accessed"] = datetime.now(timezone.utc).isoformat()
                try:
                    self.vs.update_metadata(doc_id, meta, collection="chat_history")
                except Exception:
                    pass

        return memories
