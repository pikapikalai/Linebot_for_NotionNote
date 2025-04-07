import os
from datetime import datetime, timedelta, timezone
from notion_client import Client
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

class NotionManager:
    def __init__(self):
        self.notion = Client(auth=os.getenv("NOTION_TOKEN"))
        self.database_id = os.getenv("NOTION_DATABASE_ID")
    
    def add_event(self, event_name, event_time, category, importance="中", notes=""):
        """
        將新活動添加到 Notion 資料庫
        
        參數:
        event_name (str): 活動名稱
        event_time (datetime): 活動時間
        category (str): 活動分類
        importance (str): 重要性 (高/中/低)
        notes (str): 備註
        
        返回:
        dict: 新建活動的資料
        """
        try:
            # 確保日期時間有時區信息
            if event_time.tzinfo is None:
                event_time = event_time.replace(tzinfo=timezone.utc)
                
            # 格式化日期時間為 ISO 8601 格式
            formatted_time = event_time.isoformat()
            
            # 創建新的資料庫項目
            response = self.notion.pages.create(
                parent={"database_id": self.database_id},
                properties={
                    "活動名稱": {
                        "title": [
                            {
                                "text": {
                                    "content": event_name
                                }
                            }
                        ]
                    },
                    "日期時間": {
                        "date": {
                            "start": formatted_time
                        }
                    },
                    "分類": {
                        "select": {
                            "name": category
                        }
                    },
                    "重要性": {
                        "select": {
                            "name": importance
                        }
                    },
                    "備註": {
                        "rich_text": [
                            {
                                "text": {
                                    "content": notes
                                }
                            }
                        ]
                    },
                    "提醒狀態": {
                        "select": {
                            "name": "未提醒"
                        }
                    }
                }
            )
            return response
        except Exception as e:
            print(f"添加活動時出錯: {e}")
            return None
    
    def query_events(self, start_date, end_date=None, reminder_status=None):
        """
        查詢指定時間範圍內的活動
        
        參數:
        start_date (datetime): 開始日期
        end_date (datetime, optional): 結束日期，如果未提供則使用開始日期
        reminder_status (str, optional): 提醒狀態過濾 ("已提醒"/"未提醒")
        
        返回:
        list: 活動列表
        """
        try:
            # 如果未提供結束日期，則使用開始日期
            if end_date is None:
                end_date = start_date
            
            # 確保日期時間有時區信息
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
                
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)
            
            # 格式化日期為 ISO 8601 格式
            start_formatted = start_date.isoformat()
            end_formatted = end_date.isoformat()
            
            # 準備過濾條件
            filter_conditions = [
                {
                    "property": "日期時間",
                    "date": {
                        "on_or_after": start_formatted
                    }
                },
                {
                    "property": "日期時間",
                    "date": {
                        "on_or_before": end_formatted
                    }
                }
            ]
            
            # 如果指定了提醒狀態，則添加相應的過濾條件
            if reminder_status:
                filter_conditions.append({
                    "property": "提醒狀態",
                    "select": {
                        "equals": reminder_status
                    }
                })
            
            # 查詢資料庫
            response = self.notion.databases.query(
                database_id=self.database_id,
                filter={
                    "and": filter_conditions
                },
                sorts=[
                    {
                        "property": "日期時間",
                        "direction": "ascending"
                    }
                ]
            )
            
            # 處理結果
            events = []
            for page in response["results"]:
                properties = page["properties"]
                event = {
                    "id": page["id"],
                    "name": self._get_title_property(properties["活動名稱"]),
                    "time": self._get_date_property(properties["日期時間"]),
                    "category": self._get_select_property(properties["分類"]),
                    "importance": self._get_select_property(properties["重要性"]),
                    "notes": self._get_text_property(properties["備註"]),
                    "reminder_status": self._get_select_property(properties["提醒狀態"])
                }
                events.append(event)
            
            return events
        
        except Exception as e:
            print(f"查詢活動時出錯: {e}")
            return []
    
    def get_upcoming_events(self, days=3):
        """
        獲取即將到來的活動（未來幾天內）
        
        參數:
        days (int): 未來幾天
        
        返回:
        list: 活動列表
        """
        try:
            # 使用帶時區的日期時間
            today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = today + timedelta(days=days)
            
            # 查詢資料庫
            response = self.notion.databases.query(
                database_id=self.database_id,
                filter={
                    "and": [
                        {
                            "property": "日期時間",
                            "date": {
                                "on_or_after": today.isoformat()
                            }
                        },
                        {
                            "property": "日期時間",
                            "date": {
                                "on_or_before": end_date.isoformat()
                            }
                        },
                        {
                            "property": "提醒狀態",
                            "select": {
                                "equals": "未提醒"
                            }
                        }
                    ]
                }
            )
            
            # 處理結果
            events = []
            for page in response["results"]:
                properties = page["properties"]
                event = {
                    "id": page["id"],
                    "name": self._get_title_property(properties["活動名稱"]),
                    "time": self._get_date_property(properties["日期時間"]),
                    "category": self._get_select_property(properties["分類"]),
                    "importance": self._get_select_property(properties["重要性"]),
                    "notes": self._get_text_property(properties["備註"])
                }
                events.append(event)
            
            return events
        
        except Exception as e:
            print(f"獲取即將到來的活動時出錯: {e}")
            return []
    
    def update_reminder_status(self, page_id, status="已提醒"):
        """
        更新活動的提醒狀態
        
        參數:
        page_id (str): 頁面 ID
        status (str): 新的提醒狀態
        
        返回:
        dict: 更新後的頁面資料
        """
        try:
            response = self.notion.pages.update(
                page_id=page_id,
                properties={
                    "提醒狀態": {
                        "select": {
                            "name": status
                        }
                    }
                }
            )
            return response
        except Exception as e:
            print(f"更新提醒狀態時出錯: {e}")
            return None
    
    # 輔助方法，用於從屬性中提取值
    def _get_title_property(self, property_value):
        """從標題屬性中提取值"""
        if property_value["title"]:
            return property_value["title"][0]["text"]["content"]
        return ""
    
    def _get_date_property(self, property_value):
        """從日期屬性中提取值"""
        if property_value["date"]:
            return property_value["date"]["start"]
        return None
    
    def _get_select_property(self, property_value):
        """從選擇屬性中提取值"""
        if property_value["select"]:
            return property_value["select"]["name"]
        return ""
    
    def _get_text_property(self, property_value):
        """從文本屬性中提取值"""
        if property_value["rich_text"]:
            return property_value["rich_text"][0]["text"]["content"]
        return "" 