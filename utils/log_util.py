from core.logger import LogManager, LogLevel
from utils.config_manager import ConfigManager

_log_manager = None


def get_logger():
    global _log_manager
    if _log_manager is None:
        config = ConfigManager().logging
        _log_manager = LogManager(config)
    return _log_manager


def log_structured(log_manager, event, level="info", **kwargs):
    """结构化日志输出，event为事件名，kwargs为附加字段"""
    import json
    msg = json.dumps({"event": event, **kwargs}, ensure_ascii=False)
    getattr(log_manager, level)(msg)
