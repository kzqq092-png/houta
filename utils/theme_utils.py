import json
import re

def load_theme_json_with_comments(path):
    """
    加载带注释的JSON主题配置文件，支持//和#注释。
    Args:
        path: 文件路径
    Returns:
        dict: 解析后的JSON对象
    """
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    # 去除 // 和 # 注释
    content = re.sub(r'//.*|#.*', '', content)
    return json.loads(content)
