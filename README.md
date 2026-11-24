# SECRET website

Source of <https://secret.seg.br> — SECurity & Reverse Engineering Team, UFPR.

Plain [Hugo](https://gohugo.io) with a small built-in theme (no Hugo Blox, no Go modules), YAML data files,
and **BibTeX as the single source of truth for publications**. GitHub Actions validates, builds and publishes
every push to GitHub Pages.

## Where things live

| To change…                         | Edit                                             |
|------------------------------------|--------------------------------------------------|
| Papers                             | `bibliography/publications.bib`                  |
| Theses & dissertations             | `bibliography/theses.bib`                        |
| A member (add/remove/role/photo)   | `content/people/<name>/index.md` + `avatar.jpg`  |
| News posts                         | `content/post/<slug>/index.md` (+ images)        |
| Awards                             | `data/awards.yaml` + photo in `assets/images/awards/` |
| Partners                           | `data/partners.yaml` + logo in `assets/images/partners/` |
| Home page texts, contact, footer   | `data/site.yaml`                                 |
| Menu, site URL                     | `hugo.toml`                                      |
| Look & feel                        | `assets/css/main.css`, `layouts/`                |
| Icons                              | `assets/icons/*.svg` ([Font Awesome Free](https://fontawesome.com), CC BY 4.0) — add any other icon by copying its SVG there |

## Common tasks

**Add a paper with a DOI** (fetches metadata from Crossref and appends a clean entry):

```sh
.venv/bin/python scripts/doi2bib.py 10.1145/3617897
```

Review the new entry at the end of `publications.bib` (title capitalisation, accents), then commit.
For papers without a DOI, paste a BibTeX entry by hand — order in the file doesn't matter.
Optional extra fields the site understands: `pdf`, `code`, `slides`, `note`.

**Add a thesis:** add a `@phdthesis` or `@mastersthesis` entry to `theses.bib`
(`advisor = {A and B}`, `url`, `abstract` are shown on the page).

**Add a member:**

```sh
hugo new content people/jane-doe/index.md     # fills in the template
```

Put a square-ish photo next to it as `avatar.jpg`. Set `group` to one of the groups in `hugo.toml`
(`peopleGroups`). When someone leaves, change `group` to `Alumni / Past Visitors`.
Papers are linked to profiles automatically by surname + first initial; if someone publishes under
another spelling, list it under `bib_names` (see `content/people/paulo-almeida/index.md`).

**Add a news post:**

```sh
hugo new content post/my-news/index.md
```

## What the site does with BibTeX

`scripts/bib2data.py` reads the `.bib` files on every build and:

- **validates** them: the build fails on duplicate keys, missing required fields
  (`journal` for `@article`, `booktitle` for `@inproceedings`, …) or a malformed year;
- writes `data/generated/*.json`, which Hugo renders as `/publication/`, `/thesis-dissertations/`,
  the home page "Recent Publications" and each member's profile;
- each entry gets a **Cite** button (copy or download `/bib/<key>.bib`), and the full files are
  downloadable from `/bibliography/publications.bib` and `/bibliography/theses.bib`.

## Local preview

Needs Hugo **extended ≥ 0.146** and Python 3.

```sh
make setup      # once: creates .venv with bibtexparser + PyYAML
make serve      # http://localhost:1313 — run `make data` again after editing a .bib file
make check      # same validation + link check as GitHub Actions
```

## Publishing (GitHub Actions + GitHub Pages)

Every commit to `main` (from your computer or from GitHub's web editor) runs
`.github/workflows/pages.yml`, which validates the BibTeX, builds the site, checks links,
and publishes it to GitHub Pages. It takes about a minute; follow it in the **Actions** tab.
If a step fails (usually a typo in a `.bib` file), nothing is published and the live site stays
as it was. The error message in the failed step says which entry and field to fix.
Pull requests are built and checked but not published.

One-time setup:

1. **Settings → Pages → Build and deployment → Source: GitHub Actions.**
2. Re-run the workflow (**Actions → Build and publish site → Run workflow**). The site appears at
   `https://secretrdlab.github.io/SECRET-site/`.
3. When ready to switch the domain, set these DNS records for `secret.seg.br` (at registro.br):
   - A: `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
   - AAAA: `2606:50c0:8000::153`, `2606:50c0:8001::153`, `2606:50c0:8002::153`, `2606:50c0:8003::153`
   - `www` CNAME: `secretrdlab.github.io`
4. **Settings → Pages → Custom domain:** `secret.seg.br`, save, then run the workflow once more so
   links use the new address. Tick **Enforce HTTPS** once GitHub has issued the certificate.

To upgrade Hugo, change `HUGO_VERSION` in `.github/workflows/pages.yml` and run `make check` locally first.
