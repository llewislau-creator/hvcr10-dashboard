"""P0/P1 regression gates: source syntax, strategy provenance, and homepage parity."""
import ast
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"

class P0P1Regression(unittest.TestCase):
    def test_all_python_sources_compile(self):
        for path in list((ROOT / "scripts").glob("*.py")) + list((ROOT / "tests").glob("*.py")):
            with self.subTest(path=path.name):
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    def test_portfolio_no_literal_newline_escapes_in_statements(self):
        source = (ROOT / "scripts" / "portfolio_risk.py").read_text(encoding="utf-8")
        self.assertNotIn(r"\n    traded_tickers=", source)
        self.assertNotIn(r"\n            if not np.isfinite", source)
        self.assertNotIn(r"\n    frame=pd.DataFrame", source)

    def test_homepage_uses_same_eligible_rows_as_rankings(self):
        source = (SITE / "homepage.js").read_text(encoding="utf-8")
        self.assertIn("r.data_quality?.status!=='blocked'", source)
        self.assertNotIn("r=>r.swing&&r.data_quality?.status==='ok'", source)
        self.assertIn("iidStrong", source)
        self.assertIn("與五維核心策略不同", source)

    def test_published_priority_is_counted_even_with_warning(self):
        data = json.loads((SITE / "data" / "report.json").read_text(encoding="utf-8"))
        rows = [r for r in data["rows"] if r.get("swing") and r.get("data_quality", {}).get("status") != "blocked"]
        priorities = [r for r in rows if r["swing"].get("signal") == "優先研究"]
        self.assertEqual(len(priorities), sum(r["swing"]["signal"] == "優先研究" for r in data["rows"]))
        self.assertTrue(all(r["data_quality"]["status"] in ("ok", "warning") for r in priorities))

    def test_strategies_are_disclosed_on_all_pages(self):
        for page in ("overview", "screener", "stock", "backtest", "portfolio", "method"):
            html = (SITE / (page + ".html")).read_text(encoding="utf-8")
            with self.subTest(page=page):
                self.assertIn("ATR 獨立策略", html)
                self.assertIn("五維核心", html)
        js = (SITE / "research-app.js").read_text(encoding="utf-8")
        self.assertIn("與五維分數≥60的持有期研究不同", js)
        self.assertIn("前40%暖機、後60%逐日驗證", js)

if __name__ == "__main__":
    unittest.main()
