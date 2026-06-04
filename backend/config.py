"""
全局配置管理
所有配置从 .env 文件读取，不硬编码敏感信息
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """统一配置类"""

    # ========== 路径 ==========
    BASE_DIR: Path = BASE_DIR
    PROJECT_DIR: Path = PROJECT_DIR
    DATA_DIR: Path = PROJECT_DIR / "data"
    IMAGES_DIR: Path = DATA_DIR / "images"
    LOGS_DIR: Path = DATA_DIR / "logs"
    CHROMA_DIR: Path = DATA_DIR / "chroma_db"
    MODELS_DIR: Path = Path(os.getenv("EMBEDDING_CACHE_DIR", str(DATA_DIR / "models")))
    PROMPTS_DIR: Path = BASE_DIR / "prompts" / "system_prompts"

    # ========== LLM ==========
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "deepseek-chat")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))

    # ========== Embedding ==========
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-zh-v1.5")
    EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "1024"))

    # ========== 外部 API ==========
    AMAP_API_KEY: str = os.getenv("AMAP_API_KEY", "")
    WEATHER_API_KEY: str = os.getenv("WEATHER_API_KEY", "")
    WEATHER_API_HOST: str = os.getenv("WEATHER_API_HOST", "devapi.qweather.com")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

    # ========== 服务 ==========
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # ========== 知识库 ==========
    MAX_CHAT_HISTORY: int = 1000
    MAX_DOCS_PER_DESTINATION: int = 100
    FORGETTING_DECAY_DAYS: int = 7
    FORGETTING_THRESHOLD: float = 0.3
    FORGETTING_RETENTION_DAYS: int = 30
    CLEANUP_INTERVAL_HOURS: int = 24

    # ========== 文档处理 ==========
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 80
    RETRIEVAL_TOP_K: int = 5

    # ========== 模拟数据 ==========
    USE_MOCK_TICKET: bool = True  # 票务使用模拟数据

    @classmethod
    def ensure_dirs(cls) -> None:
        """确保所有数据目录存在"""
        for d in [cls.DATA_DIR, cls.IMAGES_DIR, cls.LOGS_DIR, cls.CHROMA_DIR, cls.MODELS_DIR]:
            d.mkdir(parents=True, exist_ok=True)

    @classmethod
    def validate(cls) -> list[str]:
        """验证关键配置，返回缺失项列表"""
        missing = []
        if not cls.LLM_API_KEY:
            missing.append("LLM_API_KEY")
        return missing


# 模块级单例
config = Config()
