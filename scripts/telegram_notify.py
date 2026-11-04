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
    signals = [r for r in rows if r.get("signal") == "反彈觀察"]
    date = max((r.get("last_price_date", "") for r in rows), default="未知")
    lines = [
        "📊 HVCR-10 v3 反彈機率研究",
        f"股價日期：{date}",
        f"成功分析：{len(rows)} 隻｜反彈觀察：{len(signals)} 隻",
        "",
    ]
    if signals:
        lines.append("🔎 今日反彈觀察（10日內先觸及+8%）：")
        for r in signals:
            lines.append(f"• {r['ticker']}｜符合 {r.get('matched',0)}/6｜樣本外機率 {str(r.get('probability'))+'%' if r.get('probability') is not None else '樣本不足'}｜收盤 ${r['close']}")
    else:
        lines.append("今日沒有符合至少4/6條件且通過基本篩選的股票。")
    if report.get("errors"):
        lines.append(f"⚠️ 下載失敗：{len(report['errors'])} 隻")
    lines += ["", f"完整報告：{URL}", "樣本外歷史頻率非未來保證；未計入滑價，非買賣建議。"]
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
