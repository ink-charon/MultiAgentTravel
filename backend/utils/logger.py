"""统一日志配置"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler


def get_logger(name: str, log_dir: Path | None = None, level: str = "INFO") -> logging.Logger:
    """获取配置好的 logger"""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 控制台 handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG)
    console_fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    console.setFormatter(console_fmt)
    logger.addHandler(console)

    # 文件 handler（可选）
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_dir / "app.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_fmt = logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_fmt)
        logger.addHandler(file_handler)

    return logger
