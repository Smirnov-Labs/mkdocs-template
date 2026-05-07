# mkdocs-template

A reusable MkDocs Material scaffold for project documentation, with scripts for serving locally, building a static site, and exporting to PDF / DOCX.

## What's inside

```
.
├── Makefile                 # install / serve / build / pdf / docx / clean
├── requirements.txt         # mkdocs + plugins + python-docx + cairosvg
├── mkdocs.yml               # Material theme, plugins, extensions, nav skeleton
├── .gitignore
├── .gitlab-ci.yml.example   # Optional: GitLab Pages deploy
├── scripts/
│   ├── export-pdf.sh        # Print-to-PDF helper (uses mkdocs-print-site-plugin)
│   ├── export-docx.sh       # Pandoc-based DOCX export with cover/footer
│   ├── nav-resolve.py       # Resolves mkdocs.yml nav selectors to file lists
│   └── postprocess-docx.py  # python-docx post-processor (tables, TOC, headings)
├── templates/
│   └── reference.docx       # Pandoc reference style for DOCX output
└── content/
    ├── index.md
    ├── assets/              # Logos, favicon, images referenced in mkdocs.yml
    ├── data/                # Brand assets for DOCX export (see below)
    ├── stylesheets/extra.css
    ├── functional-specification/index.md
    ├── user-journey-planning/index.md
    ├── technical-specification/index.md
    └── project-management/index.md
```

## Importing into a new repo

The simplest path is to copy this directory into your repo as `docs/`:

```bash
cp -r /path/to/mkdocs-template /path/to/your-repo/docs
cd /path/to/your-repo/docs
make install
make serve
```

## What to customize

After importing, edit these:

1. **`mkdocs.yml`** — set `site_name`, `site_description`, `site_author`, `repo_name`, `repo_url`. Adjust the `nav` tree as content grows.
2. **`content/index.md`** — replace placeholder with a real overview of the project.
3. **`content/stylesheets/extra.css`** — adjust the `--md-primary-fg-color` palette to match your brand.
4. **`content/assets/`** — drop in `logo.svg` / favicon, then uncomment the `theme.logo` and `theme.favicon` lines in `mkdocs.yml`.
5. **`content/data/`** *(optional, for DOCX export)*:
   - `cover-logo.png` — appears on the cover page (~256×256 PNG works well)
   - `footer-logo.svg` *or* `footer-logo.png` — appears in the page footer
   - All optional. Missing files are skipped silently.
6. **`.gitlab-ci.yml.example`** — rename to `.gitlab-ci.yml` if deploying to GitLab Pages, or delete.

## Daily commands

| Command | What it does |
|---------|--------------|
| `make install` | Create `.venv` and install `requirements.txt` |
| `make serve` | Serve on `http://localhost:8000` (auto-picks next free port) |
| `make build` | Build static site into `site/` |
| `make pdf` | Serve and print `/print_page/` to PDF via browser |
| `make pdf-section SECTION=user-journey-planning` | Same, but for one section |
| `make docx` | Export full docs to `exports/full-documentation.docx` |
| `make docx SECTION="Technical Specification"` | Export one section by nav label |
| `make docx-list` | List nav nodes available as DOCX selectors |
| `make clean` | Remove `site/`, `exports/`, `.venv/` |

## Requirements

- **Python 3.10+** for the venv
- **pandoc** for `make docx` (`brew install pandoc` / `apt install pandoc`)
- A modern browser for PDF export (uses browser's print-to-PDF)
