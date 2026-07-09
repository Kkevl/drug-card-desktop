# 藥物記憶卡 使用說明

這是一個可以在 Windows 11 與 macOS 上離線使用的藥物記憶卡軟體。  
不需要網路、不需要登入帳號，也不需要開瀏覽器。

## 快速開始

### 如果你拿到的是 Windows 已打包版本

1. 打開 `DrugFlashcard` 資料夾。
2. 找到 `DrugFlashcard.exe`。
3. 用滑鼠左鍵雙擊 `DrugFlashcard.exe`。
4. 程式打開後就可以開始使用。

請不要只複製 `DrugFlashcard.exe` 一個檔案。  
如果要把軟體交給別人，請複製整個 `DrugFlashcard` 資料夾。

### 如果你拿到的是 macOS 已打包版本

1. 找到 `DrugFlashcard.app`。
2. 雙擊 `DrugFlashcard.app`。
3. 如果 macOS 擋下未簽章 app，測試版可嘗試右鍵點 app，選擇 `打開`。

Windows 的 `.exe` 不能直接給 Mac 使用。  
macOS 的 `.app` 也不能直接在 Windows 執行。  
同一份原始碼可以共用，但發佈檔需要分平台產生。

### 如果你是在 Windows 原始碼資料夾中使用

1. 打開你下載或解壓縮後的軟體資料夾。
2. 找到 `run_app.bat`。
3. 雙擊 `run_app.bat`。
4. 如果 Windows 跳出安全提醒，確認這是你自己的檔案後選擇繼續執行。

平常使用時，不需要打開 `main.py`，也不需要自己輸入指令。

### 如果你是在 macOS 原始碼資料夾中使用

一般使用者建議使用已打包的 `.app`。  
如果你是在 macOS 上拿到原始碼資料夾，也可以用內建腳本啟動：

1. 打開 `終端機 Terminal`。
2. 把目前位置切到軟體資料夾。
3. 執行：

```bash
bash run_macos.sh
```

第一次執行時，腳本會自動建立 `.venv` 並安裝需要的套件。  
之後再執行同一個指令即可開啟程式。

macOS 原始碼執行需要 Python 3.9 或更新版本。  
如果 Python 太舊，腳本會停止並顯示目前版本。

## 主畫面介紹

程式上方有兩個分頁：

- `複習模式`：用記憶卡複習藥物。
- `考試模式`：用輸入答案的方式測驗自己。

右上角有 `設定` 按鈕。  
新增、編輯、刪除、匯入、匯出、考試項目管理都在設定裡。

## 複習模式怎麼用

1. 進入 `複習模式`。
2. 畫面中間會顯示一張藥物卡片。
3. 卡片正面會顯示藥名。
4. 按 `翻面` 可以看到：
   - 分類
   - 藥物的機制
   - 考點
   - 副作用
   - 備註
5. 按 `上一張`、`下一張` 可以切換卡片。
6. 按 `隨機抽卡` 可以隨機看一張卡片。

翻到背面後，畫面會出現熟悉度：

- `不熟`
- `普通`
- `熟`

你可以依照自己的狀況標記。  
改熟悉度不會增加複習次數；只有翻到背面時才會記錄一次複習。

## 搜尋與篩選

在 `複習模式` 上方可以搜尋或篩選：

- 在搜尋框輸入藥名，可以找指定藥物。
- 用分類下拉選單，可以只看某一類藥物。
- 勾選 `只複習不熟`，只會顯示熟悉度為 `不熟` 的卡片。

如果沒有符合的卡片，畫面會顯示提示，不會當掉。

## 新增藥物卡片

1. 按右上角 `設定`。
2. 按 `新增藥物`。
3. 填寫藥物資料。
4. `drug_name` 是必填欄位。
5. 填完後按 `Save`。

可以填的欄位：

- `drug_name`：藥名
- `category`：分類
- `mechanism`：藥物的機制
- `key_points`：考點
- `side_effects`：副作用
- `note`：備註
- `familiarity`：熟悉度

## 編輯或刪除卡片

### 編輯卡片

1. 先在主畫面切到你想修改的藥物卡片。
2. 按 `設定`。
3. 按 `編輯目前卡片`。
4. 修改內容後按 `Save`。

### 刪除卡片

1. 先在主畫面切到你想刪除的藥物卡片。
2. 按 `設定`。
3. 按 `刪除目前卡片`。
4. 系統會再次確認，避免誤刪。

刪除後無法從軟體內復原，請小心使用。

## 資料庫要怎麼編輯

一般使用者不需要直接打開資料庫檔案。

建議用這三種方式管理資料：

1. 在軟體中按 `設定`，使用 `新增藥物`、`編輯目前卡片`、`刪除目前卡片`。
2. 用 `匯出 CSV` 把資料匯出，用 Excel 編輯後，再用 `匯入 CSV` 匯回來。
3. 如果要整批更換資料，關閉軟體後，替換資料庫檔案。

資料庫檔案名稱是：

```text
drug_cards.db
```

資料庫不會放在 exe 或 app bundle 裡，而是放在目前使用者的應用程式資料目錄。

Windows 預設位置：

```text
%APPDATA%\DrugFlashcard\drug_cards.db
```

macOS 預設位置：

```text
~/Library/Application Support/DrugFlashcard/drug_cards.db
```

請注意：

- 不建議在軟體開啟時直接修改 `drug_cards.db`。
- 如果要複製、覆蓋或備份資料庫，請先關閉軟體。
- 如果你不知道怎麼直接編輯資料庫，請使用 CSV 匯入 / 匯出，這對一般使用者最安全。

## 考試模式怎麼用

考試模式會顯示藥名，讓你輸入指定項目的答案。

### 第一次使用考試模式前

請先幫藥物卡片設定考試項目：

1. 按 `設定`。
2. 按 `考試項目管理`。
3. 選擇一張藥物卡片。
4. 按 `新增項目`。
5. 填寫：
   - `項目名稱 item_name`
   - `標準答案 expected_answer`
   - `分數 points`
6. 按 `Save`。

常見項目名稱可以是：

- 機轉
- 適應症 / 用途
- 副作用
- 禁忌症
- 考點
- 備註

### 開始考試

1. 切換到 `考試模式` 分頁。
2. 選擇考試範圍：
   - 全部卡片
   - 指定分類
   - 只考不熟
3. 選擇題目數量：
   - 全部
   - 10 題
   - 20 題
   - 自訂數量
4. 按 `開始考試`。
5. 題目會顯示藥名。
6. 依照畫面上的項目輸入答案。
7. 按 `確認答案`。
8. 看完結果後按 `下一題`。
9. 最後會顯示總分、滿分、正確率與錯題列表。

## 考試答案怎麼判斷

目前採用簡單嚴格比對。

系統只會忽略：

- 答案前後多餘空白
- 大小寫差異
- 中間連續多個空白

例如標準答案是：

```text
COX inhibitor
```

以下會算對：

```text
COX inhibitor
 cox inhibitor
cox   inhibitor
```

以下會算錯：

```text
COX
inhibits COX
NSAID mechanism
cyclooxygenase inhibitor
```

也就是說，答案需要和標準答案一致才會得分。  
系統不會判斷同義詞，也不會因為你寫到部分關鍵字就給分。

## 考試後熟悉度怎麼更新

考試結束後，系統會依照每張卡片的答題結果自動更新熟悉度：

- 正確率 80% 以上：標記為 `熟`
- 正確率 50% 到 79%：標記為 `普通`
- 正確率低於 50%：標記為 `不熟`

考試也會更新複習次數與最後複習時間。

## 匯入 CSV

如果你有很多藥物資料，可以用 CSV 一次匯入。

1. 按 `設定`。
2. 按 `匯入 CSV`。
3. 選擇 CSV 檔案。
4. 匯入完成後，卡片會出現在軟體中。

軟體會自動嘗試常見 CSV 編碼，包括：

- UTF-8 with BOM
- UTF-8
- Big5 / CP950
- GB18030

如果你用 Windows Excel 編輯 CSV，通常也可以正常匯入中文。  
匯入完成後，提示訊息會顯示本次使用的編碼。

如果匯入後軟體內也顯示亂碼，通常代表 CSV 在匯入時已經被錯誤解碼。  
這種已寫入資料庫的亂碼資料通常無法自動修復，建議刪除亂碼資料後，從原始 CSV 重新匯入。

CSV 至少要有 `drug_name` 欄位。

建議欄位如下：

```text
drug_name,category,mechanism,key_points,side_effects,note,familiarity
```

`familiarity` 可以填：

```text
不熟
普通
熟
```

如果不知道怎麼準備 CSV，可以先新增幾張卡片，再使用匯出 CSV 來看範例格式。

## 匯出 CSV

1. 按 `設定`。
2. 按 `匯出 CSV`。
3. 選擇要儲存的位置。
4. 軟體會產生一個 CSV 檔案。

CSV 可以用 Excel、Google Sheets 或文字編輯器開啟。

軟體匯出時會使用 `UTF-8 BOM` 格式，讓 Windows Excel 直接開啟時中文比較不容易亂碼。

如果你直接打開 CSV 還是看到中文亂碼，可以改用 Excel 的「資料匯入」功能，並選擇 UTF-8 編碼。

## 匯出 Excel .xlsx

如果主要是給 Excel 使用，建議優先匯出 `.xlsx`。

1. 按 `設定`。
2. 按 `匯出 Excel .xlsx`。
3. 選擇要儲存的位置。
4. 用 Excel 開啟匯出的 `.xlsx` 檔案。

`.xlsx` 比 CSV 更不容易遇到中文亂碼，適合直接交給客戶查看或編輯。

## 資料存在哪裡

資料會存在目前使用者的應用程式資料目錄。

Windows：

```text
%APPDATA%\DrugFlashcard\drug_cards.db
```

macOS：

```text
~/Library/Application Support/DrugFlashcard/drug_cards.db
```

請不要隨便刪除這個檔案。  
如果要備份資料，可以複製上方位置的 `drug_cards.db` 到安全的位置。

如果你第一次開啟軟體，程式會自動建立資料夾、資料庫與資料表。  
如果你想使用自己的資料，建議用 CSV 匯入；進階使用者也可以關閉軟體後，用自己的 `drug_cards.db` 覆蓋上方位置的資料庫。

舊版如果資料庫放在軟體資料夾根目錄：

```text
drug_cards.db
```

新版啟動時會自動複製到：

```text
目前使用者的應用程式資料目錄
```

## 常見問題

### 打不開軟體怎麼辦？

請先確認你是雙擊：

```text
run_app.bat
```

或打包後的：

```text
DrugFlashcard.exe
```

不要直接雙擊 `main.py`。

### 為什麼考試模式沒有題目？

通常是因為還沒有設定考試項目。

請到：

```text
設定 > 考試項目管理
```

幫至少一張藥物卡片新增考試項目。

### 匯入 CSV 後中文變亂碼怎麼辦？

新版匯入會自動嘗試多種編碼。  
如果資料已經用錯誤編碼匯入到資料庫，軟體無法保證自動修復既有亂碼資料。

建議做法：

1. 刪除亂碼卡片，或改用乾淨的資料庫備份。
2. 找回原始 CSV。
3. 用新版軟體重新匯入。

### 直接開啟 CSV 看到中文亂碼怎麼辦？

這通常是 Excel 或記事本猜錯 CSV 編碼，不一定是軟體資料壞掉。

建議優先嘗試：

1. 改用 `匯出 Excel .xlsx`。
2. 或重新用 `匯出 CSV` 產生 UTF-8 BOM 格式的 CSV。
3. 或在 Excel 中使用「資料匯入」功能，手動選擇 UTF-8 編碼。

### 為什麼答案看起來差不多卻算錯？

因為目前考試模式是嚴格比對。  
答案必須和標準答案一致才會得分。

### 刪除卡片後可以復原嗎？

目前軟體內沒有復原功能。  
建議定期備份 `drug_cards.db`。

### 沒有網路可以用嗎？

可以。  
這個軟體是本機離線使用，不需要網路。

## 快捷鍵

在複習模式可以使用：

- `Space`：翻面
- `Right`：下一張
- `Left`：上一張

## 給維護者：從原始碼執行

一般使用者不需要看這段。  

### Windows 原始碼執行

如果你是在 Windows 原始碼資料夾中維護程式，可以使用：

```powershell
.\.venv\Scripts\python.exe main.py
```

如果尚未建立虛擬環境：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### macOS 原始碼執行

請在 macOS 環境執行：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

最低支援 Python 3.9。  
如果 `.venv` 是用太舊的 Python 建立的，請刪除 `.venv` 後重新執行 `bash run_macos.sh`。

## 給維護者：重新打包

PyInstaller 不是 cross-compiler。

- Windows 的 `.exe` 必須在 Windows 上打包。
- macOS 的 `.app` 必須在 macOS 上打包。
- 同一份原始碼可以共用，但發佈檔要分平台產生。

### Windows 打包 exe

```powershell
.\build_exe.bat
```

等同於：

```powershell
.\.venv\Scripts\pyinstaller.exe --noconfirm --windowed --name DrugFlashcard main.py
```

打包完成後，輸出位置通常是：

```text
.\dist\DrugFlashcard\DrugFlashcard.exe
```

要給別人使用時，請複製整個資料夾：

```text
.\dist\DrugFlashcard
```

接收方不需要安裝 Python。

### macOS 打包 app

請在 macOS 環境執行：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pyinstaller --noconfirm --windowed --name DrugFlashcard main.py
```

或執行：

```bash
bash build_macos.sh
```

打包完成後，輸出位置通常是：

```text
dist/DrugFlashcard.app
```

目前如果是在 Windows 上開發，只能完成跨平台程式碼與 macOS 打包文件；真正可執行的 `.app` 需要在 macOS 上產生。

### macOS 安全性提示

- 未簽章的 macOS app 可能會被 Gatekeeper 阻擋。
- 測試版可以請使用者右鍵點 `DrugFlashcard.app`，再選擇 `打開`。
- 若要正式發佈給客戶，建議之後做 Apple Developer ID 簽章與 notarization。
- 若要更正式發佈，可以之後再製作 `.dmg`。

## 給維護者：主要檔案

- `main.py`：程式畫面與操作流程。
- `database.py`：本機資料儲存、匯入匯出、考試結果紀錄。
- `models.py`：資料結構。
- `requirements.txt`：需要安裝的套件。
- `run_app.bat`：在原始碼資料夾中啟動軟體。
- `run_macos.sh`：在 macOS 原始碼資料夾中啟動軟體。
- `build_exe.bat`：在 Windows 打包成 exe。
- `build_macos.sh`：在 macOS 打包成 app。
