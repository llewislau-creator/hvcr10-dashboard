"""Send HVCR-10 daily report through Telegram Bot API (stdlib only)."""
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPORT = Path(__file__).resolve().parents[1] / "site" / "data" / "report.json"
URL = "https://hvcr10-dashboard.pages.dev/"

def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("Telegram not configured: add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in GitHub Actions secrets.")
        return 0
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    rows = report.get("rows", [])
    signals = [r for r in rows if r.get("signal") == "反轉觀察"]
    date = max((r.get("last_price_date", "") for r in rows), default="未知")
    lines = [
        "📊 HVCR-10 每日美股研究報告",
        f"股價日期：{date}",
        f"成功分析：{len(rows)} 隻｜反轉觀察：{len(signals)} 隻",
        "",
    ]
    if signals:
        lines.append("🔎 今日反轉觀察：")
        for r in signals:
            lines.append(f"• {r['ticker']}｜收盤 ${r['close']}｜Z20 {r['z20']}｜RV20 {r['rv20']}%")
    else:
        lines.append("今日沒有符合條件的反轉觀察股票。")
    if report.get("errors"):
        lines.append(f"⚠️ 下載失敗：{len(report['errors'])} 隻")
    lines += ["", f"完整報告：{URL}", "僅供研究，非買賣建議。"]
    body = urllib.parse.urlencode({"chat_id": chat_id, "text": "\n".join(lines)}).encode()
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=body, method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.loads(response.read().decode())
        if not result.get("ok"):
            raise RuntimeError("Telegram API returned unsuccessful response")
        print("Telegram report delivered.")
        return 0
    except Exception as exc:
        print(f"Telegram delivery failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
