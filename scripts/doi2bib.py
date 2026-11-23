#!/usr/bin/env python3
"""Fetch a paper's metadata from Crossref by DOI and append a clean BibTeX entry.

    python3 scripts/doi2bib.py 10.1145/3617897                 # append to bibliography/publications.bib
    python3 scripts/doi2bib.py 10.1145/3617897 10.1109/x.y     # several at once
    python3 scripts/doi2bib.py --print 10.1145/3617897         # only print, don't write

Always review the appended entry (title capitalisation, author names) before committing.
Uses only the Python standard library.
"""
import argparse
import html
import json
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

BIB = Path(__file__).resolve().parent.parent / "bibliography" / "publications.bib"
STOP = {"a", "an", "the", "on", "of", "in", "for", "to", "and", "is", "we", "why", "how", "what", "who", "with"}


def ascii_(s): return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
def clean(s): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html.unescape(s or ""))).strip()
def esc(s): return s.replace("&", r"\&").replace("%", r"\%").replace("#", r"\#")


def protect(title):
    """Brace words with internal capitals (acronyms, CamelCase) so styles keep their case."""
    return re.sub(r"[A-Za-z0-9\-]*[A-Za-z][A-Za-z0-9\-]*",
                  lambda m: "{" + m.group(0) + "}" if re.search(r".[A-Z]", m.group(0)) else m.group(0), title)


def person(p): return (p.get("family", "") + (", " + p["given"] if p.get("given") else "")).strip()


def year_of(c):
    for k in ("published-print", "published", "issued"):
        dp = c.get(k, {}).get("date-parts")
        if dp and dp[0] and dp[0][0]:
            return dp[0][0]


def fetch(doi):
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi)
    req = urllib.request.Request(url, headers={"User-Agent": "secret-site (mailto:secret@inf.ufpr.br)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["message"]


def to_bibtex(c, existing_keys):
    title = clean((c.get("title") or [""])[0])
    if c.get("subtitle") and c["subtitle"][0]:
        title += ": " + clean(c["subtitle"][0])
    authors = [person(a) for a in c.get("author", [])]
    year = year_of(c)
    containers = [clean(x) for x in c.get("container-title", [])]
    f = {}
    if c.get("type") == "journal-article":
        et, f["journal"] = "article", (containers[0] if containers else "")
    else:
        et = "inproceedings"
        series = [x for x in containers if x.lower().startswith(("lecture notes", "communications in"))]
        books = [x for x in containers if x not in series]
        f["booktitle"] = books[-1] if books else (containers[0] if containers else "")
        if series:
            f["series"] = series[0]
    if c.get("volume"): f["volume"] = c["volume"]
    if c.get("issue"): f["number"] = c["issue"]
    if c.get("page"): f["pages"] = c["page"].replace("-", "--")
    elif c.get("article-number"): f["pages"] = c["article-number"]
    if c.get("publisher"): f["publisher"] = clean(c["publisher"])
    f["doi"] = c["DOI"].lower()
    f["url"] = "https://doi.org/" + f["doi"]
    last = authors[0].split(",")[0] if authors else "anon"
    words = [w for w in re.findall(r"[a-z0-9]+", ascii_(title).lower()) if w not in STOP and len(w) >= 3]
    base = re.sub(r"[^a-z]", "", ascii_(last).lower()) + str(year) + (words[0] if words else "")
    key, n = base, 0
    while key in existing_keys:
        n += 1
        key = base + chr(96 + n)
    lines = [f"@{et}{{{key},", f"  author    = {{{' and '.join(authors)}}},", f"  title     = {{{protect(esc(title))}}},"]
    for k in ("journal", "booktitle", "series", "volume", "number", "pages", "year", "publisher", "doi", "url"):
        v = str(year) if k == "year" else f.get(k)
        if v:
            lines.append(f"  {k:<9} = {{{v if k in ('doi', 'url') else esc(v)}}},")
    lines[-1] = lines[-1].rstrip(",")
    return key, "\n".join(lines) + "\n}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dois", nargs="+")
    ap.add_argument("--print", action="store_true", dest="only_print")
    args = ap.parse_args()
    text = BIB.read_text(encoding="utf-8") if BIB.exists() else ""
    keys = set(re.findall(r"^@\w+\{([^,]+),", text, flags=re.M))
    known = {d.lower() for d in re.findall(r"doi\s*=\s*\{([^}]+)\}", text)}
    new = []
    for raw in args.dois:
        doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", raw.strip()).lower()
        if doi in known and not args.only_print:
            print(f"skip {doi}: already in {BIB.name}")
            continue
        try:
            c = fetch(doi)
        except Exception as e:
            print(f"error {doi}: {e}", file=sys.stderr)
            continue
        key, entry = to_bibtex(c, keys)
        keys.add(key)
        new.append(entry)
        print(entry + "\n")
    if new and not args.only_print:
        with BIB.open("a", encoding="utf-8") as fh:
            fh.write("\n" + "\n\n".join(new) + "\n")
        print(f"Appended {len(new)} entr{'y' if len(new) == 1 else 'ies'} to {BIB.relative_to(Path.cwd()) if BIB.is_relative_to(Path.cwd()) else BIB}")


if __name__ == "__main__":
    main()
