"""遗忘机制 — 三级衰减策略，防止向量库无限膨胀"""

from datetime import datetime, timezone


class ForgettingManager:
    """遗忘管理器

    三级衰减策略:
    Level 1: 访问频率衰减 — 长期未访问 → 降低重要性评分
    Level 2: 压缩存储    — 评分低于阈值 → LLM 压缩为摘要
    Level 3: 彻底删除    — 压缩后仍长期未访问 → 物理删除
    """

    def __init__(
        self,
        vector_store,
        llm_client=None,
        decay_days: int = 7,
        importance_threshold: float = 0.3,
        retention_days: int = 30,
        max_docs_per_destination: int = 100,
    ):
        self.vs = vector_store
        self.llm = llm_client
        self.decay_days = decay_days
        self.threshold = importance_threshold
        self.retention_days = retention_days
        self.max_docs_per_destination = max_docs_per_destination

    async def check_and_clean(self) -> dict:
        """执行清理检查

        Returns:
            清理统计信息
        """
        stats = {
            "decayed": 0,       # 衰减的文档数
            "compressed": 0,    # 压缩的文档数
            "deleted": 0,       # 删除的文档数
            "by_destination": {},  # 按目的地清理数量
        }

        now = datetime.now(timezone.utc)

        # 遍历 travel_docs
        all_docs = self.vs.get_all_with_metadata("travel_docs")

        # 按目的地分组检查数量限制
        dest_count: dict[str, list[dict]] = {}
        for doc in all_docs:
            dest = doc.get("metadata", {}).get("destination", "unknown")
            dest_count.setdefault(dest, []).append(doc)

        for dest, docs in dest_count.items():
            # 超过上限的按重要性排序删除
            if len(docs) > self.max_docs_per_destination:
                sorted_docs = sorted(
                    docs,
                    key=lambda d: d["metadata"].get("importance_score", 0),
                )
                to_delete = sorted_docs[:len(docs) - self.max_docs_per_destination]
                ids = [d["id"] for d in to_delete]
                self.vs.delete(ids, "travel_docs")
                stats["deleted"] += len(ids)
                stats["by_destination"][dest] = stats["by_destination"].get(dest, 0) + len(ids)

        # Level 1: 重要性衰减
        for doc in all_docs:
            meta = doc.get("metadata", {})
            last_accessed = meta.get("last_accessed")
            if last_accessed:
                try:
                    last_dt = datetime.fromisoformat(last_accessed)
                    days_since = (now - last_dt).days
                    if days_since > self.decay_days:
                        # 衰减公式: new_score = old_score * 0.9^(days_since - decay_days)
                        old_score = meta.get("importance_score", 0.5)
                        new_score = old_score * (0.9 ** (days_since - self.decay_days))
                        new_score = round(new_score, 4)

                        # 更新元数据
                        meta["importance_score"] = new_score
                        meta["last_decayed"] = now.isoformat()
                        self.vs.update_metadata(doc["id"], meta, "travel_docs")
                        stats["decayed"] += 1

                        # Level 2: 低于阈值触发压缩
                        if new_score < self.threshold:
                            await self._compress_document(doc)
                            stats["compressed"] += 1
                except (ValueError, KeyError):
                    pass

        # Level 3: 检查压缩文档是否过期
        for doc in all_docs:
            meta = doc.get("metadata", {})
            if meta.get("compressed"):
                ingested_str = meta.get("compressed_at") or meta.get("ingested_at", "")
                try:
                    ingested_dt = datetime.fromisoformat(ingested_str)
                    if (now - ingested_dt).days > self.retention_days:
                        self.vs.delete([doc["id"]], "travel_docs")
                        stats["deleted"] += 1
                except (ValueError, KeyError):
                    pass

        return stats

    async def _compress_document(self, doc: dict) -> None:
        """将文档压缩为摘要（Level 2）"""
        content = doc.get("document", "")
        if len(content) < 100:
            # 短文本直接标记，不压缩
            meta = doc.get("metadata", {})
            meta["compressed"] = True
            meta["compressed_at"] = datetime.now(timezone.utc).isoformat()
            self.vs.update_metadata(doc["id"], meta, "travel_docs")
            return

        summary = content

        # 有 LLM 时用 LLM 压缩
        if self.llm:
            prompt = f"请将以下旅游相关信息压缩为1-2句关键摘要：\n\n{content}\n\n摘要："
            try:
                summary = await self.llm.chat(prompt, temperature=0.2, max_tokens=100)
                summary = summary.strip()
            except Exception:
                summary = content[:150] + "..."

        # 更新文档为压缩版
        col = self.vs.get_collection("travel_docs")
        col.update(
            ids=[doc["id"]],
            documents=[summary],
            metadatas=[{
                **doc.get("metadata", {}),
                "compressed": True,
                "compressed_at": datetime.now(timezone.utc).isoformat(),
                "original_length": len(content),
            }],
        )

    def get_stats(self) -> dict:
        """获取存储统计"""
        return {
            "travel_docs_count": self.vs.count("travel_docs"),
            "chat_history_count": self.vs.count("chat_history"),
            "user_prefs_count": self.vs.count("user_prefs"),
        }
