#!/bin/bash
set -euo pipefail

# Export docs to Word (.docx) using pandoc
# Files are resolved from mkdocs.yml nav via nav-resolve.py.
#
# Usage:
#   ./export-docx.sh                                  # Full documentation
#   ./export-docx.sh "Technical Specification"         # Single section (nav label)
#   ./export-docx.sh "Functional Specification,Technical Specification"  # Multi-section
#   ./export-docx.sh functional-specification          # Slug also works
#
# Optional brand assets (place in docs/data/, all optional):
#   data/cover-logo.png   — Cover page logo (PNG, ~256x256 recommended)
#   data/footer-logo.svg  — Footer logomark (will be auto-converted to PNG)
#   data/footer-logo.png  — Pre-rendered footer logo (used if .svg absent)
# When any asset is missing, the corresponding decoration is silently skipped.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DOCS_DIR="$(dirname "$SCRIPT_DIR")"
CONTENT_DIR="$DOCS_DIR/content"
EXPORTS_DIR="$DOCS_DIR/exports"
TEMPLATE="$DOCS_DIR/templates/reference.docx"
POSTPROCESS="$SCRIPT_DIR/postprocess-docx.py"
NAV_RESOLVE="$SCRIPT_DIR/nav-resolve.py"
PYTHON="$DOCS_DIR/.venv/bin/python3"

# Check pandoc is installed
if ! command -v pandoc &> /dev/null; then
    echo "Error: pandoc is not installed."
    echo "Install it with: brew install pandoc (macOS) or apt install pandoc (Linux)"
    exit 1
fi

mkdir -p "$EXPORTS_DIR"

# Brand assets — all optional, absent paths are silently skipped downstream.
COVER_LOGO="$DOCS_DIR/data/cover-logo.png"
FOOTER_LOGO_SVG="$DOCS_DIR/data/footer-logo.svg"
FOOTER_LOGO_PNG="$DOCS_DIR/data/footer-logo.png"
MKDOCS_YML="$DOCS_DIR/mkdocs.yml"

# Strip MkDocs admonitions (!!! note/info/warning) — pandoc doesn't understand them.
# Converts admonition blocks into plain bold paragraphs with dedented content.
# Works on temporary copies so source files are untouched.
TMPDIR_CLEAN="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_CLEAN"' EXIT

strip_admonitions() {
    local src="$1" dst="$2"
    mkdir -p "$(dirname "$dst")"
    "$PYTHON" -c "
import re, sys, os

src, dst = sys.argv[1], sys.argv[2]
with open(src, 'r', encoding='utf-8') as f:
    text = f.read()

# Match admonition blocks: !!! type [\"title\"] followed by indented lines
def replace_admonition(m):
    kind = m.group(1).capitalize()
    title = m.group(2).strip(' \"') if m.group(2) else kind
    body = m.group(3)
    # Dedent body (remove leading 4 spaces)
    lines = body.split('\n')
    dedented = '\n'.join(line[4:] if line.startswith('    ') else line for line in lines)
    # Bold the title as a callout prefix
    return f'**{title}:** {dedented.strip()}\n'

text = re.sub(
    r'^!!! *(\w+)(?: *(\"[^\"]*\"|\w+))? *\n((?:    .+\n?)+)',
    replace_admonition,
    text,
    flags=re.MULTILINE,
)

os.makedirs(os.path.dirname(dst), exist_ok=True)
with open(dst, 'w', encoding='utf-8') as f:
    f.write(text)
" "$src" "$dst"
}

# Convert SVG footer logo → PNG if needed (DOCX can't embed SVG).
if [ -f "$FOOTER_LOGO_SVG" ] && [ -x "$PYTHON" ]; then
    echo "Converting footer logo SVG → PNG..."
    "$PYTHON" -c "
import cairosvg
cairosvg.svg2png(url='$FOOTER_LOGO_SVG', write_to='$FOOTER_LOGO_PNG', output_width=256, output_height=256)
"
fi

SECTION="${1:-}"

TEMPLATE_FLAG=""
if [ -f "$TEMPLATE" ]; then
    TEMPLATE_FLAG="--reference-doc=$TEMPLATE"
fi

# Resolve file list and metadata from mkdocs.yml nav
if [ -n "$SECTION" ]; then
    echo "Exporting section: $SECTION"
    NAV_FILES=($("$PYTHON" "$NAV_RESOLVE" "$MKDOCS_YML" "$SECTION"))
    META_JSON=$("$PYTHON" "$NAV_RESOLVE" "$MKDOCS_YML" --meta "$SECTION")
else
    echo "Exporting full documentation..."
    NAV_FILES=($("$PYTHON" "$NAV_RESOLVE" "$MKDOCS_YML"))
    META_JSON=""
fi

if [ ${#NAV_FILES[@]} -eq 0 ]; then
    echo "Error: No files resolved for selector '$SECTION'."
    echo "Available sections:"
    "$PYTHON" "$NAV_RESOLVE" "$MKDOCS_YML" --list
    exit 1
fi

# Determine output filename
if [ -n "$META_JSON" ]; then
    OUT_NAME=$(echo "$META_JSON" | "$PYTHON" -c "import sys,json; print(json.load(sys.stdin)['filename'])")
    COVER_TITLE=$(echo "$META_JSON" | "$PYTHON" -c "import sys,json; print(json.load(sys.stdin)['title'])")
    COVER_SUBTITLE=$(echo "$META_JSON" | "$PYTHON" -c "import sys,json; print(json.load(sys.stdin)['subtitle'])")
    OUTPUT="$EXPORTS_DIR/$OUT_NAME.docx"
else
    OUTPUT="$EXPORTS_DIR/full-documentation.docx"
    COVER_TITLE=""
    COVER_SUBTITLE=""
fi

# Strip admonitions and collect files
FILES=()
for f in "${NAV_FILES[@]}"; do
    if [ -f "$CONTENT_DIR/$f" ]; then
        strip_admonitions "$CONTENT_DIR/$f" "$TMPDIR_CLEAN/$f"
        FILES+=("$TMPDIR_CLEAN/$f")
    else
        echo "Warning: $f not found, skipping"
    fi
done

if [ ${#FILES[@]} -eq 0 ]; then
    echo "Error: No content files found on disk."
    exit 1
fi

pandoc "${FILES[@]}" \
    -o "$OUTPUT" \
    $TEMPLATE_FLAG \
    --toc --toc-depth=3 \
    --from=markdown \
    --to=docx

echo "Exported: $OUTPUT"

# Post-process: fix table widths, page breaks, heading spacing, cover page, footer
if [ -f "$POSTPROCESS" ] && [ -x "$PYTHON" ]; then
    echo "Post-processing..."
    POSTPROCESS_ARGS=("$OUTPUT")
    [ -f "$COVER_LOGO" ] && POSTPROCESS_ARGS+=(--logo "$COVER_LOGO")
    [ -f "$FOOTER_LOGO_PNG" ] && POSTPROCESS_ARGS+=(--footer-logo "$FOOTER_LOGO_PNG")
    [ -f "$MKDOCS_YML" ] && POSTPROCESS_ARGS+=(--mkdocs "$MKDOCS_YML")
    [ -n "$COVER_TITLE" ] && POSTPROCESS_ARGS+=(--title "$COVER_TITLE")
    [ -n "$COVER_SUBTITLE" ] && POSTPROCESS_ARGS+=(--subtitle "$COVER_SUBTITLE")
    "$PYTHON" "$POSTPROCESS" "${POSTPROCESS_ARGS[@]}"
else
    echo "Warning: Skipping post-processing (python3 or script not found)"
fi

echo "Done."
