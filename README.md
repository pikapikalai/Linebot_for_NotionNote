# LINE Bot 活動管理系統

這是一個管理活動和接收提醒的 LINE Bot。您可以使用它來設定活動、查詢活動以及接收即將到來的活動提醒。

## 功能特點

- 多種活動設定方式（互動表單、指令輸入）
- 靈活的活動查詢功能（單日、日期範圍、快捷查詢）
- 智能提醒系統（自動提醒、手動提醒）
- 支援手機和PC端操作
- 與Notion整合，實現跨平台同步

## 安裝與設定

### 方法一：直接安裝

1. 克隆專案：
```bash
git clone https://github.com/your-username/linebot-event-manager.git
cd linebot-event-manager
```

2. 安裝依賴：
```bash
pip install -r requirements.txt
```

3. 設定環境變數：
   - 複製 `.env.example` 為 `.env`
   - 填入您的LINE Bot和Notion相關設定

4. 運行應用：
```bash
python main.py
```

### 方法二：使用Docker

1. 克隆專案：
```bash
git clone https://github.com/your-username/linebot-event-manager.git
cd linebot-event-manager
```

2. 設定環境變數：
   - 複製 `.env.example` 為 `.env`
   - 填入您的LINE Bot和Notion相關設定

3. 使用Docker Compose啟動：
```bash
docker compose up -d
```

4. 查看日誌：
```bash
docker compose logs -f
```

5. 停止服務：
```bash
docker compose down
```

## 環境變數說明

在 `.env` 文件中需要設定以下變數：

- `LINE_CHANNEL_ACCESS_TOKEN`: LINE Bot的Channel Access Token
- `LINE_CHANNEL_SECRET`: LINE Bot的Channel Secret
- `NOTION_TOKEN`: Notion的API Token
- `NOTION_DATABASE_ID`: Notion數據庫ID

## 主要功能

### 1. 設定活動
您可以透過兩種方式設定活動：

**互動方式**：
- **手機版**：點選「設定活動表單」按鈕，使用互動表單：
  1. 選擇日期和時間（可選預設時間或自訂時間）
  2. 選擇活動重要性（高/中/低，預設為中）
  3. 選擇活動分類（會議/活動/提醒/任務，預設為活動）
  4. 輸入活動名稱
  5. 選擇是否輸入備註
  6. 檢查確認資訊並提交

- **PC版**：點選「設定活動」按鈕，系統將引導您完成設定流程：
  1. 選擇日期和時間（可選常用時間或自訂時間）
  2. 選擇活動重要性（高/中/低）
  3. 選擇活動分類（會議/活動/提醒/任務）
  4. 輸入活動名稱
  5. 輸入備註（可輸入「無」、「none」、「n/a」、「n」或直接留空來跳過）
  6. 確認資訊後提交

**指令方式**：
- 直接輸入指令：`設定活動:[活動名稱],[時間],[分類],[重要性],[備註]`
- 範例：`設定活動:團隊會議,2023/12/25 14:00,會議,高,討論年度計劃`

### 2. 查詢活動
您可以透過多種方式查詢活動：

**互動方式**：
- 點選「查詢活動」按鈕，可選擇：
  - 選擇單一日期（日期選擇器）
  - 選擇日期範圍（開始與結束日期）
  - 查詢今天
  - 查詢後7天
  - 查詢本月
  - 查詢本年

**指令方式**：
- 查詢特定日期：`查詢活動:2023/12/25`
- 查詢日期範圍：`查詢活動:2023/12/01,2023/12/31`

### 3. 活動提醒
系統提供兩種提醒方式：

**自動提醒**：
- 系統每天早上6點自動檢查活動並根據重要性發送提醒通知：
  - 高重要性：每天提醒
  - 中重要性：當天和提前3天提醒
  - 低重要性：僅當天提醒

**手動提醒**：
- 點選「手動提醒」按鈕或輸入「手動提醒」文字，立即檢查未來活動

## 活動顯示格式

查詢結果將以以下格式顯示：
```
活動名稱     日期時間 (重要性)
[分類] 備註內容
```

## 使用技巧
- 設定活動時，可使用預設時間選項快速設定常用時間
- 設定活動時，如不需要備註，可輸入「無」或「n」跳過，或選擇「取消備註」選項
- 重要性分為「高」、「中」、「低」三個等級，影響提醒頻率
- 分類可選「會議」、「活動」、「提醒」、「任務」
- 活動時間格式為：YYYY/MM/DD HH:MM

## 幫助
- 輸入「幫助」或點選「幫助」按鈕可查看使用說明

## 開發者文檔

詳細的開發者文檔請參考 [README_for_dev.md](README_for_dev.md)。

## 測試文檔

測試相關說明請參考 [README_for_testing.md](README_for_testing.md)。

## 貢獻指南

1. Fork 專案
2. 創建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 開啟一個 Pull Request

## 授權

本專案採用 MIT 授權條款 - 詳見 [LICENSE](LICENSE) 文件
