from PIL import Image, ImageDraw, ImageFont
import os

def create_rich_menu_image():
    """創建Rich Menu的臨時圖片"""
    # 創建一個2500x843的白色圖片
    img = Image.new('RGB', (2500, 843), color=(255, 255, 255))
    
    # 獲取繪圖工具
    draw = ImageDraw.Draw(img)
    
    # 定義區域邊界
    area1 = (0, 0, 833, 843)
    area2 = (833, 0, 1667, 843)
    area3 = (1667, 0, 2500, 843)
    
    # 嘗試載入字體，如果找不到則使用默認字體
    try:
        # 嘗試一些常見的字體
        font_paths = [
            'C:/Windows/Fonts/msjh.ttc',  # 微軟正黑體 (Windows)
            '/System/Library/Fonts/PingFang.ttc',  # PingFang (macOS)
            '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',  # Linux
            './simsun.ttc',  # 如果有在當前目錄放置字體
            None  # 默認字體
        ]
        
        font = None
        for path in font_paths:
            try:
                if path:
                    font = ImageFont.truetype(path, 60)
                    break
            except Exception:
                continue
                
        if not font:
            font = ImageFont.load_default()
    except Exception as e:
        print(f"載入字體時出錯: {e}")
        font = ImageFont.load_default()
    
    # 繪製區域分隔線
    draw.line([(833, 0), (833, 843)], fill=(200, 200, 200), width=5)
    draw.line([(1667, 0), (1667, 843)], fill=(200, 200, 200), width=5)
    
    # 區域背景色
    draw.rectangle(area1, fill=(240, 240, 255), outline=(200, 200, 200), width=3)
    draw.rectangle(area2, fill=(240, 255, 240), outline=(200, 200, 200), width=3)
    draw.rectangle(area3, fill=(255, 240, 240), outline=(200, 200, 200), width=3)
    
    # 添加標題文字
    draw.text((area1[0] + 170, area1[1] + 400), "設定活動", font=font, fill=(0, 0, 0))
    draw.text((area2[0] + 170, area2[1] + 400), "查詢活動", font=font, fill=(0, 0, 0))
    draw.text((area3[0] + 170, area3[1] + 400), "手動提醒", font=font, fill=(0, 0, 0))
    
    # 保存圖片
    img.save('rich_menu_image.jpg')
    print("Rich Menu 圖片已創建：rich_menu_image.jpg")
    
if __name__ == "__main__":
    create_rich_menu_image() 