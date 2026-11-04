# HVCR-10 免費研究網站

GitHub Actions 每週一至五 23:30 UTC 嘗試更新，使用 yfinance 免費數據與 15 隻預選美股，非全美股歷史股票池。

## 部署
1. GitHub Actions → HVCR-10 Daily Update → Run workflow，首次生成 site/data/report.json。
2. Cloudflare Dashboard → Workers & Pages → Create Pages → Connect to Git，選擇本 Repository。
3. Framework preset: None；Build command 留空；Build output directory: site。
4. 如 Actions 無法提交報告，在 Settings → Actions → General 確認 Workflow permissions 允許 Read and write。

## 限制
僅研究用途，並非投資建議。網站內展示訊號，不含主動 Telegram/Email 推播。免費數據可能限流；排程可能延遲。歷史條件報酬非可執行策略回測；預選股票有存活者及選股偏差。