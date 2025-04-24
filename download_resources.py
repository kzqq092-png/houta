import os
import requests
from pathlib import Path

def download_loading_gif():
    """下载加载动画并保存到resources目录"""
    # 创建资源目录
    resources_dir = Path(__file__).parent / "resources" / "images"
    resources_dir.mkdir(parents=True, exist_ok=True)
    
    # 加载动画URL (使用一个简单的加载动画)
    loading_url = "https://media.giphy.com/media/3oEjI6SIIHBdRxXI40/giphy.gif"
    
    try:
        # 下载动画
        response = requests.get(loading_url)
        response.raise_for_status()
        
        # 保存动画
        gif_path = resources_dir / "loading.gif"
        with open(gif_path, 'wb') as f:
            f.write(response.content)
            
        print(f"加载动画已保存到: {gif_path}")
        
    except Exception as e:
        print(f"下载加载动画失败: {str(e)}")
        print("请手动下载一个loading.gif文件并放置到resources/images目录下")

if __name__ == "__main__":
    download_loading_gif() 