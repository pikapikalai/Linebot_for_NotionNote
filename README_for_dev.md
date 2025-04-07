# LINE Bot 活動管理系統 - 開發者文檔

這是一個將 LINE Bot 與 Notion 整合的活動管理系統，用於管理重要活動並提供自動提醒功能。本文檔針對系統部署和設置提供指南。

## 系統架構

- **Flask 伺服器**: 處理 LINE Webhook 事件
- **LINE Messaging API**: 與使用者互動的介面
- **Notion API**: 後端資料庫，用於存儲活動資訊
- **定時任務**: 實現自動提醒功能

## 技術棧

- **Python 3.8+**
- **Flask**: Web 框架
- **line-bot-sdk-python v3.16.2+**: LINE Bot SDK
- **Notion Python SDK**: 連接 Notion 資料庫
- **APScheduler**: 實現定時任務
- **Python-dateutil**: 處理日期時間
- **Pytz**: 時區管理
- **Python-dotenv**: 環境變數管理

## 環境變數設置

在專案根目錄創建 `.env` 文件，填入以下資訊：

```
LINE_CHANNEL_SECRET=your_line_channel_secret
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
NOTION_TOKEN=your_notion_integration_token
NOTION_DATABASE_ID=your_notion_database_id
```

## 部署流程

### 本地開發環境
1. 克隆專案：`git clone <repository_url>`
2. 安裝依賴：`pip install -r requirements.txt`
3. 創建並配置 `.env` 文件
4. 運行應用：`python main.py`
5. (選擇性) 初始化Rich Menu：訪問 `http://localhost:5000/init_rich_menu`

### 生產環境部署
1. 在服務器上設置 Python 環境
2. 創建並配置 `.env` 文件
3. 設置 HTTPS 服務（可使用 Nginx + Let's Encrypt）
4. 設置自動啟動腳本：
   ```bash
   # /etc/systemd/system/linebot.service
   [Unit]
   Description=LINE Bot Activity Manager
   After=network.target

   [Service]
   User=your_user
   WorkingDirectory=/path/to/project
   ExecStart=/path/to/python /path/to/project/main.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
5. 啟動服務：`systemctl start linebot`
6. 設置開機啟動：`systemctl enable linebot`
7. 初始化Rich Menu：訪問 `https://your_domain/init_rich_menu`

## Notion 資料庫設置

1. 在 Notion 中創建新資料庫
2. 添加以下屬性：
   - Name（標題）: 活動名稱
   - Time（日期）: 活動時間
   - Category（選項）: 活動分類（會議、活動、提醒、任務）
   - Importance（選項）: 重要性（高、中、低）
   - Notes（文本）: 備註
   - Reminded（複選框）: 是否已提醒
3. 創建 Notion Integration 並獲取 Token
4. 共享資料庫給 Integration

## LINE Bot 設置

1. 在 [LINE Developers](https://developers.line.biz/) 創建新的提供者和頻道
2. 設置 Webhook URL: `https://your_domain/callback`
3. 開啟傳訊 API
4. 獲取頻道密鑰和訪問令牌
5. 設置Rich Menu（系統會自動創建，或可透過 `/init_rich_menu` 端點初始化）

## 代碼結構

- `main.py`: 主程序，包含 Flask 伺服器和 LINE Bot 處理邏輯
- `notion_manager.py`: Notion API 整合，處理資料庫操作
- `reminder.py`: 提醒系統，包含自動提醒功能
- `rich_menu.png`: Rich Menu 圖片
- `requirements.txt`: 依賴清單

## 功能模組

### 1. 主要模塊 (main.py)
- 處理 LINE Webhook 事件
- 解析使用者指令
- 管理使用者狀態（活動創建流程等）
- 實現Rich Menu功能
- 實現Flex Message表單

### 2. Notion 管理器 (notion_manager.py)
- 連接 Notion API
- 添加、查詢活動
- 更新提醒狀態

### 3. 提醒系統 (reminder.py)
- 定時檢查活動
- 根據重要性設定不同的提醒策略
- 發送提醒消息
- 記錄已提醒狀態

## 用戶狀態管理

系統使用字典來管理用戶狀態，主要結構如下：
```python
user_states = {
    "user_id": {
        "event_creation": {  # 活動創建狀態
            "step": "選擇步驟",  # waiting_for_time/selecting_importance/selecting_category/waiting_for_name/waiting_for_notes/waiting_for_confirmation
            "datetime": "活動時間",
            "importance": "重要性",
            "category": "分類",
            "name": "活動名稱",
            "notes": "備註"
        },
        "flex_form": {  # Flex表單狀態
            "step": "表單步驟",  # waiting_for_flex_name/waiting_for_flex_notes/waiting_for_confirmation
            "datetime": "活動時間",
            "importance": "重要性",
            "category": "分類",
            "name": "活動名稱",
            "notes": "備註"
        },
        "query": {  # 查詢相關狀態
            "start_date": "開始日期",
            "waiting_for_end_date": True/False
        }
    }
}
```

## 擴展指南

### 添加新功能

1. 在 `handle_message` 函數中添加新的指令處理分支
2. 實現相應的處理函數
3. 更新相關文件

### 優化提醒邏輯

系統已根據活動重要性調整提醒頻率和方式：
- 高重要性：每天提醒
- 中重要性：當天和提前3天提醒
- 低重要性：當天提醒

## 主要改進

本系統已實現的主要改進：

1. **用戶界面優化**：
   - 使用Rich Menu提供直觀的操作介面
   - 實現Flex Message表單，提供更好的移動端體驗
   - 使用QuickReply簡化用戶選項輸入

2. **功能增強**：
   - 根據重要性提供差異化提醒
   - 活動查詢支持多種範圍和格式
   - PC端和移動端分別優化的流程

3. **錯誤處理與狀態管理**：
   - 統一用戶狀態管理
   - 改進錯誤處理機制
   - 添加詳細日誌輸出

## 故障排除

### 常見問題

1. Webhook 驗證失敗
   - 檢查 LINE_CHANNEL_SECRET 是否正確
   - 確認 URL 是否可正常訪問

2. 無法連接 Notion
   - 檢查 NOTION_TOKEN 是否有效
   - 確認資料庫權限設置

3. 提醒功能無法正常工作
   - 檢查 APScheduler 配置
   - 確認時區設置是否正確
   - 檢查datetime對象是否都有正確的時區信息

4. Rich Menu 初始化失敗
   - 確認LINE_CHANNEL_ACCESS_TOKEN是否有效
   - 檢查rich_menu.png圖片格式是否符合要求（建議2500x1686像素）

5. 用戶狀態問題
   - 檢查狀態名稱是否一致，例如'waiting_for_notes'與'inputting_notes'
