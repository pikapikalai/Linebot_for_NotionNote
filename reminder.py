import os
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from notion_manager import NotionManager
from linebot.v3.messaging import MessagingApi, ApiClient, Configuration, TextMessage, PushMessageRequest
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

class EventReminder:
    def __init__(self):
        self.notion_manager = NotionManager()
        configuration = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
        api_client = ApiClient(configuration)
        self.line_bot_api = MessagingApi(api_client)
        self.scheduler = BackgroundScheduler()
    
    def start(self):
        """啟動排程器"""
        # 將提醒時間從早上9點改為早上6點
        self.scheduler.add_job(
            self.check_and_remind,
            CronTrigger(hour=6, minute=0),
            id='daily_reminder'
        )
        
        # 啟動排程器
        self.scheduler.start()
        print("提醒排程器已啟動 - 設定為每天早上6點執行")
    
    def stop(self):
        """停止排程器"""
        self.scheduler.shutdown()
        print("提醒排程器已停止")
    
    def check_and_remind(self):
        """檢查即將到來的活動並根據重要性發送提醒"""
        try:
            # 使用帶時區的日期時間，解決時區問題
            today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            
            # 獲取未來7天內的所有活動（為了高重要性的每天提醒）
            all_events = self.notion_manager.query_events(today, today + timedelta(days=7))
            
            if not all_events:
                print("未找到需要提醒的活動")
                return
            
            # 篩選不同重要性的活動
            events_to_remind = []
            
            for event in all_events:
                # 確保使用相同時區格式的日期時間進行比較
                event_time = datetime.fromisoformat(event["time"].replace("Z", "+00:00"))
                event_date = event_time.replace(hour=0, minute=0, second=0, microsecond=0)
                
                # 計算日期差異時確保兩個日期時間都帶有時區信息
                days_until_event = (event_date - today).days
                importance = event["importance"]
                
                # 高重要性：每天提醒
                if importance == "高":
                    # 活動日期在未來7天內都要提醒
                    if 0 <= days_until_event <= 7:
                        events_to_remind.append(event)
                
                # 中重要性：當天和3天前提醒
                elif importance == "中":
                    # 當天或剛好3天前
                    if days_until_event == 0 or days_until_event == 3:
                        events_to_remind.append(event)
                
                # 低重要性：僅當天提醒
                elif importance == "低":
                    # 僅當天
                    if days_until_event == 0:
                        events_to_remind.append(event)
            
            if not events_to_remind:
                print("今天沒有需要提醒的活動")
                return
            
            print(f"根據重要性篩選後，找到 {len(events_to_remind)} 個需要提醒的活動")
            
            # 向所有需要提醒的用戶發送消息
            for user_id in self.get_reminder_recipients():
                self.send_reminders(user_id, events_to_remind)
            
            # 僅更新當天活動的提醒狀態為"已提醒"
            for event in events_to_remind:
                event_time = datetime.fromisoformat(event["time"].replace("Z", "+00:00"))
                event_date = event_time.replace(hour=0, minute=0, second=0, microsecond=0)
                
                # 只有當天的活動才標記為已提醒，因為高重要性的活動需要每天提醒
                if (event_date - today).days == 0:
                    self.notion_manager.update_reminder_status(event["id"], "已提醒")
        
        except Exception as e:
            print(f"提醒過程中出錯: {e}")
    
    def send_reminders(self, user_id, events):
        """向指定用戶發送活動提醒"""
        try:
            # 創建提醒消息
            message = "📅 活動提醒：\n\n"
            
            # 將活動按照日期分組
            events_by_date = {}
            for event in events:
                # 確保使用一致的時區格式
                event_time = datetime.fromisoformat(event["time"].replace("Z", "+00:00"))
                event_date = event_time.strftime("%Y/%m/%d")
                
                if event_date not in events_by_date:
                    events_by_date[event_date] = []
                
                events_by_date[event_date].append(event)
            
            # 按日期順序顯示活動
            for date in sorted(events_by_date.keys()):
                message += f"📆 {date}:\n"
                
                for event in events_by_date[date]:
                    # 確保使用一致的時區格式
                    event_time = datetime.fromisoformat(event["time"].replace("Z", "+00:00"))
                    formatted_time = event_time.strftime("%H:%M")
                    
                    message += f"- {event['name']} ({formatted_time})\n"
                    message += f"  [{event['category']}] "
                    
                    # 顯示重要性
                    if event["importance"] == "高":
                        message += "🔴 高重要性"
                    elif event["importance"] == "中":
                        message += "🟡 中重要性"
                    else:
                        message += "🟢 低重要性"
                    
                    message += "\n"
                    
                    if event["notes"]:
                        message += f"  備註：{event['notes']}\n"
                    
                    message += "\n"
            
            # 發送消息
            push_message_request = PushMessageRequest(
                to=user_id,
                messages=[TextMessage(text=message)]
            )
            self.line_bot_api.push_message(push_message_request)
            
            print(f"已向用戶 {user_id} 發送提醒")
        
        except Exception as e:
            print(f"發送提醒時出錯: {e}")
    
    def get_reminder_recipients(self):
        """獲取需要接收提醒的用戶 ID 列表"""
        # 這裡可以從配置文件或資料庫中獲取用戶 ID
        # 暫時返回一個硬編碼的列表，您需要根據實際情況修改
        admin_id = os.getenv("ADMIN_USER_ID", "")
        if admin_id == "您的_LINE_用戶_ID" or not admin_id:
            print("警告：ADMIN_USER_ID 未設置，提醒將不會發送")
            return []
        return [admin_id]
    
    def manual_remind(self, user_id):
        """手動觸發提醒"""
        try:
            # 手動提醒模式下，直接使用重要性邏輯進行提醒
            self.check_and_remind()
            return "已手動觸發活動提醒，根據重要性發送了不同時間的提醒"
        except Exception as e:
            print(f"手動提醒時出錯: {e}")
            return "提醒發送過程中出錯，請稍後再試" 