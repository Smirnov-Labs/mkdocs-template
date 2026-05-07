VENV := .venv
BIN := $(VENV)/bin
PORT ?= 8000

# Find a free port starting from PORT
FREE_PORT := $(shell port=$(PORT); while lsof -ti:$$port >/dev/null 2>&1; do port=$$((port + 1)); done; echo $$port)

.PHONY: install serve build pdf pdf-section docx docx-list clean

## Install MkDocs and plugins into a local venv
install:
	python3 -m venv $(VENV)
	$(BIN)/pip install -r requirements.txt

## Serve docs locally
serve:
	@echo "Serving docs at http://localhost:$(FREE_PORT)"
	$(BIN)/mkdocs serve -f mkdocs.yml -a localhost:$(FREE_PORT)

## Build docs static site
build:
	$(BIN)/mkdocs build -f mkdocs.yml

## Export to PDF (opens print page for browser PDF export)
pdf:
	@echo "Open http://localhost:$(FREE_PORT)/print_page/ and print to PDF"
	@echo "Or use browser: File → Print → Save as PDF"
	$(BIN)/mkdocs serve -f mkdocs.yml -a localhost:$(FREE_PORT)

## Export a section to PDF (usage: make pdf-section SECTION=user-journey-planning)
pdf-section:
	@echo "Open http://localhost:$(FREE_PORT)/$(SECTION)/ and print to PDF"
	$(BIN)/mkdocs serve -f mkdocs.yml -a localhost:$(FREE_PORT)

## Export docs to Word (usage: make docx [SECTION="Technical Specification"])
docx:
	mkdir -p exports
ifdef SECTION
	bash scripts/export-docx.sh "$(SECTION)"
else
	bash scripts/export-docx.sh
endif

## List available sections for DOCX export
docx-list:
	@echo "Available sections for DOCX export:"
	@$(BIN)/python3 scripts/nav-resolve.py mkdocs.yml --list

## Remove built site, exports, and venv
clean:
	rm -rf site/ exports/ $(VENV)/
