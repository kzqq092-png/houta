def log_structured(log_manager, event, level="info", **kwargs):
    """结构化日志输出，event为事件名，kwargs为附加字段"""
    import json
    msg = json.dumps({"event": event, **kwargs}, ensure_ascii=False)
    getattr(log_manager, level)(msg)
