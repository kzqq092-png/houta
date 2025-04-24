from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(text, size=(32, 32), bg_color=(240, 240, 240), text_color=(0, 0, 0)):
    """创建一个简单的图标"""
    image = Image.new('RGB', size, bg_color)
    draw = ImageDraw.Draw(image)
    
    # 添加边框
    draw.rectangle([(0, 0), (size[0]-1, size[1]-1)], outline=(200, 200, 200))
    
    # 添加文字
    try:
        font = ImageFont.truetype("arial.ttf", 12)
    except:
        font = ImageFont.load_default()
    
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    x = (size[0] - text_width) // 2
    y = (size[1] - text_height) // 2
    
    draw.text((x, y), text, fill=text_color, font=font)
    return image

def main():
    # 确保icons目录存在
    if not os.path.exists('icons'):
        os.makedirs('icons')
    
    # 创建图标
    icons = {
        'new': '新建',
        'open': '打开',
        'save': '保存',
        'undo': '撤销',
        'redo': '重做',
        'analyze': '分析',
        'backtest': '回测',
        'optimize': '优化',
        'zoom_in': '放大',
        'zoom_out': '缩小',
        'reset_zoom': '重置',
        'settings': '设置',
        'calculator': '计算',
        'converter': '转换'
    }
    
    for name, text in icons.items():
        icon = create_icon(text)
        icon.save(f'icons/{name}.png')
        print(f'已创建图标: {name}.png')

if __name__ == '__main__':
    main() 