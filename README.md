# HVCR-10 免費研究網站

GitHub Actions 每週一至五 23:30 UTC 嘗試更新，使用 yfinance 免費數據與 15 隻預選美股，非全美股歷史股票池。

## 部署
1. GitHub Actions → HVCR-10 Daily Update → Run workflow，首次生成 site/data/report.json。
2. Cloudflare Dashboard → Workers & Pages → Create Pages → Connect to Git，選擇本 Repository。
3. Framework preset: None；Build command 留空；Build output directory: site。
4. 如 Actions 無法提交報告，在 Settings → Actions → General 確認 Workflow permissions 允許 Read and write。

## 限制
僅研究用途，並非投資建議。網站內展示訊號，不含主動 Telegram/Email 推播。免費數據可能限流；排程可能延遲。歷史條件報酬非可執行策略回測；預選股票有存活者及選股偏差。

## v2 模型與回測限制
- ZigZag 門檻為 max(5%, 1.5×ATR14/Close)，只在確認日記錄轉折；週期以確認日間距計算，非實際波峰波谷時間。
- 週期穩定分數是研究用啟發式評分，並非預測機率；最近最多 12 個已確認週期，分數至少 75 才列為觀察。
- 收盤產生訊號、次日開盤進場、固定進場 ATR 的 1.5 倍停損，最長持有 10 個交易日；隔夜跳空按開盤價處理，日內觸及停損按停損價處理。
- 成本假設每邊 15 bps（共 30 bps），尚未依股票估計真實滑價、衝擊成本、融資或稅務。
- 僅 15 隻目前預選股票，存在存活者偏差；尚未進行獨立樣本外、退市證券、財報事件及完整交易可行性驗證。
- 重新執行 GitHub Actions 以產生 v2 JSON。Telegram 通知將依新模型結果發送；訊號數量可能不同。
