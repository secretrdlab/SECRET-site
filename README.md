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

## Hosting and Jenkins

The site is hosted on **GitHub Pages** from the `gh-pages` branch of this repository.
Nobody edits that branch by hand: Jenkins rebuilds it from `main`.

`Jenkinsfile` runs: **Setup** (downloads the pinned Hugo, creates the venv) → **Validate BibTeX** →
**Build** → **Check** (broken internal links) → **Archive** (`site.tar.gz`) →
**Deploy** (only for `main`: force-pushes the built site to `gh-pages`).

One-time setup:

1. Create a key pair: `ssh-keygen -t ed25519 -N "" -C jenkins-secret-site -f ~/.ssh/secret-site-gh`
2. In GitHub, go to **Settings → Deploy keys → Add deploy key**, paste `secret-site-gh.pub`,
   and tick **Allow write access**.
3. In Jenkins, go to **Manage Jenkins → Credentials → Add** and choose
   **SSH Username with private key**: ID `secret-site-github-key`, username `git`, private key = `secret-site-gh`.
4. Create a *Pipeline* job: *Pipeline script from SCM* → Git →
   `https://github.com/secretrdlab/SECRET-site.git`, branch `*/main`, script path `Jenkinsfile`.
   Run **Build Now** once; this creates the `gh-pages` branch.
5. In GitHub, go to **Settings → Pages**: Source *Deploy from a branch*, branch `gh-pages`, folder `/ (root)`.
6. Point the domain to GitHub, then tick **Enforce HTTPS** in Settings → Pages:
   - `secret.seg.br` A records: `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
   - `secret.seg.br` AAAA records: `2606:50c0:8000::153`, `2606:50c0:8001::153`, `2606:50c0:8002::153`, `2606:50c0:8003::153`
   - `www.secret.seg.br` CNAME: `secretrdlab.github.io`

To preview before the domain is switched, run the job with **Build with Parameters** and
`BASE_URL = https://secretrdlab.github.io/SECRET-site/`. That build writes no `CNAME`, so the site
appears at that address. Building again with the default `BASE_URL` sets the custom domain back.

Jenkins checks GitHub for new commits every 5 minutes. The agent needs `bash`, `curl`, `tar`, `git`,
`ssh` and `python3` (with `venv`), on Linux or macOS. To upgrade Hugo, change `HUGO_VERSION`
in the `Jenkinsfile` and run `make check` locally first.
