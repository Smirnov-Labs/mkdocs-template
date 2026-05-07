#!/usr/bin/env bash
set -euo pipefail

# Export docs to PDF using mkdocs-print-site-plugin
#
# Usage:
#   ./export-pdf.sh              # Full site PDF instructions
#   ./export-pdf.sh SECTION      # Section-specific PDF instructions
#
# The print-site plugin creates a /print_page/ endpoint that renders
# all pages in a single printable view. Use browser's Print → Save as PDF.

SECTION="${1:-}"

echo "=== Product Documentation PDF Export ==="
echo ""

if [ -n "$SECTION" ]; then
    echo "To export the '$SECTION' section:"
    echo "  1. Run: cd docs && make serve"
    echo "  2. Open: http://localhost:8000/$SECTION/"
    echo "  3. Use browser: File → Print → Save as PDF"
    echo ""
    echo "Tip: Use browser print settings to remove headers/footers"
else
    echo "To export the full documentation:"
    echo "  1. Run: cd docs && make serve"
    echo "  2. Open: http://localhost:8000/print_page/"
    echo "  3. Use browser: File → Print → Save as PDF"
    echo ""
    echo "To export a specific section:"
    echo "  ./export-pdf.sh functional-specification"
    echo "  ./export-pdf.sh user-journey-planning"
    echo "  ./export-pdf.sh technical-specification"
fi

echo ""
echo "Starting MkDocs server..."
cd "$(dirname "$0")/.."
mkdocs serve -f mkdocs.yml
