#!/usr/bin/env python3
"""Post-build sanity check: every internal link/src in public/ must resolve to a file.

    python3 scripts/check_site.py public
"""
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls, self.ids = [], set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        for k in ("href", "src"):
            if a.get(k):
                self.urls.append(a[k])


def main(root: Path) -> int:
    pages = {}
    for f in root.rglob("*.html"):
        p = Links()
        p.feed(f.read_text(encoding="utf-8", errors="replace"))
        pages[f] = p
    broken = []
    for f, p in pages.items():
        for url in p.urls:
            u = urlparse(url)
            if u.scheme or url.startswith(("mailto:", "tel:", "//", "data:")):
                continue
            path = unquote(u.path)
            if not path:  # same-page anchor
                continue
            target = (root / path.lstrip("/")) if path.startswith("/") else (f.parent / path)
            if target.is_dir() or path.endswith("/"):
                target = target / "index.html"
            if not target.exists():
                broken.append(f"{f.relative_to(root)} -> {url}")
            elif u.fragment and target.suffix == ".html" and target in pages and u.fragment not in pages[target].ids:
                broken.append(f"{f.relative_to(root)} -> {url} (missing anchor)")
    for b in sorted(set(broken)):
        print("BROKEN:", b)
    required = ["index.html", "publication/index.html", "bibliography/publications.bib", "index.json"]
    missing = [r for r in required if not (root / r).exists()]
    for m in missing:
        print("MISSING:", m)
    print(f"Checked {len(pages)} pages: {len(set(broken))} broken links, {len(missing)} missing files")
    return 1 if broken or missing else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1] if len(sys.argv) > 1 else "public")))
