"""向量化模块 — 魔搭社区下载 → 本地加载 → ChromaDB 兼容"""

import os
import logging
from pathlib import Path

logger = logging.getLogger("embedder")


class Embedder:
    """中文文本向量化

    1. 从魔搭社区下载模型到 data/models/
    2. 用 sentence-transformers 本地加载
    3. 实现 __call__ 接口，可直接传给 ChromaDB
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-large-zh-v1.5",
        cache_dir: str | Path = "./data/models",
        device: str = "cpu",
    ):
        self.model_name = model_name
        self.cache_dir = Path(cache_dir).resolve()
        self.device = device
        self._model = None

    def name(self) -> str:
        """ChromaDB 要求的接口"""
        return "bge-large-zh-v1.5"

    def __call__(self, input: list[str]) -> list[list[float]]:
        """ChromaDB 接口（参数名必须为 input）"""
        return self.embed_documents(input)

    @property
    def model(self):
        if self._model is None:
            self._load_model()
        return self._model

    def _download_from_modelscope(self) -> str:
        """从魔搭社区下载模型，返回本地路径"""
        from modelscope.hub.snapshot_download import snapshot_download

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        # 设置镜像（modelscope 国内可直连）
        os.environ.setdefault("MODELSCOPE_CACHE", str(self.cache_dir))

        logger.info(f"从魔搭社区下载模型: {self.model_name} → {self.cache_dir}")
        local_path = snapshot_download(
            self.model_name,
            cache_dir=str(self.cache_dir),
            revision="master",
        )
        logger.info(f"模型已下载到: {local_path}")
        return local_path

    def _load_model(self):
        """下载并加载模型"""
        # Step 1: 从魔搭社区下载到 data/models/
        try:
            local_path = self._download_from_modelscope()
        except Exception as e:
            logger.warning(f"魔搭社区下载失败: {e}，尝试 HF 镜像")
            # 回退：HF 镜像
            os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
            local_path = self.model_name  # 让 sentence-transformers 自己下载

        # Step 2: 用 sentence-transformers 加载本地模型
        from sentence_transformers import SentenceTransformer

        logger.info(f"加载模型: {local_path}")
        self._model = SentenceTransformer(
            local_path,
            device=self.device,
        )
        logger.info(f"模型加载完成，维度: {self._model.get_embedding_dimension()}")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """批量向量化"""
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=32,
        )
        return embeddings.tolist()

    def embed_query(self, input: str = "", query: str = "") -> list[list[float]]:
        """ChromaDB 要求返回 list[list[float]]"""
        text = input or query
        if isinstance(text, list):
            text = text[0] if text else ""
        vec = self.embed_documents([text])[0]
        return [vec]  # ChromaDB 期望 [[...]] 格式
