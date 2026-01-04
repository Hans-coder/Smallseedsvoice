# Threads API 設置指南

## 概述

要將活動自動發布到Threads，需要申請Meta（Facebook）開發者帳號並獲取API憑證。

## 申請步驟

### 1. 創建Meta開發者帳號

1. 前往 [Meta for Developers](https://developers.facebook.com/)
2. 使用您的Facebook或Instagram帳號登錄
3. 點擊「我的應用程式」→「建立應用程式」

### 2. 創建應用程式

1. 選擇應用程式類型：
   - 選擇「商業」或「其他」
   - 填寫應用程式名稱（例如：台灣音樂活動發布器）
   - 填寫聯絡電子郵件

2. 添加產品：
   - 在應用程式儀表板中，點擊「新增產品」
   - 找到並添加「Threads API」

### 3. 獲取Access Token（在開發者工具中）

#### 方法1：使用Graph API Explorer（推薦，測試用）

**詳細步驟：**

1. **前往 Graph API Explorer**
   - 網址：https://developers.facebook.com/tools/explorer/
   - 或從開發者儀表板：工具 → Graph API Explorer

2. **選擇應用程式**
   - 在右上角的下拉選單中，選擇您剛創建的應用程式

3. **選擇用戶或頁面**
   - 在「使用者或頁面」下拉選單中，選擇您的Threads帳號
   - 如果看不到Threads帳號，請確認：
     - 您已將Threads帳號連接到Facebook/Instagram
     - 應用程式已添加Threads API產品

4. **生成Access Token**
   - 點擊「產生存取權杖」按鈕
   - 會彈出權限選擇視窗

5. **選擇必要權限**
   勾選以下權限：
   - ✅ `threads_basic` - 基本讀取權限
   - ✅ `threads_content_publish` - 發布內容權限
   - （可選）`pages_read_engagement` - 讀取互動數據

6. **複製Token**
   - 點擊「產生存取權杖」後，Token會顯示在「存取權杖」欄位中
   - **立即複製並保存**（這個Token只會顯示一次！）
   - 格式類似：`EAABwzLix...`（很長的字串）

**⚠️ 重要：這個Token是短期Token（1-2小時有效），僅用於測試**

#### 方法2：獲取長期Token（生產環境用）

**步驟1：先獲取短期Token**
- 按照方法1獲取短期Token

**步驟2：轉換為長期Token**
- 使用瀏覽器或curl工具訪問以下URL（替換參數）：
  ```
  https://graph.facebook.com/v18.0/oauth/access_token?
    grant_type=fb_exchange_token&
    client_id={你的App_ID}&
    client_secret={你的App_Secret}&
    fb_exchange_token={短期Token}
  ```

**範例：**
```
https://graph.facebook.com/v18.0/oauth/access_token?grant_type=fb_exchange_token&client_id=123456789&client_secret=abcdef123456&fb_exchange_token=EAABwzLix...
```

**回應格式：**
```json
{
  "access_token": "新的長期Token",
  "token_type": "bearer",
  "expires_in": 5183944
}
```

### 4. 獲取App ID和App Secret（在開發者工具中）

**詳細步驟：**

1. **進入應用程式設定**
   - 在開發者儀表板中，點擊您的應用程式
   - 左側選單：點擊「設定」→「基本」

2. **找到App ID（應用程式編號）**
   - 在「基本」頁面頂部
   - 標籤為「應用程式編號」或「App ID」
   - 格式：一串數字（如：1234567890123456）
   - **直接複製即可**

3. **找到App Secret（應用程式密鑰）**
   - 在「基本」頁面中，找到「應用程式密鑰」區塊
   - 點擊「顯示」按鈕（可能需要輸入Facebook密碼確認）
   - 會顯示一串長字串（如：`a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`）
   - **立即複製並保存**（只會顯示一次！）

**📸 視覺指引：**
```
開發者儀表板
  └─ 我的應用程式
      └─ [您的應用程式名稱]
          └─ 設定
              └─ 基本
                  ├─ 應用程式編號 (App ID) ← 這裡
                  └─ 應用程式密鑰 (App Secret) ← 點擊「顯示」
```

**⚠️ 安全提醒：**
- App Secret 是敏感資訊，不要分享給他人
- 不要將 App Secret 提交到公開的程式碼庫
- 如果懷疑洩露，可以重新生成 App Secret

## 配置系統

### 1. 創建.env文件

在專案根目錄創建 `.env` 文件：

```bash
cd /Users/hanshsieh/taiwan-music-events
touch .env
```

### 2. 編輯.env文件

使用文字編輯器打開 `.env` 文件，填入您從開發者工具中獲取的參數：

```env
# Threads API 配置
# 從 Graph API Explorer 或長期Token獲取的Access Token
THREADS_ACCESS_TOKEN=EAABwzLix...（貼上您的Token）

# 從應用程式設定 → 基本 頁面獲取的App ID
THREADS_APP_ID=1234567890123456（貼上您的App ID）

# 從應用程式設定 → 基本 頁面獲取的App Secret
THREADS_APP_SECRET=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6（貼上您的App Secret）

# 其他配置（可選）
LOG_LEVEL=INFO
```

**📝 參數對應關係：**

| .env 變數 | 在開發者工具中的位置 | 說明 |
|----------|---------------------|------|
| `THREADS_ACCESS_TOKEN` | Graph API Explorer → 存取權杖欄位 | 用於API認證 |
| `THREADS_APP_ID` | 設定 → 基本 → 應用程式編號 | 應用程式識別碼 |
| `THREADS_APP_SECRET` | 設定 → 基本 → 應用程式密鑰 | 應用程式密鑰 |

**⚠️ 注意：**
- 所有參數都是**必填**的
- Token 如果是短期Token，1-2小時後會過期，需要重新獲取
- 建議使用長期Token（60天有效）

### 3. 測試配置

運行測試腳本：

```bash
source venv/bin/activate
python -c "from src.threads.threads_poster import ThreadsPoster; import os; from dotenv import load_dotenv; load_dotenv(); poster = ThreadsPoster(os.getenv('THREADS_ACCESS_TOKEN')); print('Threads API配置成功！')"
```

## 注意事項

### Token有效期

- **短期Token**：通常1-2小時有效
- **長期Token**：通常60天有效
- **永久Token**：需要設置應用程式為「生產模式」並通過審核

### 權限要求

確保您的應用程式有以下權限：
- `threads_basic` - 基本讀取權限
- `threads_content_publish` - 發布內容權限

### 速率限制

Threads API有速率限制：
- 每個應用程式每小時最多200個請求
- 建議在發布時添加適當的延遲

### 安全建議

1. **不要將.env文件提交到Git**
   - `.env`已在`.gitignore`中
   - 使用`.env.example`作為模板

2. **定期更新Token**
   - 設置提醒更新長期Token
   - 考慮實現Token自動刷新機制

3. **使用環境變數**
   - 在生產環境中使用環境變數而非文件
   - 使用密鑰管理服務（如AWS Secrets Manager）

## 故障排除

### 問題1：Token無效
- 檢查Token是否過期
- 確認Token權限是否正確
- 重新生成Token

### 問題2：發布失敗
- 檢查內容是否符合Threads規範
- 確認圖片大小和格式
- 查看日誌了解具體錯誤

### 問題3：權限不足
- 確認應用程式已添加Threads API產品
- 檢查Token是否包含必要權限
- 確認應用程式狀態（開發/生產模式）

## 測試發布

創建測試腳本 `test_threads.py`：

```python
from src.threads.threads_poster import ThreadsPoster
import os
from dotenv import load_dotenv

load_dotenv()

access_token = os.getenv("THREADS_ACCESS_TOKEN")
if not access_token:
    print("錯誤：未設置THREADS_ACCESS_TOKEN")
    exit(1)

poster = ThreadsPoster(access_token)

# 測試發布
test_text = "🎵 測試發布\n\n這是一個測試貼文。"
success = poster.create_post(test_text)

if success:
    print("✅ 發布成功！")
else:
    print("❌ 發布失敗，請檢查日誌")
```

運行測試：
```bash
source venv/bin/activate
python test_threads.py
```

## 下一步

配置完成後，系統會自動：
1. 抓取Instagram活動
2. 處理和保存數據
3. 發布到Threads

查看 `USAGE.md` 了解如何使用系統。

