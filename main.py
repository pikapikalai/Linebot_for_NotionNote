from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import MessagingApi, ApiClient, Configuration
from linebot.v3.webhooks import MessageEvent, TextMessageContent, PostbackEvent
from linebot.v3.messaging import (
    TextMessage, 
    ReplyMessageRequest,
    RichMenuArea,
    RichMenuSize,
    RichMenuBounds,
    URIAction,
    FlexMessage,
    FlexContainer,
    RichMenuResponse,
    RichMenuRequest,
    ConfirmTemplate
)
from linebot.v3.messaging.models import (
    QuickReply,
    QuickReplyItem,
    MessageAction,
    PostbackAction,
    DatetimePickerAction,
    TemplateMessage,
    ButtonsTemplate
)
import os
from dotenv import load_dotenv
import re
import json
from datetime import datetime, timedelta, timezone
from notion_manager import NotionManager
from reminder import EventReminder
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder

# 載入 .env 文件中的環境變數
load_dotenv()

# 檢查環境變數是否正確加載
print("檢查環境變數...")
if not os.getenv('LINE_CHANNEL_ACCESS_TOKEN'):
    print("警告: LINE_CHANNEL_ACCESS_TOKEN 未設置")
else:
    token_prefix = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')[:10] + "..." if len(os.getenv('LINE_CHANNEL_ACCESS_TOKEN')) > 10 else ""
    print(f"LINE_CHANNEL_ACCESS_TOKEN: {token_prefix} (已設置)")

if not os.getenv('LINE_CHANNEL_SECRET'):
    print("警告: LINE_CHANNEL_SECRET 未設置")
else:
    print("LINE_CHANNEL_SECRET: (已設置)")

app = Flask(__name__)

# 設定您的 LINE Bot 憑證
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')

# 初始化 LINE API 客戶端
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
api_client = ApiClient(configuration)
line_bot_api = MessagingApi(api_client)

# 初始化 Notion 管理器和提醒器
notion_manager = NotionManager()
event_reminder = EventReminder()

# 啟動自動提醒
event_reminder.start()

# 檢查 Rich Menu 圖片是否存在，如果不存在則創建
def ensure_rich_menu_image():
    if not os.path.exists('rich_menu_image.jpg'):
        try:
            # 嘗試引入PILlow並創建圖片
            from PIL import Image, ImageDraw, ImageFont
            # 創建一個2500x843的白色圖片
            img = Image.new('RGB', (2500, 843), color=(255, 255, 255))
            
            # 獲取繪圖工具
            draw = ImageDraw.Draw(img)
            
            # 定義區域邊界
            area1 = (0, 0, 833, 843)
            area2 = (833, 0, 1667, 843)
            area3 = (1667, 0, 2500, 843)
            
            # 使用默認字體
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
        except Exception as e:
            print(f"創建圖片時出錯: {e}")
            # 如果無法創建圖片，嘗試創建一個空白圖片
            try:
                with open('rich_menu_image.jpg', 'wb') as f:
                    # 創建一個最小的白色JPEG圖片
                    f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xdb\x00C\x01\t\t\t\x0c\x0b\x0c\x18\r\r\x182!\x1c!22222222222222222222222222222222222222222222222222\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x03\x01"\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&\'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xc4\x00\x1f\x01\x00\x03\x01\x01\x01\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x11\x00\x02\x01\x02\x04\x04\x03\x04\x07\x05\x04\x04\x00\x01\x02w\x00\x01\x02\x03\x11\x04\x05!1\x06\x12AQ\x07aq\x13"2\x81\x08\x14B\x91\xa1\xb1\xc1\t#3R\xf0\x15br\xd1\n\x16$4\xe1%\xf1\x17\x18\x19\x1a&\'()*56789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00?\x00\xfe\xfe(\xa2\x8a\x00\xff\xd9')
                    print("已創建簡單的空白圖像作為替代")
            except Exception as e:
                print(f"創建空白圖像時也出錯: {e}")

# 初始化 Rich Menu
def init_rich_menu():
    try:
        # 確保Rich Menu圖片存在
        print("正在確保Rich Menu圖片存在...")
        ensure_rich_menu_image()
        
        # 檢查圖片是否存在
        if not os.path.exists('rich_menu_image.jpg'):
            print("無法找到Rich Menu圖片，初始化失敗")
            return None
        
        print("圖片存在，開始創建Rich Menu...")
        
        # 創建 Rich Menu - 使用RichMenuRequest替代CreateRichMenuRequest
        rich_menu_to_create = RichMenuRequest(
            size=RichMenuSize(width=2500, height=843),
            selected=True,
            name="活動管理主選單",
            chat_bar_text="開啟活動管理選單",
            areas=[
                RichMenuArea(
                    bounds=RichMenuBounds(x=0, y=0, width=833, height=843),
                    action=PostbackAction(label="設定活動", data="action=open_event_form_flex")
                ),
                RichMenuArea(
                    bounds=RichMenuBounds(x=833, y=0, width=834, height=843),
                    action=PostbackAction(label="查詢活動", data="action=open_query_form")
                ),
                RichMenuArea(
                    bounds=RichMenuBounds(x=1667, y=0, width=833, height=843),
                    action=MessageAction(label="手動提醒", text="手動提醒")
                )
            ]
        )
        
        # 使用create_rich_menu方法創建
        print("呼叫LINE API創建Rich Menu...")
        response = line_bot_api.create_rich_menu(rich_menu_to_create)
        rich_menu_id = response.rich_menu_id
        print(f"已創建 Rich Menu，ID: {rich_menu_id}")
        
        # 使用requests直接調用LINE API來上傳圖片
        print("正在上傳Rich Menu圖片...")
        try:
            import requests
            from requests_toolbelt.multipart.encoder import MultipartEncoder
            
            with open('rich_menu_image.jpg', 'rb') as f:
                image_data = f.read()
                print(f"讀取圖片成功，大小: {len(image_data)} 字節")
                
                url = f'https://api-data.line.me/v2/bot/richmenu/{rich_menu_id}/content'
                headers = {
                    'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}',
                    'Content-Type': 'image/jpeg'
                }
                
                print(f"直接呼叫LINE API上傳圖片: {url}")
                response = requests.post(url, headers=headers, data=image_data)
                
                if response.status_code == 200:
                    print("上傳圖片成功!")
                else:
                    print(f"上傳圖片失敗: {response.status_code}, {response.text}")
                    raise Exception(f"上傳圖片失敗: {response.status_code}, {response.text}")
        except Exception as e:
            print(f"上傳圖片時發生錯誤: {e}")
            raise e
        
        # 使用requests直接調用LINE API來設置默認Rich Menu
        print("正在設置為默認Rich Menu...")
        try:
            url = f'https://api.line.me/v2/bot/user/all/richmenu/{rich_menu_id}'
            headers = {
                'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'
            }
            
            print(f"直接呼叫LINE API設置默認Rich Menu: {url}")
            response = requests.post(url, headers=headers)
            
            if response.status_code == 200:
                print("設置默認Rich Menu成功!")
            else:
                print(f"設置默認Rich Menu失敗: {response.status_code}, {response.text}")
                raise Exception(f"設置默認Rich Menu失敗: {response.status_code}, {response.text}")
        except Exception as e:
            print(f"設置默認Rich Menu時發生錯誤: {e}")
            raise e
        
        print("Rich Menu 設定成功")
        
        return rich_menu_id
    except Exception as e:
        print(f"創建 Rich Menu 時發生錯誤: {e}")
        # 添加更詳細的錯誤信息
        import traceback
        print(f"詳細錯誤堆疊:\n{traceback.format_exc()}")
        return None

# 全局變數，用於存儲用戶的日期選擇狀態
user_date_selection = {}

# 全局變數，用於存儲所有用戶狀態
# 使用結構化格式：
# user_states[user_id] = {
#     'event_creation': {...},  # 用於存儲活動創建相關狀態
#     'flex_form': {...},       # 用於存儲Flex表單相關狀態 
#     'query': {...}            # 用於存儲查詢相關狀態
# }
user_states = {}

# 為了向後兼容，保留這些變數但將其指向user_states
user_event_creation = user_states  # 將在下一版本移除
user_state = user_states  # 將在下一版本移除

# 在應用啟動時初始化 Rich Menu
rich_menu_id = None

@app.route("/callback", methods=['POST'])
def callback():
    # 取得 X-Line-Signature 標頭值
    signature = request.headers['X-Line-Signature']

    # 取得請求內容
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # 驗證簽名
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@app.route("/init_rich_menu", methods=['GET'])
def init_rich_menu_route():
    """初始化Rich Menu的路由"""
    global rich_menu_id
    try:
        if rich_menu_id is None:
            print("開始初始化Rich Menu...")
            # 捕獲詳細的錯誤信息
            try:
                rich_menu_id = init_rich_menu()
                if rich_menu_id:
                    print(f"Rich Menu初始化成功，ID: {rich_menu_id}")
                    return f"Rich Menu 初始化成功，ID: {rich_menu_id}"
                else:
                    print("Rich Menu初始化失敗，返回為None")
                    return "Rich Menu 初始化失敗，請檢查伺服器日誌"
            except Exception as inner_e:
                error_message = f"初始化Rich Menu時發生內部錯誤: {str(inner_e)}"
                import traceback
                error_trace = traceback.format_exc()
                print(f"{error_message}\n{error_trace}")
                return f"初始化Rich Menu時發生錯誤: {str(inner_e)}\n\n詳細信息: {error_trace}"
        else:
            print(f"Rich Menu已存在，ID: {rich_menu_id}")
            return f"Rich Menu 已存在，ID: {rich_menu_id}"
    except Exception as e:
        error_message = f"初始化Rich Menu時發生錯誤: {str(e)}"
        print(error_message)
        # 打印更多詳細信息
        import traceback
        error_trace = traceback.format_exc()
        print(f"詳細錯誤信息:\n{error_trace}")
        return f"初始化Rich Menu時發生錯誤: {str(e)}\n\n詳細信息: {error_trace}"

@handler.add(MessageEvent)
def handle_message(event):
    try:
        # 打印用戶ID - 添加在這裡，確保每次收到文字消息時都會打印
        user_id = event.source.user_id
        print(f"用戶 ID: {user_id}")
        print(f"完整事件: {event}")
        
        # 檢查是否為文字消息
        if isinstance(event.message, TextMessageContent):
            # 獲取用戶發送的文字消息
            user_text = event.message.text.strip()
            reply_token = event.reply_token
            
            # 檢查是否為設定活動的指令
            if user_text.startswith("設定活動:"):
                handle_add_event(user_text, reply_token, user_id)
            
            # 檢查是否為查詢活動的指令
            elif user_text.startswith("查詢活動:"):
                handle_query_events(user_text, reply_token, user_id)
            
            # 檢查是否為手動提醒的指令
            elif user_text == "手動提醒":
                response_text = event_reminder.manual_remind(user_id)
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=reply_token,
                        messages=[TextMessage(text=response_text)]
                    )
                )
            
            # 檢查是否為幫助指令
            elif user_text == "幫助" or user_text == "help":
                send_help_message(reply_token)
            
            # 新增：設定活動表單請求
            elif user_text == "設定活動":
                start_event_creation_flow(reply_token, user_id)
            
            # 新增：查詢活動日期選擇請求
            elif user_text == "查詢活動":
                send_query_form_with_quick_reply(reply_token)
                
            # 新增：處理LIFF輸入活動名稱
            elif user_text.startswith("LIFF_NAME:"):
                name = user_text[10:].strip()
                handle_liff_name_input(name, reply_token, user_id)
                
            # 新增：處理LIFF輸入備註
            elif user_text.startswith("LIFF_NOTES:"):
                notes = user_text[11:].strip()
                handle_liff_notes_input(notes, reply_token, user_id)

            # 處理設定活動流程中的活動名稱輸入（修改：添加支持Flex表單）
            elif (user_id in user_states and 
                  (('event_creation' in user_states[user_id] and user_states[user_id]['event_creation'].get('step') == 'waiting_for_name') or
                   ('flex_form' in user_states[user_id] and user_states[user_id]['flex_form'].get('step') == 'waiting_for_flex_name'))):
                
                if 'flex_form' in user_states[user_id] and user_states[user_id]['flex_form'].get('step') == 'waiting_for_flex_name':
                    # 處理Flex表單的名稱輸入
                    user_states[user_id]['flex_form']['name'] = user_text
                    
                    # 詢問是否需要備註
                    template_message = TemplateMessage(
                        alt_text="是否需要備註",
                        template=ConfirmTemplate(
                            text="是否需要添加備註？",
                            actions=[
                                PostbackAction(
                                    label="是",
                                    data="action=need_notes_flex&value=yes"
                                ),
                                PostbackAction(
                                    label="否",
                                    data="action=need_notes_flex&value=no"
                                )
                            ]
                        )
                    )
                    
                    line_bot_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=reply_token,
                            messages=[template_message]
                        )
                    )
                else:
                    # 處理常規流程的名稱輸入
                    handle_event_name_input(user_text, reply_token, user_id)
                
            # 處理設定活動流程中的備註輸入（修改：添加支持Flex表單）
            elif (user_id in user_states and 
                  (('event_creation' in user_states[user_id] and user_states[user_id]['event_creation'].get('step') == 'waiting_for_notes') or
                   ('flex_form' in user_states[user_id] and user_states[user_id]['flex_form'].get('step') == 'waiting_for_flex_notes'))):
                
                if 'flex_form' in user_states[user_id] and user_states[user_id]['flex_form'].get('step') == 'waiting_for_flex_notes':
                    # 處理Flex表單的備註輸入
                    # 如果用戶輸入「無」或「n」，則設置備註為空字符串
                    notes = user_text
                    if notes.lower() in ['無', 'none', 'n/a', '', 'n']:
                        notes = ""
                    
                    user_states[user_id]['flex_form']['notes'] = notes
                    
                    # 創建完整的提交確認消息
                    flex_form = user_states[user_id]['flex_form']
                    confirm_message = f"請確認活動資訊:\n\n"
                    
                    if 'datetime' in flex_form:
                        confirm_message += f"時間: {flex_form['datetime']}\n"
                    if 'importance' in flex_form:
                        confirm_message += f"重要性: {flex_form['importance']}\n"
                    if 'category' in flex_form:
                        confirm_message += f"分類: {flex_form['category']}\n"
                    if 'name' in flex_form:
                        confirm_message += f"活動名稱: {flex_form['name']}\n"
                    if notes:
                        confirm_message += f"備註: {notes}\n"
                    
                    # 發送確認按鈕
                    
                    # 更新用戶狀態，表示等待確認
                    user_states[user_id]['flex_form']['step'] = 'waiting_for_confirmation'
                    
                    # 添加無備註信息
                    if not notes:
                        confirm_message += f"備註: (無備註)\n"
                    
                    # 使用共用函數發送確認訊息
                    send_confirmation_message(reply_token, confirm_message, is_flex=True)
                else:
                    # 處理常規流程的備註輸入 - 修正：將參數從notes改為user_text
                    handle_event_notes_input(user_text, reply_token, user_id)

            # 新增：處理分類消息
            elif user_text.startswith("分類:") and user_id in user_states and 'event_creation' in user_states[user_id]:
                category = user_text[3:].strip()
                handle_category_selection(category, reply_token, user_id)
            
            # 新增：處理時間選擇消息
            elif user_text.startswith("選擇時間:") and user_id in user_states and 'event_creation' in user_states[user_id] and user_states[user_id]['event_creation'].get('step') == 'selecting_datetime':
                # 解析時間字符串
                try:
                    # 從消息中提取時間
                    time_str = user_text[5:].strip()
                    
                    # 解析日期時間字符串
                    selected_time = datetime.strptime(time_str, "%Y/%m/%d %H:%M")
                    
                    # 確保時間有時區信息
                    selected_time = selected_time.replace(tzinfo=timezone.utc)
                    
                    # 保存到用戶的活動創建狀態中
                    user_states[user_id]['event_creation']['datetime'] = time_str
                    user_states[user_id]['event_creation']['step'] = 'selecting_importance'
                    
                    # 創建重要性選擇的QuickReply選項
                    importance_items = [
                        QuickReplyItem(
                            action=MessageAction(
                                label="高重要性",
                                text="重要性:高"
                            )
                        ),
                        QuickReplyItem(
                            action=MessageAction(
                                label="中重要性",
                                text="重要性:中"
                            )
                        ),
                        QuickReplyItem(
                            action=MessageAction(
                                label="低重要性",
                                text="重要性:低"
                            )
                        )
                    ]
                    
                    # 創建含有QuickReply的文字訊息
                    importance_message = TextMessage(
                        text=f"📅 設定活動 (步驟 2/4)\n您選擇的時間是: {time_str}\n\n請選擇活動的重要性等級：",
                        quick_reply=QuickReply(items=importance_items)
                    )
                    
                    line_bot_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=reply_token,
                            messages=[importance_message]
                        )
                    )
                except Exception as e:
                    print(f"處理時間選擇時出錯: {e}")
                    line_bot_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=reply_token,
                            messages=[TextMessage(text="時間格式不正確，請重新選擇")]
                        )
                    )
            
            # 新增：處理重要性選擇消息
            elif user_text.startswith("重要性:") and user_id in user_states and 'event_creation' in user_states[user_id] and user_states[user_id]['event_creation'].get('step') == 'selecting_importance':
                # 解析重要性
                importance = user_text[4:].strip()
                
                # 驗證重要性
                valid_importance = ["高", "中", "低"]
                if importance not in valid_importance:
                    line_bot_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=reply_token,
                            messages=[TextMessage(text=f"無效的重要性: {importance}。請使用「高」、「中」或「低」。")]
                        )
                    )
                    return
                
                # 保存到用戶的活動創建狀態中
                user_states[user_id]['event_creation']['importance'] = importance
                user_states[user_id]['event_creation']['step'] = 'selecting_category'
                
                # 顯示已完成的設定
                progress_message = f"您已設定：\n時間: {user_states[user_id]['event_creation']['datetime']}\n重要性: {importance}\n\n"
                
                # 發送分類選擇器
                category_quick_reply = QuickReply(
                    items=[
                        QuickReplyItem(
                            action=MessageAction(
                                label="會議",
                                text="分類:會議"
                            )
                        ),
                        QuickReplyItem(
                            action=MessageAction(
                                label="活動",
                                text="分類:活動"
                            )
                        ),
                        QuickReplyItem(
                            action=MessageAction(
                                label="提醒",
                                text="分類:提醒"
                            )
                        ),
                        QuickReplyItem(
                            action=MessageAction(
                                label="任務",
                                text="分類:任務"
                            )
                        ),
                        QuickReplyItem(
                            action=MessageAction(
                                label="其他",
                                text="分類:其他"
                            )
                        )
                    ]
                )
                
                # 發送分類選擇消息
                category_message = TextMessage(
                    text=f"📅 設定活動 (步驟 3/4)\n{progress_message}請選擇活動分類：",
                    quick_reply=category_quick_reply
                )
                
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=reply_token,
                        messages=[category_message]
                    )
                )
            
            # 其他情況，回覆相同的訊息並附帶快速回覆按鈕
            else:
                send_message_with_quick_reply(reply_token, user_text)
    except Exception as e:
        print(f"處理消息時出錯: {e}")

# 處理按鈕點擊事件
@handler.add(PostbackEvent)
def handle_postback(event):
    """處理 postback 事件"""
    try:
        user_id = event.source.user_id
        reply_token = event.reply_token
        data = event.postback.data
        
        print(f"收到 postback 事件: {data}")
        print(f"完整 postback 事件: data='{data}' params={event.postback.params}")
        
        # 處理活動確認或取消
        if data == "action=confirm_event":
            handle_event_confirmation(reply_token, user_id, is_flex=False)
        elif data == "action=confirm_event_flex":
            handle_event_confirmation(reply_token, user_id, is_flex=True)
        elif data == "action=cancel_event":
            handle_event_cancellation(reply_token, user_id, is_flex=False)
        elif data == "action=cancel_event_flex":
            handle_event_cancellation(reply_token, user_id, is_flex=True)
        # 處理開啟Flex表單
        elif data == "action=open_event_form_flex":
            send_event_creation_flex(reply_token, user_id)
        # 處理自訂時間選擇
        elif data == "action=select_custom_time" and event.postback.params and "datetime" in event.postback.params:
            selected_datetime = event.postback.params["datetime"]
            
            # 格式化日期時間
            dt_obj = datetime.strptime(selected_datetime, "%Y-%m-%dT%H:%M")
            formatted_datetime = dt_obj.strftime("%Y/%m/%d %H:%M")
            
            # 保存到用戶的活動創建狀態中
            if user_id not in user_states:
                user_states[user_id] = {}
            
            if 'event_creation' not in user_states[user_id]:
                user_states[user_id]['event_creation'] = {}
                
            user_states[user_id]['event_creation']['datetime'] = formatted_datetime
            user_states[user_id]['event_creation']['step'] = 'selecting_importance'
            
            # 創建重要性選擇的QuickReply選項
            importance_items = [
                QuickReplyItem(
                    action=MessageAction(
                        label="高重要性",
                        text="重要性:高"
                    )
                ),
                QuickReplyItem(
                    action=MessageAction(
                        label="中重要性",
                        text="重要性:中"
                    )
                ),
                QuickReplyItem(
                    action=MessageAction(
                        label="低重要性",
                        text="重要性:低"
                    )
                )
            ]
            
            # 創建含有QuickReply的文字訊息
            importance_message = TextMessage(
                text=f"📅 設定活動 (步驟 2/4)\n您選擇的時間是: {formatted_datetime}\n\n請選擇活動的重要性等級：",
                quick_reply=QuickReply(items=importance_items)
            )
            
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[importance_message]
                )
            )
            
        # 處理日期選擇（用於查詢單一日期）
        elif data == "action=select_date" and event.postback.params and "date" in event.postback.params:
            date_str = event.postback.params["date"]
            start_date = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
            end_date = start_date.replace(hour=23, minute=59, second=59)
            events = notion_manager.query_events(start_date, end_date)
            send_query_results(reply_token, start_date, end_date, events)
            return
        # 處理查詢範圍開始日期選擇
        elif data == "action=select_start_date" and event.postback.params and "date" in event.postback.params:
            start_date_str = event.postback.params["date"]
            
            # 保存開始日期到用戶狀態
            if user_id not in user_states:
                user_states[user_id] = {}
            
            user_states[user_id]['query_start_date'] = start_date_str
            
            # 顯示結束日期選擇器
            send_end_date_picker(reply_token, start_date_str)
            
        # 處理查詢範圍結束日期選擇
        elif data == "action=select_end_date" and event.postback.params and "date" in event.postback.params:
            end_date_str = event.postback.params["date"]
            
            # 獲取之前保存的開始日期
            if user_id in user_states and 'query_start_date' in user_states[user_id]:
                start_date_str = user_states[user_id]['query_start_date']
                
                # 轉換日期格式並添加時區信息
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
                
                # 檢查日期順序
                if end_date < start_date:
                    line_bot_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=reply_token,
                            messages=[TextMessage(text="結束日期不能早於開始日期，請重新選擇")]
                        )
                    )
                    return
                
                # 查詢事件並顯示結果
                events = notion_manager.query_events(start_date, end_date)
                send_query_results(reply_token, start_date, end_date, events)
                
                # 清理用戶狀態
                del user_states[user_id]['query_start_date']
            else:
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=reply_token,
                        messages=[TextMessage(text="請先選擇開始日期")]
                    )
                )
        # 處理事件時間選擇
        elif data == "action=select_event_date" and event.postback.params and "datetime" in event.postback.params:
            selected_datetime = event.postback.params["datetime"]
            
            # 確保使用者狀態存在
            if user_id not in user_state:
                user_state[user_id] = {}
            
            if "flex_form_data" not in user_state[user_id]:
                user_state[user_id]["flex_form_data"] = {}
            
            # 從 LINE 返回的日期時間格式（YYYY-MM-DDTHH:mm）轉換為我們使用的格式（YYYY/MM/DD HH:mm）
            dt_obj = datetime.strptime(selected_datetime, "%Y-%m-%dT%H:%M")
            formatted_datetime = dt_obj.strftime("%Y/%m/%d %H:%M")
            
            # 保存到用戶的表單數據中
            user_state[user_id]["flex_form_data"]["datetime"] = formatted_datetime
            
            # 回覆用戶確認消息
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=f"已選擇時間: {formatted_datetime}")]
                )
            )
        # 處理查詢單一日期
        elif data == "action=query_date" and event.postback.params and "date" in event.postback.params:
            date_str = event.postback.params["date"]
            start_date = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
            end_date = start_date.replace(hour=23, minute=59, second=59)
            events = notion_manager.query_events(start_date, end_date)
            send_query_results(reply_token, start_date, end_date, events)
            
        # 處理查詢今天
        elif data == "action=query_today":
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
            end_date = today.replace(hour=23, minute=59, second=59)
            events = notion_manager.query_events(today, end_date)
            send_query_results(reply_token, today, end_date, events)
            
        # 處理查詢未來7天
        elif data == "action=query_next7days":
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
            end_date = (today + timedelta(days=7)).replace(hour=23, minute=59, second=59)
            events = notion_manager.query_events(today, end_date)
            send_query_results(reply_token, today, end_date, events)
            
        # 處理查詢本月
        elif data == "action=query_month":
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0, day=1, tzinfo=timezone.utc)
            if today.month == 12:
                end_date = datetime(today.year + 1, 1, 1, 23, 59, 59, tzinfo=timezone.utc) - timedelta(days=1)
            else:
                end_date = datetime(today.year, today.month + 1, 1, 23, 59, 59, tzinfo=timezone.utc) - timedelta(days=1)
            events = notion_manager.query_events(today, end_date)
            send_query_results(reply_token, today, end_date, events)
            
        # 處理查詢本年
        elif data == "action=query_year":
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0, day=1, month=1, tzinfo=timezone.utc)
            end_date = datetime(today.year + 1, 1, 1, 0, 0, 0, tzinfo=timezone.utc) - timedelta(seconds=1)
            events = notion_manager.query_events(today, end_date)
            send_query_results(reply_token, today, end_date, events)

        # 處理日期選擇器開啟表單
        elif data == "action=open_query_form":
            send_query_form_with_quick_reply(reply_token)
            
        # 處理日期範圍選擇
        elif data == "action=select_date_range":
            send_start_date_picker(reply_token)

        # 處理其他操作
        elif data == "action=open_event_form":
            handle_query_events(data, reply_token, user_id)
        elif data == "action=select_datetime_flex" and event.postback.params and "datetime" in event.postback.params:
            # 處理Flex表單的日期時間選擇
            selected_datetime = event.postback.params["datetime"]
            
            # 格式化日期時間
            dt_obj = datetime.strptime(selected_datetime, "%Y-%m-%dT%H:%M")
            formatted_datetime = dt_obj.strftime("%Y/%m/%d %H:%M")
            
            # 保存到用戶的Flex表單狀態中
            if user_id not in user_states:
                user_states[user_id] = {}
            
            if 'flex_form' not in user_states[user_id]:
                user_states[user_id]['flex_form'] = {}
                
            user_states[user_id]['flex_form']['datetime'] = formatted_datetime
            
            # 發送確認消息
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=f"已選擇時間: {formatted_datetime}\n請繼續選擇重要性和分類")]
                )
            )
        elif data.startswith("action=select_importance_flex"):
            # 從data參數中提取重要性值
            importance = data.split("value=")[1] if "value=" in data else "中"
            
            # 保存重要性到用戶的Flex表單狀態中
            if user_id not in user_states:
                user_states[user_id] = {}
            
            if 'flex_form' not in user_states[user_id]:
                user_states[user_id]['flex_form'] = {}
                
            user_states[user_id]['flex_form']['importance'] = importance
            
            # 發送確認消息
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=f"已選擇重要性: {importance}\n請繼續選擇分類")]
                )
            )
        elif data.startswith("action=select_category_flex"):
            # 從data參數中提取分類值
            category = data.split("value=")[1] if "value=" in data else "活動"
            
            # 保存分類到用戶的Flex表單狀態中
            if user_id not in user_states:
                user_states[user_id] = {}
            
            if 'flex_form' not in user_states[user_id]:
                user_states[user_id]['flex_form'] = {
                    'datetime': datetime.now().strftime("%Y/%m/%d %H:%M"),  # 默認為當前時間
                    'importance': '中'  # 默認為中等重要性
                }
                
            user_states[user_id]['flex_form']['category'] = category
            
            # 確保設置了默認值
            if 'datetime' not in user_states[user_id]['flex_form'] or not user_states[user_id]['flex_form']['datetime']:
                user_states[user_id]['flex_form']['datetime'] = datetime.now().strftime("%Y/%m/%d %H:%M")
                
            if 'importance' not in user_states[user_id]['flex_form'] or not user_states[user_id]['flex_form']['importance']:
                user_states[user_id]['flex_form']['importance'] = '中'
                
            user_states[user_id]['flex_form']['step'] = 'waiting_for_flex_name'
            
            # 創建含QuickReply的消息以繼續收集信息
            quick_reply_items = [
                QuickReplyItem(
                    action=MessageAction(
                        label="取消",
                        text="取消設定活動"
                    )
                )
            ]
            
            # 創建含有QuickReply的訊息
            message = TextMessage(
                text=f"已選擇分類: {category}\n\n請直接輸入活動名稱：",
                quick_reply=QuickReply(items=quick_reply_items)
            )
            
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[message]
                )
            )
        elif data.startswith("action=need_notes_flex"):
            # 從data參數中提取是否需要備註
            need_notes = data.split("value=")[1] if "value=" in data else "no"
            
            if need_notes.lower() == "yes":
                # 用戶希望添加備註
                if user_id not in user_states:
                    user_states[user_id] = {}
                
                if 'flex_form' not in user_states[user_id]:
                    user_states[user_id]['flex_form'] = {}
                    
                user_states[user_id]['flex_form']['step'] = 'waiting_for_flex_notes'
                
                # 創建含QuickReply的消息
                quick_reply_items = [
                    QuickReplyItem(
                        action=MessageAction(
                            label="取消備註",
                            text="無"
                        )
                    )
                ]
                
                # 創建含有QuickReply的訊息
                message = TextMessage(
                    text="請直接輸入備註，或選擇「取消備註」跳過：",
                    quick_reply=QuickReply(items=quick_reply_items)
                )
                
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=reply_token,
                        messages=[message]
                    )
                )
            else:
                # 用戶不需要添加備註，直接進入確認步驟
                if user_id not in user_states:
                    user_states[user_id] = {}
                
                if 'flex_form' not in user_states[user_id]:
                    user_states[user_id]['flex_form'] = {}
                    
                user_states[user_id]['flex_form']['notes'] = ""
                
                # 構建確認信息
                flex_form = user_states[user_id]['flex_form']
                confirm_message = "請確認活動資訊:\n"
                
                if 'datetime' in flex_form:
                    confirm_message += f"時間: {flex_form['datetime']}\n"
                if 'importance' in flex_form:
                    confirm_message += f"重要性: {flex_form['importance']}\n"
                if 'category' in flex_form:
                    confirm_message += f"分類: {flex_form['category']}\n"
                if 'name' in flex_form:
                    confirm_message += f"活動名稱: {flex_form['name']}\n"
                
                confirm_message += f"備註: (無備註)"
                
                # 設置用戶狀態為等待確認
                user_states[user_id]['flex_form']['step'] = 'waiting_for_confirmation'
                
                # 發送確認訊息
                send_confirmation_message(reply_token, confirm_message, is_flex=True)
        elif data == "action=set_importance":
            handle_query_events(data, reply_token, user_id)
        # 處理選擇重要性按鈕
        elif data.startswith("action=set_importance"):
            # 從data參數中提取重要性值
            importance = data.split("value=")[1] if "value=" in data else "中"
            
            # 保存重要性到用戶的活動創建狀態中
            if user_id in user_states and 'event_creation' in user_states[user_id] and user_states[user_id]['event_creation'].get('step') == 'selecting_importance':
                user_states[user_id]['event_creation']['importance'] = importance
                user_states[user_id]['event_creation']['step'] = 'selecting_category'
                
                # 顯示已完成的設定
                progress_message = f"您已設定：\n時間: {user_states[user_id]['event_creation']['datetime']}\n重要性: {importance}\n\n"
                
                # 發送分類選擇器
                category_quick_reply = QuickReply(
                    items=[
                        QuickReplyItem(
                            action=MessageAction(
                                label="會議",
                                text="分類:會議"
                            )
                        ),
                        QuickReplyItem(
                            action=MessageAction(
                                label="活動",
                                text="分類:活動"
                            )
                        ),
                        QuickReplyItem(
                            action=MessageAction(
                                label="提醒",
                                text="分類:提醒"
                            )
                        ),
                        QuickReplyItem(
                            action=MessageAction(
                                label="任務",
                                text="分類:任務"
                            )
                        ),
                        QuickReplyItem(
                            action=MessageAction(
                                label="其他",
                                text="分類:其他"
                            )
                        )
                    ]
                )
                
                category_message = TextMessage(
                    text=progress_message + "📅 設定活動 (步驟 3/4)\n請選擇活動分類",
                    quick_reply=category_quick_reply
                )
                
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=reply_token,
                        messages=[category_message]
                    )
                )
            else:
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=reply_token,
                        messages=[TextMessage(text="請先選擇活動時間")]
                    )
                )
    except Exception as e:
        print(f"處理 postback 時出錯: {e}")
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text="處理請求時發生錯誤，請稍後再試")]
            )
        )

# 新增：發送主選單
def send_main_menu(reply_token):
    buttons_template = ButtonsTemplate(
        title="📅 活動管理主選單",
        text="請選擇您要使用的功能",
        actions=[
            PostbackAction(
                label="設定活動",
                data="action=open_event_form"
            ),
            PostbackAction(
                label="查詢活動",
                data="action=open_query_form"
            ),
            MessageAction(
                label="手動提醒",
                text="手動提醒"
            ),
            MessageAction(
                label="幫助",
                text="幫助"
            )
        ]
    )
    
    template_message = TemplateMessage(
        alt_text="主選單",
        template=buttons_template
    )
    
    line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[template_message]
        )
    )

# 開始活動創建流程
def start_event_creation_flow(reply_token, user_id):
    # 重置用戶的活動創建狀態
    if user_id not in user_states:
        user_states[user_id] = {}
        
    # 初始化或重置event_creation狀態
    user_states[user_id]['event_creation'] = {
        'step': 'selecting_datetime'
    }
    
    # 創建時間選擇的QuickReply選項
    today = datetime.now().strftime("%Y/%m/%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y/%m/%d")
    
    quick_reply_items = [
        QuickReplyItem(
            action=DatetimePickerAction(
                label="自訂時間",
                data="action=select_custom_time",
                mode="datetime"
            )
        ),
        QuickReplyItem(
            action=MessageAction(
                label="今天8點",
                text=f"選擇時間:{today} 08:00"
            )
        ),
        QuickReplyItem(
            action=MessageAction(
                label="今天10點",
                text=f"選擇時間:{today} 10:00"
            )
        ),
        QuickReplyItem(
            action=MessageAction(
                label="今天12點",
                text=f"選擇時間:{today} 12:00"
            )
        ),
        QuickReplyItem(
            action=MessageAction(
                label="今天14點",
                text=f"選擇時間:{today} 14:00"
            )
        ),
        QuickReplyItem(
            action=MessageAction(
                label="今天17點",
                text=f"選擇時間:{today} 17:00"
            )
        ),
        QuickReplyItem(
            action=MessageAction(
                label="明天8點",
                text=f"選擇時間:{tomorrow} 08:00"
            )
        ),
        QuickReplyItem(
            action=MessageAction(
                label="明天12點",
                text=f"選擇時間:{tomorrow} 12:00"
            )
        ),
        QuickReplyItem(
            action=MessageAction(
                label="明天14點",
                text=f"選擇時間:{tomorrow} 14:00"
            )
        ),
        QuickReplyItem(
            action=MessageAction(
                label="明天16點",
                text=f"選擇時間:{tomorrow} 16:00"
            )
        )
    ]
    
    # 創建含有QuickReply的文字訊息
    guide_message = TextMessage(
        text="請按照以下步驟設定活動：\n1. 選擇日期和時間\n2. 選擇活動重要性\n3. 選擇活動分類\n4. 輸入活動名稱和備註"
    )
    
    time_selection_message = TextMessage(
        text="📅 設定活動 (步驟 1/4)\n請選擇活動的日期和時間：",
        quick_reply=QuickReply(items=quick_reply_items)
    )
    
    line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[guide_message, time_selection_message]
        )
    )

# 發送重要性選擇器
def send_importance_selector(reply_token):
    # 創建重要性選擇按鈕
    importance_buttons = [
        PostbackAction(
            label="高重要性",
            data="action=set_importance&value=高"
        ),
        PostbackAction(
            label="中重要性",
            data="action=set_importance&value=中"
        ),
        PostbackAction(
            label="低重要性",
            data="action=set_importance&value=低"
        )
    ]
    
    # 創建重要性選擇模板
    importance_template = TemplateMessage(
        alt_text="選擇活動重要性",
        template=ButtonsTemplate(
            title="📅 設定活動 (步驟 2/4)",
            text="請選擇活動的重要性等級",
            actions=importance_buttons
        )
    )
    
    line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[importance_template]
        )
    )

# 發送分類選擇器
def send_category_selector(reply_token):
    # 創建分類選擇快速回覆
    category_quick_reply = QuickReply(
        items=[
            QuickReplyItem(
                action=MessageAction(
                    label="會議",
                    text="分類:會議"
                )
            ),
            QuickReplyItem(
                action=MessageAction(
                    label="活動",
                    text="分類:活動"
                )
            ),
            QuickReplyItem(
                action=MessageAction(
                    label="提醒",
                    text="分類:提醒"
                )
            ),
            QuickReplyItem(
                action=MessageAction(
                    label="任務",
                    text="分類:任務"
                )
            ),
            QuickReplyItem(
                action=MessageAction(
                    label="其他",
                    text="分類:其他"
                )
            )
        ]
    )
    
    # 發送分類選擇消息
    category_message = TextMessage(
        text="📅 設定活動 (步驟 3/4)\n請選擇活動分類",
        quick_reply=category_quick_reply
    )
    
    line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[category_message]
        )
    )

# 處理分類選擇
def handle_category_selection(category, reply_token, user_id):
    """處理分類選擇"""
    # 檢查用戶狀態是否正確
    if user_id in user_states and 'event_creation' in user_states[user_id] and user_states[user_id]['event_creation'].get('step') == 'selecting_category':
        # 保存分類
        user_states[user_id]['event_creation']['category'] = category
        user_states[user_id]['event_creation']['step'] = 'waiting_for_name'
        
        # 顯示已完成的設置
        progress_message = f"您已設定：\n時間: {user_states[user_id]['event_creation']['datetime']}\n重要性: {user_states[user_id]['event_creation']['importance']}\n分類: {category}\n\n"
        
        # 提示用戶輸入活動名稱
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=progress_message + "請輸入活動名稱：")]
            )
        )
    else:
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text="請先設定活動時間和重要性")]
            )
        )

# 處理活動名稱輸入
def handle_event_name_input(event_name, reply_token, user_id):
    """處理活動名稱輸入"""
    if user_id in user_states and 'event_creation' in user_states[user_id] and user_states[user_id]['event_creation'].get('step') == 'waiting_for_name':
        # 保存活動名稱
        user_states[user_id]['event_creation']['name'] = event_name
        
        # 詢問備註 - 修改為單一按鈕
        quick_reply_items = [
            QuickReplyItem(
                action=MessageAction(
                    label="取消備註",
                    text="無"
                )
            )
        ]
        
        message = TextMessage(
            text="請直接輸入備註，或選擇「取消備註」跳過：",
            quick_reply=QuickReply(items=quick_reply_items)
        )
        
        # 更新用戶狀態為等待備註輸入
        user_states[user_id]['event_creation']['step'] = 'waiting_for_notes'
        
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[message]
            )
        )
    else:
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text="請先設定活動時間、重要性和分類")]
            )
        )

# 處理備註輸入並完成活動創建
def handle_event_notes_input(notes, reply_token, user_id):
    """處理用戶輸入的活動備註"""
    if user_id in user_states and 'event_creation' in user_states[user_id] and user_states[user_id]['event_creation'].get('step') == 'waiting_for_notes':
        # 如果用戶輸入「無」或「n」，則設置備註為空字符串
        if notes.lower() in ['無', 'none', 'n/a', '', 'n']:
            notes = ""
            
        # 保存備註
        user_states[user_id]['event_creation']['notes'] = notes
        
        # 創建活動確認訊息
        confirm_message = f"請確認活動資訊:\n\n"
        confirm_message += f"時間: {user_states[user_id]['event_creation']['datetime']}\n"
        confirm_message += f"重要性: {user_states[user_id]['event_creation']['importance']}\n"
        confirm_message += f"分類: {user_states[user_id]['event_creation']['category']}\n"
        confirm_message += f"活動名稱: {user_states[user_id]['event_creation']['name']}\n"
        if notes:
            confirm_message += f"備註: {notes}\n"
        else:
            confirm_message += "備註: (無備註)\n"
        
        # 更新用戶狀態為等待確認
        user_states[user_id]['event_creation']['step'] = 'waiting_for_confirmation'
        
        # 使用共用函數發送確認訊息
        send_confirmation_message(reply_token, confirm_message, is_flex=False)

# 新增：發送活動查詢表單
def send_query_form(reply_token):
    # 創建單一日期選擇器
    date_picker = DatetimePickerAction(
        label="選擇單一日期",
        data="action=query_date",
        mode="date"
    )
    
    # 創建日期範圍選擇
    date_range_picker = PostbackAction(
        label="選擇日期範圍",
        data="action=select_date_range"
    )
    
    # 快速查詢選項
    quick_queries = [
        PostbackAction(
            label="查詢今天",
            data="action=query_today"
        ),
        PostbackAction(
            label="查詢後7天",
            data="action=query_next7days"
        ),
        PostbackAction(
            label="查詢本月",
            data="action=query_month"
        ),
        PostbackAction(
            label="查詢本年",
            data="action=query_year"
        )
    ]
    
    # 創建查詢表單模板 - 第一個按鈕組
    query_template1 = TemplateMessage(
        alt_text="活動查詢",
        template=ButtonsTemplate(
            title="📆 活動查詢 (1/2)",
            text="請選擇查詢方式",
            actions=[date_picker, date_range_picker, quick_queries[0]]
        )
    )
    
    # 創建查詢表單模板 - 第二個按鈕組
    query_template2 = TemplateMessage(
        alt_text="活動查詢",
        template=ButtonsTemplate(
            title="📆 活動查詢 (2/2)",
            text="請選擇查詢範圍",
            actions=[quick_queries[1], quick_queries[2], quick_queries[3]]
        )
    )
    
    # 發送兩個消息以提供更多按鈕
    line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[query_template1, query_template2]
        )
    )

# 新增：發送開始日期選擇器
def send_start_date_picker(reply_token):
    # 創建開始日期選擇器
    start_date_picker = DatetimePickerAction(
        label="選擇開始日期",
        data="action=select_start_date",
        mode="date"
    )
    
    # 創建日期選擇器模板
    template = TemplateMessage(
        alt_text="選擇開始日期",
        template=ButtonsTemplate(
            title="📆 選擇日期範圍",
            text="請先選擇開始日期",
            actions=[start_date_picker]
        )
    )
    
    line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[template]
        )
    )

# 新增：發送結束日期選擇器
def send_end_date_picker(reply_token, start_date):
    # 創建結束日期選擇器
    end_date_picker = DatetimePickerAction(
        label="選擇結束日期",
        data="action=select_end_date",
        mode="date"
    )
    
    # 創建日期選擇器模板
    template = TemplateMessage(
        alt_text="選擇結束日期",
        template=ButtonsTemplate(
            title="📆 選擇日期範圍",
            text=f"開始日期: {start_date}\n請選擇結束日期",
            actions=[end_date_picker]
        )
    )
    
    line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[template]
        )
    )

# 新增：發送帶有快速回覆按鈕的消息
def send_message_with_quick_reply(reply_token, text):
    # 創建快速回覆按鈕
    quick_reply = QuickReply(
        items=[
            QuickReplyItem(
                action=MessageAction(
                    label="設定活動",
                    text="設定活動"
                )
            ),
            QuickReplyItem(
                action=MessageAction(
                    label="查詢活動",
                    text="查詢活動"
                )
            ),
            QuickReplyItem(
                action=MessageAction(
                    label="手動提醒",
                    text="手動提醒"
                )
            ),
            # QuickReplyItem(
            #     action=MessageAction(
            #         label="幫助",
            #         text="幫助"
            #     )
            # )
        ]
    )
    
    # 發送帶有快速回覆按鈕的消息
    message = TextMessage(
        text=text,
        quick_reply=quick_reply
    )
    
    line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[message]
        )
    )

# 修改：更新幫助消息以包含新的互動元素說明
def send_help_message(reply_token):
    help_text = """
📅 活動管理 Bot 使用說明 📅

🔸 互動方式:
   - 「設定活動」將引導您完成活動設定的步驟
   - 「查詢活動」提供多種方式查詢活動

🔸 指令方式:
1️⃣ 設定活動:
   格式: 設定活動:[活動名稱],[時間],[分類],[重要性],[備註]
   範例: 設定活動:團隊會議,2025/01/25 14:00,會議,高,討論年度計劃

2️⃣ 查詢活動:
   格式: 查詢活動:[開始日期],[結束日期]
   範例: 查詢活動:2025/01/01,2025/12/31
   
   也可以只指定一天:
   範例: 查詢活動:2025/12/25

3️⃣ 手動提醒:
   直接發送「手動提醒」，Bot 將立即檢查並發送未來三天內的活動提醒

🔔 自動提醒功能會在每天早上 9 點自動檢查未來三天內的活動並發送提醒。
    """
    
    # 創建帶快速回覆按鈕的幫助消息
    quick_reply = QuickReply(
        items=[
            QuickReplyItem(
                action=MessageAction(
                    label="設定活動",
                    text="設定活動"
                )
            ),
            QuickReplyItem(
                action=MessageAction(
                    label="查詢活動",
                    text="查詢活動"
                )
            ),
            QuickReplyItem(
                action=MessageAction(
                    label="手動提醒",
                    text="手動提醒"
                )
            )
        ]
    )
    
    help_message = TextMessage(
        text=help_text,
        quick_reply=quick_reply
    )
    
    line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[help_message]
        )
    )

def handle_add_event(user_text, reply_token, user_id):
    """處理添加活動的命令"""
    try:
        # 檢查格式: 新增活動 活動名稱 YYYY/MM/DD HH:MM [分類] [重要性] [備註]
        pattern = r'^新增(?:活動)?\s+(.+?)\s+(\d{4}/\d{1,2}/\d{1,2}(?:\s+\d{1,2}:\d{1,2})?)\s*(?:\[([^\]]+)\])?\s*(?:\[([^\]]+)\])?\s*(?:\[([^\]]*)\])?$'
        match = re.match(pattern, user_text, re.DOTALL)
        
        if match:
            event_name = match.group(1).strip()
            date_str = match.group(2).strip()
            
            # 解析日期時間
            if ' ' in date_str and ':' in date_str.split(' ')[1]:
                event_time = datetime.strptime(date_str, "%Y/%m/%d %H:%M")
            else:
                event_time = datetime.strptime(date_str, "%Y/%m/%d").replace(hour=9, minute=0)  # 預設為上午9點
            
            # 確保event_time有時區信息
            event_time = event_time.replace(tzinfo=timezone.utc)
            
            # 解析可選參數
            category = match.group(3).strip() if match.group(3) else "活動"
            importance = match.group(4).strip() if match.group(4) else "中"
            notes = match.group(5).strip() if match.group(5) else ""
            
            # 驗證重要性
            valid_importance = ["高", "中", "低"]
            if importance not in valid_importance:
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=reply_token,
                        messages=[TextMessage(text=f"無效的重要性: {importance}。請使用「高」、「中」或「低」。")]
                    )
                )
                return
            
            # 添加到 Notion
            response = notion_manager.add_event(
                event_name=event_name,
                event_time=event_time,
                category=category,
                importance=importance,
                notes=notes
            )
            
            if response:
                # 創建成功消息
                success_message = f"✅ 活動已設定成功！\n\n活動名稱: {event_name}\n時間: {date_str}\n分類: {category}\n重要性: {importance}"
                if notes:
                    success_message += f"\n備註: {notes}"
                
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=reply_token,
                        messages=[TextMessage(text=success_message)]
                    )
                )
            else:
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=reply_token,
                        messages=[TextMessage(text="活動設定失敗，請稍後再試")]
                    )
                )
        else:
            # 格式不正確，顯示幫助
            help_message = "請使用以下格式新增活動：\n\n新增活動 活動名稱 YYYY/MM/DD HH:MM [分類] [重要性] [備註]\n\n例如：\n新增活動 開會 2023/01/01 14:30 [工作] [高] [準備簡報]"
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=help_message)]
                )
            )
    except Exception as e:
        print(f"處理添加活動時出錯: {e}")
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text="處理請求時發生錯誤，請稍後再試")]
            )
        )

def handle_query_events(user_text, reply_token, user_id):
    """處理查詢活動的指令"""
    try:
        # 判斷是否為postback操作
        if isinstance(user_text, str) and user_text.startswith("action="):
            # 處理查詢表單的開啟
            if user_text == "action=open_query_form":
                send_query_form_with_quick_reply(reply_token)
                return
            # 處理日期範圍選擇
            elif user_text == "action=select_date_range":
                send_start_date_picker(reply_token)
                return
            # 處理今天查詢
            elif user_text == "action=query_today":
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
                end_date = today.replace(hour=23, minute=59, second=59)
                events = notion_manager.query_events(today, end_date)
                send_query_results(reply_token, today, end_date, events)
                return
            # 處理未來7天查詢
            elif user_text == "action=query_next7days":
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
                end_date = (today + timedelta(days=7)).replace(hour=23, minute=59, second=59)
                events = notion_manager.query_events(today, end_date)
                send_query_results(reply_token, today, end_date, events)
                return
            # 處理本月查詢
            elif user_text == "action=query_month":
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0, day=1, tzinfo=timezone.utc)
                if today.month == 12:
                    end_date = datetime(today.year + 1, 1, 1, 23, 59, 59, tzinfo=timezone.utc) - timedelta(days=1)
                else:
                    end_date = datetime(today.year, today.month + 1, 1, 23, 59, 59, tzinfo=timezone.utc) - timedelta(days=1)
                events = notion_manager.query_events(today, end_date)
                send_query_results(reply_token, today, end_date, events)
                return
            # 處理本年查詢
            elif user_text == "action=query_year":
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0, day=1, month=1, tzinfo=timezone.utc)
                end_date = datetime(today.year + 1, 1, 1, 0, 0, 0, tzinfo=timezone.utc) - timedelta(seconds=1)
                events = notion_manager.query_events(today, end_date)
                send_query_results(reply_token, today, end_date, events)
                return
            # 其他未知操作
            else:
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=reply_token,
                        messages=[TextMessage(text="未知的查詢操作")]
                    )
                )
                return
        
        # 處理標準查詢格式："查詢活動:2023/12/01,2023/12/31"
        # 解析輸入
        # 格式: 查詢活動:[開始日期],[結束日期]
        # 範例: 查詢活動:2023/12/01,2023/12/31
        params = user_text[5:].split(',')
        
        if not params[0]:
            raise ValueError("請提供開始日期")
        
        # 解析開始日期
        try:
            start_date = datetime.strptime(params[0].strip(), "%Y/%m/%d")
            # 添加時區信息
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
        except ValueError:
            raise ValueError("開始日期格式不正確，請使用 YYYY/MM/DD 格式")
        
        # 解析結束日期（如果提供）
        end_date = None
        if len(params) > 1 and params[1].strip():
            try:
                end_date = datetime.strptime(params[1].strip(), "%Y/%m/%d")
                # 添加時區信息
                end_date = end_date.replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
            except ValueError:
                raise ValueError("結束日期格式不正確，請使用 YYYY/MM/DD 格式")
        
        # 如果沒有提供結束日期，預設查詢單日
        if not end_date:
            end_date = start_date.replace(hour=23, minute=59, second=59)
        
        # 查詢 Notion
        events = notion_manager.query_events(start_date, end_date)
        send_query_results(reply_token, start_date, end_date, events)
        
    except ValueError as e:
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=f"❌ 查詢活動錯誤: {str(e)}\n\n正確格式: 查詢活動:[開始日期],[結束日期]\n範例: 查詢活動:2023/12/01,2023/12/31")]
            )
        )
    except Exception as e:
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=f"❌ 發生錯誤: {str(e)}")]
            )
        )

# 新增：使用QuickReply發送查詢活動表單
def send_query_form_with_quick_reply(reply_token):
    """使用QuickReply發送查詢活動表單"""
    
    # 創建查詢選項的QuickReply
    quick_reply_items = [
        QuickReplyItem(
            action=DatetimePickerAction(
                label="選擇單日日期",
                data="action=query_date",
                mode="date"
            )
        ),
        QuickReplyItem(
            action=PostbackAction(
                label="選擇範圍日期",
                data="action=select_date_range"
            )
        ),
        QuickReplyItem(
            action=PostbackAction(
                label="查詢今天",
                data="action=query_today"
            )
        ),
        QuickReplyItem(
            action=PostbackAction(
                label="查詢後7天",
                data="action=query_next7days"
            )
        ),
        QuickReplyItem(
            action=PostbackAction(
                label="查詢本月",
                data="action=query_month"
            )
        ),
        QuickReplyItem(
            action=PostbackAction(
                label="查詢本年",
                data="action=query_year"
            )
        )
    ]
    
    # 創建含有QuickReply的文字訊息
    query_message = TextMessage(
        text="📅 活動查詢\n請選擇查詢方式，或直接輸入格式如：\n查詢活動:2023/12/01,2023/12/31",
        quick_reply=QuickReply(items=quick_reply_items)
    )
    
    line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[query_message]
        )
    )

# 新增：發送查詢結果的通用函數
def send_query_results(reply_token, start_date, end_date, events):
    """發送查詢結果的通用函數"""
    if events:
        # 創建回覆消息
        message = f"📅 {start_date.strftime('%Y/%m/%d')} "
        if end_date.date() != start_date.date():
            message += f"到 {end_date.strftime('%Y/%m/%d')} "
        message += f"的活動（共 {len(events)} 項）：\n\n"
        
        for event_item in events:
            event_time = datetime.fromisoformat(event_item["time"].replace("Z", "+00:00"))
            formatted_time = event_time.strftime("%Y/%m/%d %H:%M")
            
            # 簡潔格式
            message += f"{event_item['name']}     {formatted_time} ({event_item['importance']})\n"
            message += f"[{event_item['category']}]"
            
            if event_item["notes"]:
                message += f" {event_item['notes']}"
            
            message += "\n\n"
        
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=message)]
            )
        )
    else:
        message = f"📅 {start_date.strftime('%Y/%m/%d')} "
        if end_date.date() != start_date.date():
            message += f"到 {end_date.strftime('%Y/%m/%d')} "
        message += "沒有找到任何活動"
        
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=message)]
            )
        )

# 新增：發送活動設定Flex表單
def send_event_creation_flex(reply_token, user_id=None):
    # 創建Flex表單的內容
    flex_content = {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "📅 活動設定",
                    "size": "xl",
                    "weight": "bold",
                    "color": "#1DB446"
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "box",
                    "layout": "vertical",
                    "margin": "lg",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "日期時間",
                                    "size": "sm",
                                    "color": "#555555",
                                    "flex": 0
                                }
                            ]
                        },
                        {
                            "type": "text",
                            "text": "點擊選擇",
                            "size": "sm",
                            "color": "#111111",
                            "margin": "md",
                            "action": {
                                "type": "datetimepicker",
                                "label": "選擇日期時間",
                                "data": "action=select_datetime_flex",
                                "mode": "datetime",
                                "initial": datetime.now().strftime("%Y-%m-%dT%H:%M"),
                                "max": (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M"),
                                "min": datetime.now().strftime("%Y-%m-%dT%H:%M")
                            }
                        },
                        {
                            "type": "separator",
                            "margin": "lg"
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "margin": "lg",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "重要性",
                                    "size": "sm",
                                    "color": "#555555",
                                    "flex": 0
                                }
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "margin": "md",
                            "contents": [
                                {
                                    "type": "button",
                                    "style": "primary",
                                    "color": "#FF5551",
                                    "action": {
                                        "type": "postback",
                                        "label": "高",
                                        "data": "action=select_importance_flex&value=高"
                                    },
                                    "height": "sm"
                                },
                                {
                                    "type": "button",
                                    "style": "primary",
                                    "color": "#FFA500",
                                    "action": {
                                        "type": "postback",
                                        "label": "中",
                                        "data": "action=select_importance_flex&value=中"
                                    },
                                    "margin": "md",
                                    "height": "sm"
                                },
                                {
                                    "type": "button",
                                    "style": "primary",
                                    "color": "#00CC00",
                                    "action": {
                                        "type": "postback",
                                        "label": "低",
                                        "data": "action=select_importance_flex&value=低"
                                    },
                                    "margin": "md",
                                    "height": "sm"
                                }
                            ]
                        },
                        {
                            "type": "separator",
                            "margin": "lg"
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "margin": "lg",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "分類",
                                    "size": "sm",
                                    "color": "#555555",
                                    "flex": 0
                                }
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "margin": "md",
                            "contents": [
                                {
                                    "type": "button",
                                    "style": "secondary",
                                    "action": {
                                        "type": "postback",
                                        "label": "會議",
                                        "data": "action=select_category_flex&value=會議"
                                    },
                                    "height": "sm"
                                },
                                {
                                    "type": "button",
                                    "style": "secondary",
                                    "action": {
                                        "type": "postback",
                                        "label": "活動",
                                        "data": "action=select_category_flex&value=活動"
                                    },
                                    "margin": "md",
                                    "height": "sm"
                                }
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "margin": "md",
                            "contents": [
                                {
                                    "type": "button",
                                    "style": "secondary",
                                    "action": {
                                        "type": "postback",
                                        "label": "提醒",
                                        "data": "action=select_category_flex&value=提醒"
                                    },
                                    "height": "sm"
                                },
                                {
                                    "type": "button",
                                    "style": "secondary",
                                    "action": {
                                        "type": "postback",
                                        "label": "任務",
                                        "data": "action=select_category_flex&value=任務"
                                    },
                                    "margin": "md",
                                    "height": "sm"
                                }
                            ]
                        }
                        # 此處已移除活動名稱和備註輸入區塊
                    ]
                }
            ]
        }
    }
    
    # 移除對非存在欄位的操作
    
    # 移除原來的送出按鈕
    if "footer" in flex_content:
        del flex_content["footer"]
    
    flex_message = FlexMessage(
        alt_text="活動設定表單",
        contents=FlexContainer.from_dict(flex_content)
    )
    
    # 初始化用戶的Flex表單狀態，設置默認值
    if user_id:
        if user_id not in user_states:
            user_states[user_id] = {}
            
        # 初始化flex_form狀態
        user_states[user_id]['flex_form'] = {
            'datetime': datetime.now().strftime("%Y/%m/%d %H:%M"),  # 默認為當前時間
            'importance': '中',  # 默認為中等重要性
            'category': '活動'  # 默認分類
        }
        print(f"已初始化用戶Flex表單狀態，設置默認時間為{user_states[user_id]['flex_form']['datetime']}，重要性為{user_states[user_id]['flex_form']['importance']}")
    
    line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[flex_message]
        )
    )

# 新增：處理LIFF輸入活動名稱
def handle_liff_name_input(name, reply_token, user_id):
    try:
        # 將活動名稱存儲在用戶的會話狀態中
        if user_id not in user_event_creation:
            user_event_creation[user_id] = {'flex_form': {}}
        elif 'flex_form' not in user_event_creation[user_id]:
            user_event_creation[user_id]['flex_form'] = {}
            
        user_event_creation[user_id]['flex_form']['name'] = name
        
        # 發送確認消息
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=f"已設定活動名稱: {name}")]
            )
        )
    except Exception as e:
        print(f"處理LIFF活動名稱輸入時出錯: {e}")
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=f"設定活動名稱失敗: {str(e)}")]
            )
        )

# 新增：處理LIFF輸入備註
def handle_liff_notes_input(notes, reply_token, user_id):
    try:
        # 將備註存儲在用戶的會話狀態中
        if user_id not in user_event_creation:
            user_event_creation[user_id] = {'flex_form': {}}
        elif 'flex_form' not in user_event_creation[user_id]:
            user_event_creation[user_id]['flex_form'] = {}
            
        user_event_creation[user_id]['flex_form']['notes'] = notes
        
        # 發送確認消息
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=f"已設定活動備註: {notes}")]
            )
        )
    except Exception as e:
        print(f"處理LIFF備註輸入時出錯: {e}")
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=f"設定活動備註失敗: {str(e)}")]
            )
        )

# 添加共用函數
def send_confirmation_message(reply_token, confirm_message, is_flex=False):
    """
    發送活動確認訊息，使用QuickReply而不是ConfirmTemplate
    
    參數:
        reply_token (str): 回覆用的token
        confirm_message (str): 確認訊息文本
        is_flex (bool): 是否為Flex表單提交，決定使用的action名稱
    """
    # 創建確認選項的QuickReply
    quick_reply_items = [
        QuickReplyItem(
            action=PostbackAction(
                label="取消",
                data=f"action=cancel_event{'_flex' if is_flex else ''}"
            )
        ),
        QuickReplyItem(
            action=PostbackAction(
                label="確認",
                data=f"action=confirm_event{'_flex' if is_flex else ''}"
            )
        )
    ]
    
    # 創建含有QuickReply的確認訊息
    message = TextMessage(
        text=confirm_message,
        quick_reply=QuickReply(items=quick_reply_items)
    )
    
    # 發送訊息
    line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[message]
        )
    )

# 提取共用函數 - 處理事件確認邏輯
def handle_event_confirmation(reply_token, user_id, is_flex=False):
    """處理活動確認邏輯的共用函數"""
    # 確定使用哪個狀態存儲
    state_key = 'flex_form' if is_flex else 'event_creation'
    
    # 檢查用戶狀態
    if user_id in user_states and state_key in user_states[user_id]:
        # 獲取之前收集的所有信息
        event_data = user_states[user_id][state_key]
        
        # 設置默認值
        if 'datetime' not in event_data or not event_data['datetime']:
            # 使用當前時間作為默認值
            current_time = datetime.now()
            event_data['datetime'] = current_time.strftime("%Y/%m/%d %H:%M")
            print(f"設置默認時間: {event_data['datetime']}")
            
        if 'importance' not in event_data or not event_data['importance']:
            # 設置默認重要性為中
            event_data['importance'] = "中"
            print(f"設置默認重要性: {event_data['importance']}")
        
        try:
            # 解析日期時間
            event_time = datetime.strptime(event_data['datetime'], "%Y/%m/%d %H:%M")
            
            # 確保event_time有時區信息
            event_time = event_time.replace(tzinfo=timezone.utc)
            
            # 添加到 Notion
            response = notion_manager.add_event(
                event_name=event_data['name'],
                event_time=event_time,
                category=event_data['category'],
                importance=event_data['importance'],
                notes=event_data.get('notes', '')
            )
            
            if response:
                # 創建成功消息
                success_message = f"✅ 活動已設定成功！\n\n活動名稱: {event_data['name']}\n時間: {event_data['datetime']}\n分類: {event_data['category']}\n重要性: {event_data['importance']}"
                if 'notes' in event_data and event_data['notes']:
                    success_message += f"\n備註: {event_data['notes']}"
                
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=reply_token,
                        messages=[TextMessage(text=success_message)]
                    )
                )
            else:
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=reply_token,
                        messages=[TextMessage(text="活動設定失敗，請稍後再試")]
                    )
                )
        except Exception as e:
            print(f"處理活動確認時出錯: {e}")
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=f"設定活動失敗: {str(e)}")]
                )
            )
        finally:
            # 清理用戶狀態
            if state_key in user_states[user_id]:
                del user_states[user_id][state_key]
    else:
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text="無法確認活動，請重新設定")]
            )
        )

# 提取共用函數 - 處理事件取消邏輯
def handle_event_cancellation(reply_token, user_id, is_flex=False):
    """處理活動取消邏輯的共用函數"""
    # 確定使用哪個狀態存儲
    state_key = 'flex_form' if is_flex else 'event_creation'
    
    # 清理用戶狀態
    if user_id in user_states and state_key in user_states[user_id]:
        del user_states[user_id][state_key]
    
    # 發送取消確認
    line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[TextMessage(text="已取消活動設定")]
        )
    )

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
