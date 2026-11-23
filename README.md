# SECRET website

Source of <https://secret.seg.br> — SECurity & Reverse Engineering Team, UFPR.

Plain [Hugo](https://gohugo.io) with a small built-in theme (no Hugo Blox, no Go modules), YAML data files,
and **BibTeX as the single source of truth for publications**. Jenkins validates, builds and deploys every push.

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
make check      # same validation + link check as Jenkins
```

## Jenkins

`Jenkinsfile` runs: **Setup** (downloads the pinned Hugo, creates the venv) → **Validate BibTeX** →
**Build** → **Check** (broken internal links) → **Archive** (`site.tar.gz`) → **Deploy** (only on `main`).

One-time setup:

1. Create a *Pipeline* (or *Multibranch Pipeline*) job pointing at this repository, script path `Jenkinsfile`.
2. Add a credential of type **SSH Username with private key**, ID `secret-site-deploy-key`,
   whose public key is in `~/.ssh/authorized_keys` of the deploy user on the web server.
3. Edit `DEPLOY_HOST`, `DEPLOY_USER` and `DEPLOY_PATH` at the top of the `Jenkinsfile`.
4. Optional: add a webhook from the Git server to Jenkins so builds start instantly
   (otherwise Jenkins polls every 5 minutes).

The agent needs `bash`, `curl`, `tar`, `python3` (with `venv`), `rsync` and `ssh`.
To upgrade Hugo, change `HUGO_VERSION` in the `Jenkinsfile` and run `make check` locally first.
