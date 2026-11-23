# Local helpers. Jenkins runs the same steps (see Jenkinsfile).
PY := .venv/bin/python

.PHONY: setup data serve build check clean

setup:            ## create the Python venv (needs python3) — Hugo must be installed separately
	python3 -m venv .venv
	.venv/bin/pip install -q -r requirements.txt

data:             ## convert bibliography/*.bib into data/generated/*.json
	$(PY) scripts/bib2data.py

serve: data       ## live preview at http://localhost:1313 (rerun `make data` after editing .bib files)
	hugo server

build: data       ## production build into public/
	rm -rf public
	hugo --gc --minify

check: build      ## validate BibTeX and check links, like CI
	$(PY) scripts/bib2data.py --check
	$(PY) scripts/check_site.py public

clean:
	rm -rf public resources data/generated
