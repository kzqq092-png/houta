from PIL import Image, ImageDraw, ImageFont
import os
import sys
from pathlib import Path

def find_system_font():
    """查找系统中可用的中文字体"""
    possible_fonts = [
        # Windows 字体路径
        # r"C:\Windows\Fonts\msyh.ttc",  # 微软雅黑
        # r"C:\Windows\Fonts\simhei.ttf",  # 黑体
        r"C:\Windows\Fonts\simsun.ttc",  # 宋体
        # Linux 字体路径
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        # macOS 字体路径
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc"
    ]
    
    # 检查自定义字体目录
    custom_font_dir = Path(__file__).parent / "fonts"
    if custom_font_dir.exists():
        for font_file in custom_font_dir.glob("*.ttf"):
            possible_fonts.insert(0, str(font_file))
            
    for font_path in possible_fonts:
        if os.path.exists(font_path):
            return font_path
            
    return None

def create_icon(text, size=(32, 32), bg_color=(240, 240, 240), text_color=(60, 60, 60)):
    """创建一个简单的图标
    
    Args:
        text: 图标文字
        size: 图标大小，默认32x32
        bg_color: 背景颜色
        text_color: 文字颜色
    
    Returns:
        PIL.Image: 生成的图标
    """
    try:
        # 创建图像
        image = Image.new('RGB', size, bg_color)
        draw = ImageDraw.Draw(image)
        
        # 添加圆角矩形背景
        radius = 4
        draw.rounded_rectangle([(0, 0), (size[0]-1, size[1]-1)], radius, 
                             fill=bg_color, outline=(200, 200, 200))
        
        # 查找并加载字体
        font_path = find_system_font()
        if font_path:
            # 根据图标大小自动计算合适的字体大小
            font_size = min(size) // 2
            try:
                font = ImageFont.truetype(font_path, font_size)
            except Exception as e:
                print(f"加载字体失败: {e}")
                font = ImageFont.load_default()
        else:
            print("未找到合适的中文字体，使用默认字体")
            font = ImageFont.load_default()
        
        # 计算文字位置
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        x = (size[0] - text_width) // 2
        y = (size[1] - text_height) // 2
        
        # 绘制文字阴影
        shadow_offset = 1
        draw.text((x+shadow_offset, y+shadow_offset), text, 
                 fill=(180, 180, 180), font=font)
        
        # 绘制文字
        draw.text((x, y), text, fill=text_color, font=font)
        
        return image
        
    except Exception as e:
        print(f"创建图标失败: {e}")
        # 创建一个带错误标记的图标
        image = Image.new('RGB', size, (255, 200, 200))
        draw = ImageDraw.Draw(image)
        draw.line([(0, 0), (size[0], size[1])], fill=(255, 0, 0), width=2)
        draw.line([(0, size[1]), (size[0], 0)], fill=(255, 0, 0), width=2)
        return image

def main():
    """生成所有需要的图标"""
    try:
        # 确保icons目录存在
        icons_dir = Path(__file__).parent / "icons"
        icons_dir.mkdir(exist_ok=True)
        
        # 定义图标配置
        icons = {
            'new': {'text': '新建', 'color': (240, 255, 240)},
            'open': {'text': '打开', 'color': (240, 240, 255)},
            'save': {'text': '保存', 'color': (255, 240, 240)},
            'undo': {'text': '撤销', 'color': (255, 255, 240)},
            'redo': {'text': '重做', 'color': (240, 255, 255)},
            'analyze': {'text': '分析', 'color': (255, 240, 255)},
            'backtest': {'text': '回测', 'color': (245, 245, 255)},
            'optimize': {'text': '优化', 'color': (255, 245, 245)},
            'zoom_in': {'text': '放大', 'color': (245, 255, 245)},
            'zoom_out': {'text': '缩小', 'color': (255, 245, 255)},
            'reset_zoom': {'text': '重置', 'color': (245, 255, 255)},
            'settings': {'text': '设置', 'color': (255, 255, 245)},
            'calculator': {'text': '计算', 'color': (250, 250, 255)},
            'converter': {'text': '转换', 'color': (255, 250, 250)}
        }
        
        # 生成图标
        for name, config in icons.items():
            try:
                icon = create_icon(config['text'], bg_color=config['color'])
                icon_path = icons_dir / f"{name}.png"
                icon.save(str(icon_path))
                print(f"已生成图标: {icon_path}")
            except Exception as e:
                print(f"生成图标 {name} 失败: {e}")
                
        print("\n所有图标生成完成!")
        
    except Exception as e:
        print(f"生成图标过程中发生错误: {e}")

if __name__ == '__main__':
    main() 