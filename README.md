[README.md](https://github.com/user-attachments/files/33697641/README.md)
# MedLit Pocket V2.0 — iPhone 醫學文獻閱讀網站

網站：https://eran8575.github.io/medlit-pocket/

## 部署：將這個 ZIP **裡面的檔案**放到既有 GitHub repo 根目錄

1. 解壓縮，打開 `medlit_pocket_v2` 資料夾。
2. 到 https://github.com/eran8575/medlit-pocket ，選 **Add file → Upload files**。上傳 `index.html`、`update.py`、`requirements.txt`、`data/articles.json`。已存在的 `index.html` 請以新版本取代（GitHub 網頁上傳若不允許覆蓋，先開啟舊檔案點鉛筆 Edit，把新 HTML 全文貼上，或用 GitHub Desktop 直接複製覆蓋並 Push）。
3. **重要**：GitHub 網頁上傳不能直接保留 `.github/workflows` 目錄結構時，開啟 repo → Add file → Create new file，檔名輸入 `.github/workflows/daily.yml`，將 ZIP 中同名檔案的內容貼入並 Commit。或者使用 GitHub Desktop 把整個資料夾覆蓋進 repo，較簡單。
4. GitHub → Settings → Actions → General → Workflow permissions，勾選 **Read and write permissions**，Save。此權限用於把新的文章 JSON 寫回網站。
5. GitHub → Settings → Secrets and variables → Actions → New repository secret：新增 `OPENAI_API_KEY`、`TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID`。建議新增 `NCBI_EMAIL`（電子信箱）。**不可**把金鑰放在 HTML、Python 程式或公開 repo。
6. GitHub → Actions → `Daily PubMed update` → Run workflow → Run workflow。第一次會抓取預設推薦文獻及近期文獻，並產生 `data/articles.json`。
7. 等待 GitHub Pages 更新，刷新手機網站。GitHub Actions 的 cron 為 UTC 23:15，即台灣時間每天 **07:15**，但 GitHub 排程可能延遲，非精確保證。

## Telegram 設定

- Telegram 搜尋 `@BotFather`，執行 `/newbot`，取得 bot token（只放 GitHub Secret）。
- 用 Telegram 對自己的 bot 傳一則訊息。
- 在瀏覽器開啟 `https://api.telegram.org/bot<你的TOKEN>/getUpdates`，找 `message.chat.id`，把數字設為 `TELEGRAM_CHAT_ID` Secret。請不要分享 token 或含 token 的網址。
- 新增文獻時會推送最多五篇標題及網站連結；沒有新增文章時不推送。推播需先設定 secrets，且 GitHub Actions 執行成功。

## AI 及資料品質

- 需自行建立 **OpenAI API** 金鑰（ChatGPT 訂閱不包含 API 額度）。未設定仍可自動抓 PubMed，中文AI解析會標示尚未完成。
- 每天最多分析 `MAX_AI_ARTICLES=8` 篇新文獻及 `MAX_BACKFILL_AI=3` 篇舊文獻；可在 workflow env 修改。會產生 API 用量費用。
- 快速閱讀目標 500–800 中文字，深度閱讀目標 1500–2200 中文字；當摘要資訊不足時寧可縮短，不會杜撰結果。
- Google Scholar 僅作搜尋入口，**沒有自動爬取 Scholar**（避免不穩定及存取限制）。文獻收錄以 PubMed API 為主。
- 期刊優先級不是即時 impact factor 排名。
- 收藏與已讀僅保存在單一瀏覽器 localStorage，不會跨裝置同步。
- 這是公開靜態網站，請勿上傳病人資料、學生原始心得或任何 API 金鑰。

## 本地測試

`python -m pip install -r requirements.txt`

`python update.py`

`python -m http.server 8000` 後開啟 http://localhost:8000 。
