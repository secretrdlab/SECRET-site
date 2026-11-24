#!/usr/bin/env python3
"""Convert bibliography/*.bib into JSON data files that Hugo renders.

    python3 scripts/bib2data.py            # validate + write data/generated/*.json
    python3 scripts/bib2data.py --check    # validate only (used by CI); exit 1 on errors

Outputs (git-ignored, regenerated on every build):
    data/generated/publications.json   papers from bibliography/publications.bib
    data/generated/theses.json         theses from bibliography/theses.bib
    data/generated/people_pubs.json    {person-slug: [bibtex keys]} for profile pages
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

try:
    import bibtexparser
    import yaml
    from bibtexparser.bparser import BibTexParser
    from bibtexparser.bwriter import BibTexWriter
    from bibtexparser.customization import convert_to_unicode
except ImportError:
    sys.exit("Missing dependencies. Run: pip install -r requirements.txt")

ROOT = Path(__file__).resolve().parent.parent
BIB_DIR = ROOT / "bibliography"
OUT_DIR = ROOT / "data" / "generated"
PEOPLE_DIR = ROOT / "content" / "people"

TYPE_LABELS = {
    "article": "Journal article",
    "inproceedings": "Conference paper",
    "conference": "Conference paper",
    "incollection": "Book chapter",
    "inbook": "Book chapter",
    "book": "Book",
    "techreport": "Technical report",
    "misc": "Other",
    "phdthesis": "PhD thesis",
    "mastersthesis": "MSc dissertation",
}
REQUIRED = {
    "article": ["author", "title", "year", "journal"],
    "inproceedings": ["author", "title", "year", "booktitle"],
    "conference": ["author", "title", "year", "booktitle"],
    "incollection": ["author", "title", "year", "booktitle"],
    "phdthesis": ["author", "title", "year", "school"],
    "mastersthesis": ["author", "title", "year", "school"],
}
DEFAULT_REQUIRED = ["author", "title", "year"]

errors: list[str] = []
warnings: list[str] = []


# ---------------------------------------------------------------- helpers
def strip_tex(s: str) -> str:
    """Remove leftover LaTeX braces/commands after unicode conversion."""
    s = re.sub(r"\\(?:textit|textbf|emph|texttt|textsc)\s*", "", s)
    s = s.replace("\\&", "&").replace("\\%", "%").replace("\\#", "#").replace("\\_", "_")
    s = s.replace("``", "\u201c").replace("''", "\u201d").replace("--", "\u2013")
    s = s.replace("{", "").replace("}", "").replace("~", "\u00a0")
    return re.sub(r"\s+", " ", s).strip()


def fold(s: str) -> str:
    """Accent/case/punctuation-insensitive form used for name matching."""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]", "", s)


def split_name(name: str) -> tuple[str, str]:
    """BibTeX name -> (first, last). Handles 'Last, First', 'Last, Jr, First' and 'First Last'."""
    name = name.strip()
    if "," in name:
        parts = [p.strip() for p in name.split(",")]
        last = parts[0]
        first = parts[-1] if len(parts) > 1 else ""
        if len(parts) == 3:  # Last, Jr, First
            last = f"{parts[0]} {parts[1]}"
        return first, last
    tokens = name.split()
    return " ".join(tokens[:-1]), tokens[-1] if tokens else ""


def initials(first: str) -> str:
    out = []
    for tok in re.split(r"\s+", first.strip()):
        if not tok:
            continue
        sub = [p for p in re.split(r"[-.]", tok) if p]
        if tok[0].islower():  # particles like "de", "da"
            continue
        out.append(("-" if "-" in tok else " ").join(p[0] + "." for p in sub))
    return " ".join(out)


def parse_authors(field: str) -> list[dict]:
    people = []
    for raw in re.split(r"\s+and\s+", field.strip()):
        if not raw:
            continue
        if raw.lower() == "others":
            people.append({"first": "", "last": "et al.", "short": "et al.", "full": "et al.", "fold": ""})
            continue
        first, last = split_name(strip_tex(raw))
        short = f"{last}, {initials(first)}".strip().rstrip(",")
        people.append({"first": first, "last": last, "short": short,
                       "full": f"{first} {last}".strip(), "fold": fold(last) + "_" + fold(first)[:1]})
    return people


def load_bib(path: Path):
    """Return (unicode-converted entries, raw entries keyed by ID)."""
    text = path.read_text(encoding="utf-8")
    p_uni = BibTexParser(common_strings=True)
    p_uni.ignore_nonstandard_types = False
    p_uni.customization = convert_to_unicode
    p_raw = BibTexParser(common_strings=True)
    p_raw.ignore_nonstandard_types = False
    uni = bibtexparser.loads(text, parser=p_uni).entries
    raw = {e["ID"]: e for e in bibtexparser.loads(text, parser=p_raw).entries}
    # detect duplicate keys (bibtexparser silently keeps both)
    keys = re.findall(r"^\s*@\w+\s*\{\s*([^,\s]+)\s*,", text, flags=re.M)
    seen = set()
    for k in keys:
        if k in seen:
            errors.append(f"{path.name}: duplicate key '{k}'")
        seen.add(k)
    return uni, raw


def entry_to_bibtex(raw_entry: dict) -> str:
    """Re-serialise one entry as a tidy, standalone BibTeX string (without site-only fields)."""
    e = {k: v for k, v in raw_entry.items() if k not in ("pdf", "code", "slides", "featured", "abstract")}
    db = bibtexparser.bibdatabase.BibDatabase()
    db.entries = [e]
    w = BibTexWriter()
    w.indent = "  "
    w.align_values = True
    w.order_entries_by = None
    w.display_order = ["author", "title", "journal", "booktitle", "series", "editor", "school",
                       "volume", "number", "pages", "year", "month", "publisher", "address", "doi", "url"]
    return bibtexparser.dumps(db, w).strip()


def convert(path: Path) -> list[dict]:
    if not path.exists():
        warnings.append(f"{path} not found — skipping")
        return []
    uni, raw = load_bib(path)
    items = []
    for e in uni:
        key, etype = e["ID"], e["ENTRYTYPE"].lower()
        for field in REQUIRED.get(etype, DEFAULT_REQUIRED):
            if not e.get(field, "").strip():
                errors.append(f"{path.name}: [{key}] missing required field '{field}'")
        year = e.get("year", "").strip()
        if year and not re.fullmatch(r"\d{4}", year):
            errors.append(f"{path.name}: [{key}] year must be 4 digits, got '{year}'")
        if etype not in TYPE_LABELS:
            warnings.append(f"{path.name}: [{key}] unusual entry type @{etype}")
        if etype not in ("phdthesis", "mastersthesis") and not (e.get("doi") or e.get("url")):
            warnings.append(f"{path.name}: [{key}] has no doi/url (link button will be hidden)")
        doi = e.get("doi", "").strip()
        doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
        url = e.get("url", "").strip() or (f"https://doi.org/{doi}" if doi else "")
        items.append({
            "key": key,
            "type": etype,
            "type_label": TYPE_LABELS.get(etype, etype.capitalize()),
            "title": strip_tex(e.get("title", "")),
            "authors": parse_authors(e.get("author", "")),
            "year": int(year) if year.isdigit() else 0,
            "venue": strip_tex(e.get("journal") or e.get("booktitle") or e.get("school")
                               or e.get("institution") or e.get("howpublished") or ""),
            "series": strip_tex(e.get("series", "")),
            "volume": strip_tex(e.get("volume", "")),
            "number": strip_tex(e.get("number", "")),
            "pages": strip_tex(e.get("pages", "")),
            "publisher": strip_tex(e.get("publisher", "")),
            "advisors": [a["full"] for a in parse_authors(e.get("advisor", ""))] if e.get("advisor") else [],
            "abstract": strip_tex(e.get("abstract", "")),
            "note": strip_tex(e.get("note", "")),
            "doi": doi,
            "url": url,
            "pdf": e.get("pdf", ""),
            "code": e.get("code", ""),
            "slides": e.get("slides", ""),
            "bibtex": entry_to_bibtex(raw[key]) if key in raw else "",
        })
    # Newest year first; within a year, keep the order of the .bib file (stable sort).
    items.sort(key=lambda x: -x["year"])
    return items


def load_people() -> list[dict]:
    people = []
    for md in sorted(PEOPLE_DIR.glob("*/index.md")):
        text = md.read_text(encoding="utf-8")
        m = re.match(r"^---\s*\n(.*?)\n---", text, flags=re.S)
        if not m:
            errors.append(f"{md}: missing front matter")
            continue
        fm = yaml.safe_load(m.group(1)) or {}
        slug = md.parent.name
        names = fm.get("bib_names") or [f"{fm.get('last_name', '')}, {fm.get('first_name', '')}"]
        folds = set()
        for n in names:
            first, last = split_name(n)
            folds.add(fold(last) + "_" + fold(first)[:1])
        people.append({"slug": slug, "folds": folds, "title": fm.get("title", slug)})
    return people


def link_people(pubs: list[dict], people: list[dict]) -> dict:
    index: dict[str, list[str]] = {p["slug"]: [] for p in people}
    by_fold = {}
    for p in people:
        for f in p["folds"]:
            by_fold[f] = p["slug"]
    for pub in pubs:
        for a in pub["authors"]:
            slug = by_fold.get(a["fold"])
            if slug:
                a["person"] = slug
                if pub["key"] not in index[slug]:
                    index[slug].append(pub["key"])
    return index


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="validate only, don't write files")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = ap.parse_args()

    pubs = convert(BIB_DIR / "publications.bib")
    theses = convert(BIB_DIR / "theses.bib")
    people = load_people()
    people_pubs = link_people(pubs + theses, people)

    for w in warnings:
        print(f"WARNING: {w}")
    for e in errors:
        print(f"ERROR:   {e}")
    if errors or (args.strict and warnings):
        sys.exit(1)

    print(f"OK: {len(pubs)} publications, {len(theses)} theses, "
          f"{sum(1 for v in people_pubs.values() if v)} members linked to papers")
    if args.check:
        return
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, obj in (("publications", pubs), ("theses", theses), ("people_pubs", people_pubs)):
        (OUT_DIR / f"{name}.json").write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
