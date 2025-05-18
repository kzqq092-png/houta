from core.logger import LogManager, LogLevel
from utils.config_manager import ConfigManager

_log_manager = None


def get_logger():
    global _log_manager
    if _log_manager is None:
        config = ConfigManager().logging
        _log_manager = LogManager(config)
    return _log_manager
