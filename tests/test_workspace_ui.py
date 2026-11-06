"""Static release gates for the six-page HVCR-10 research workspace."""
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1] / "site"
PAGES = ("overview", "screener", "stock", "backtest", "portfolio", "method")
REQUIRED_IDS = ("health", "summary", "exclusions", "overview", "quick-overview",
                "quick-list", "portfolio", "portfolio-horizon", "portfolio-status",
                "portfolio-summary", "equity-chart", "drawdown-chart", "portfolio-regime",
                "market", "rankings", "search-ticker", "filter-status", "sort",
                "rows", "stock", "ticker", "detail", "research-confidence",
                "risk-warnings", "stage2", "robustness", "forward-evidence",
                "methodology")

class Document(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.links = []
        self.assets = []
        self.page = None
        self.scripts = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a: self.ids.append(a["id"])
        if tag == "body": self.page = a.get("data-page")
        if tag == "a" and a.get("href", "").endswith(".html"):
            self.links.append(a["href"])
        if tag == "link" and a.get("rel") == "stylesheet":
            self.assets.append(a.get("href"))
        if tag == "script" and a.get("src"):
            self.scripts.append(a["src"])

class WorkspaceReleaseTests(unittest.TestCase):
    def test_pages_have_unique_required_dom_ids_and_assets(self):
        for page in PAGES:
            with self.subTest(page=page):
                doc = Document()
                doc.feed((ROOT / (page + ".html")).read_text(encoding="utf-8"))
                self.assertEqual(doc.page, page)
                self.assertEqual(len(doc.ids), len(set(doc.ids)))
                self.assertTrue(set(REQUIRED_IDS).issubset(doc.ids),
                                sorted(set(REQUIRED_IDS)-set(doc.ids)))
                self.assertIn("./workspace.css", doc.assets)
                self.assertIn("./quant-theme.css", doc.assets)
                self.assertIn("./research-app.js", doc.scripts)
                for other in PAGES:
                    self.assertIn("./" + other + ".html", doc.links)
                for asset in doc.assets + doc.scripts:
                    self.assertTrue((ROOT / asset).is_file(), asset)
    def test_entrypoints_route_to_overview(self):
        for name in ("index.html", "swing.html"):
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn("./overview.html", text)
    def test_page_visibility_rules_and_layout_primitives(self):
        css = (ROOT / "workspace.css").read_text(encoding="utf-8")
        for page in PAGES:
            self.assertIn('body[data-page="' + page + '"]', css)
        for selector in (".grid{display:grid", ".flex{display:flex",
                         ".scroll{max-width:100%", "@media(max-width:768px)"):
            self.assertIn(selector, css)
    def test_data_paths_and_user_controls(self):
        js = (ROOT / "research-app.js").read_text(encoding="utf-8")
        self.assertIn("./data/report.json", js)
        self.assertIn("./data/portfolio_risk.json", js)
        for control in ("search-ticker", "filter-status", "portfolio-horizon", "ticker"):
            self.assertIn(control, js)
        self.assertIn("encodeURIComponent(b.dataset.t)", js)

if __name__ == "__main__":
    unittest.main()
