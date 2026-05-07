#!/usr/bin/env python3
"""Post-process pandoc-generated .docx for client-ready output.

Fixes:
- Strip internal .md hyperlinks (become plain text)
- Page break after Table of Contents
- Page break before each Heading 1 section
- Table column widths (proportional, first column wider)
- Table font size (9pt for readability)
- Tables don't break across pages (rows kept together)
- Header rows repeat on every page
- Header rows shaded + bold
- Heading spacing (better margins between sections)
- Cover page with logo, title, subtitle
- Footer with logomark on every page
"""

import argparse
import os
import sys
import copy
from xml.sax.saxutils import escape as xml_escape
import yaml
from docx import Document
from docx.shared import Pt, Inches, Emu, RGBColor
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml
from docx.enum.text import WD_ALIGN_PARAGRAPH


# 1 inch = 1440 twips
TWIPS_PER_INCH = 1440


def inches_to_twips(inches):
    return int(inches * TWIPS_PER_INCH)


class _PermissiveLoader(yaml.SafeLoader):
    """YAML loader that ignores unknown tags (e.g. !!python/name:...)."""
    pass

_PermissiveLoader.add_multi_constructor("", lambda loader, suffix, node: None)


def read_mkdocs_config(mkdocs_path):
    """Read mkdocs.yml and extract site_name and site_description."""
    if not os.path.exists(mkdocs_path):
        return None, None
    with open(mkdocs_path, "r", encoding="utf-8") as f:
        config = yaml.load(f, Loader=_PermissiveLoader)
    site_name = config.get("site_name", "")
    site_description = config.get("site_description", "")
    return site_name, site_description


def build_cover_page(doc, logo_path, title, subtitle):
    """Insert a branded cover page at the very beginning of the document."""
    title = xml_escape(title)
    subtitle = xml_escape(subtitle)
    body = doc.element.body
    insert_idx = 0

    def insert_elem(elem):
        nonlocal insert_idx
        body.insert(insert_idx, elem)
        insert_idx += 1

    def make_empty_para():
        return parse_xml(f'<w:p {nsdecls("w")}><w:pPr><w:jc w:val="center"/></w:pPr></w:p>')

    # ~6 empty paragraphs for vertical spacing
    for _ in range(6):
        insert_elem(make_empty_para())

    # Logo paragraph
    if logo_path and os.path.exists(logo_path):
        logo_para = parse_xml(
            f'<w:p {nsdecls("w")}>'
            '<w:pPr><w:jc w:val="center"/></w:pPr>'
            '</w:p>'
        )
        insert_elem(logo_para)

        # Build a temporary paragraph using python-docx API to get the image run XML,
        # then transplant it into the inserted paragraph
        tmp_para = doc.add_paragraph()
        tmp_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = tmp_para.add_run()
        run.add_picture(logo_path, width=Inches(4.36))
        # Move the run element into the cover logo paragraph
        for r_elem in list(tmp_para._p):
            logo_para.append(r_elem)
        # Remove the temporary paragraph from the end of the document
        tmp_para._p.getparent().remove(tmp_para._p)
    else:
        if logo_path:
            print(f"Warning: Cover logo not found: {logo_path}")
        insert_elem(make_empty_para())

    # Empty spacing paragraph
    insert_elem(make_empty_para())

    # Title paragraph: centered, 26pt, color #0F4761, bold
    title_xml = (
        f'<w:p {nsdecls("w")}>'
        '<w:pPr><w:jc w:val="center"/></w:pPr>'
        '<w:r>'
        '<w:rPr>'
        '<w:b/>'
        '<w:color w:val="0F4761"/>'
        '<w:sz w:val="52"/>'
        '<w:szCs w:val="52"/>'
        '</w:rPr>'
        f'<w:t>{title}</w:t>'
        '</w:r>'
        '</w:p>'
    )
    insert_elem(parse_xml(title_xml))

    # Subtitle paragraph: centered, 20pt, color #0F4761
    subtitle_xml = (
        f'<w:p {nsdecls("w")}>'
        '<w:pPr><w:jc w:val="center"/></w:pPr>'
        '<w:r>'
        '<w:rPr>'
        '<w:color w:val="0F4761"/>'
        '<w:sz w:val="40"/>'
        '<w:szCs w:val="40"/>'
        '</w:rPr>'
        f'<w:t>{subtitle}</w:t>'
        '</w:r>'
        '</w:p>'
    )
    insert_elem(parse_xml(subtitle_xml))

    # More empty paragraphs for vertical spacing
    for _ in range(4):
        insert_elem(make_empty_para())

    # Page break paragraph
    page_break_xml = (
        f'<w:p {nsdecls("w")}>'
        '<w:r>'
        '<w:br w:type="page"/>'
        '</w:r>'
        '</w:p>'
    )
    insert_elem(parse_xml(page_break_xml))


def add_footer_logo(doc, logo_path):
    """Add logomark PNG to footer of every page, right-aligned, 0.41"x0.41"."""
    if not os.path.exists(logo_path):
        print(f"Warning: Footer logo not found: {logo_path}")
        return

    width_emu = int(Inches(0.41))
    height_emu = int(Inches(0.41))

    for section in doc.sections:
        footer = section.footer
        footer.is_linked_to_previous = False

        # Clear existing footer content
        for p in list(footer.paragraphs):
            p._p.getparent().remove(p._p)

        # Add image paragraph via footer part
        paragraph = footer.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT

        # Add image relationship to footer part
        rId, image_part = footer.part.get_or_add_image(logo_path)

        inline_xml = (
            f'<wp:inline {nsdecls("wp", "r", "a", "pic")} '
            f'distT="0" distB="0" distL="0" distR="0">'
            f'  <wp:extent cx="{width_emu}" cy="{height_emu}"/>'
            f'  <wp:docPr id="1" name="Footer Logo"/>'
            f'  <a:graphic>'
            f'    <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'      <pic:pic>'
            f'        <pic:nvPicPr>'
            f'          <pic:cNvPr id="0" name="logo.png"/>'
            f'          <pic:cNvPicPr/>'
            f'        </pic:nvPicPr>'
            f'        <pic:blipFill>'
            f'          <a:blip r:embed="{rId}"/>'
            f'          <a:stretch><a:fillRect/></a:stretch>'
            f'        </pic:blipFill>'
            f'        <pic:spPr>'
            f'          <a:xfrm>'
            f'            <a:off x="0" y="0"/>'
            f'            <a:ext cx="{width_emu}" cy="{height_emu}"/>'
            f'          </a:xfrm>'
            f'          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
            f'        </pic:spPr>'
            f'      </pic:pic>'
            f'    </a:graphicData>'
            f'  </a:graphic>'
            f'</wp:inline>'
        )

        drawing = parse_xml(f'<w:drawing {nsdecls("w")}>{inline_xml}</w:drawing>')
        run = paragraph.add_run()
        run._r.append(drawing)


def strip_internal_hyperlinks(doc):
    """Convert internal .md hyperlinks to plain text, preserving formatting.

    In docx XML, a hyperlink looks like:
      <w:hyperlink r:id="rIdNN">
        <w:r><w:rPr>...</w:rPr><w:t>link text</w:t></w:r>
      </w:hyperlink>

    We replace the hyperlink element with its child runs directly in the
    parent paragraph, so the visible text stays but is no longer clickable.
    """
    body = doc.element.body

    for hyperlink in body.iter(qn("w:hyperlink")):
        parent = hyperlink.getparent()
        if parent is None:
            continue

        # Check if this is an internal link (to .md file) via relationship
        r_id = hyperlink.get(qn("r:id"))
        is_internal = False

        if r_id:
            for rel in doc.part.rels.values():
                if rel.rId == r_id:
                    target = rel.target_ref or ""
                    if target.endswith(".md") or ".md#" in target:
                        is_internal = True
                    break
        else:
            # Anchor-only links (w:anchor) are also internal
            is_internal = True

        if not is_internal:
            continue

        # Extract child runs and insert them before the hyperlink
        idx = list(parent).index(hyperlink)
        runs = list(hyperlink)
        for i, run in enumerate(runs):
            # Remove hyperlink styling (blue/underline) from runs
            rPr = run.find(qn("w:rPr"))
            if rPr is not None:
                for c in rPr.findall(qn("w:color")):
                    rPr.remove(c)
                for u in rPr.findall(qn("w:u")):
                    rPr.remove(u)
                for rs in rPr.findall(qn("w:rStyle")):
                    if rs.get(qn("w:val")) == "Hyperlink":
                        rPr.remove(rs)
            parent.insert(idx + i, run)

        parent.remove(hyperlink)


def add_page_break_after_toc(doc):
    """Insert a page break after the Table of Contents.

    Pandoc generates the TOC as a Structured Document Tag (SDT) element,
    not as regular paragraphs with TOC styles. We find the SDT and add
    a page break after it. Falls back to searching for TOC-styled
    paragraphs if no SDT is found.
    """
    body = doc.element.body
    page_break_p = parse_xml(
        f'<w:p {nsdecls("w")}>'
        '  <w:r>'
        '    <w:br w:type="page"/>'
        '  </w:r>'
        '</w:p>'
    )

    for elem in body:
        if elem.tag == qn("w:sdt"):
            elem.addnext(page_break_p)
            return

    last_toc_elem = None
    for paragraph in doc.paragraphs:
        style_name = paragraph.style.name or ""
        if style_name.startswith("TOC") or style_name == "toc":
            last_toc_elem = paragraph._p

    if last_toc_elem is not None:
        last_toc_elem.addnext(page_break_p)


def fix_heading_spacing(doc):
    """Add spacing before/after headings for better section separation."""
    first_h1_seen = False

    for paragraph in doc.paragraphs:
        style_name = paragraph.style.name or ""

        if style_name == "Heading 1":
            pf = paragraph.paragraph_format
            pf.space_before = Pt(36)
            pf.space_after = Pt(12)
            pf.keep_with_next = True
            if first_h1_seen:
                pf.page_break_before = True
            first_h1_seen = True

        elif style_name == "Heading 2":
            pf = paragraph.paragraph_format
            pf.space_before = Pt(24)
            pf.space_after = Pt(8)
            pf.keep_with_next = True

        elif style_name == "Heading 3":
            pf = paragraph.paragraph_format
            pf.space_before = Pt(18)
            pf.space_after = Pt(6)
            pf.keep_with_next = True

        elif style_name == "Heading 4":
            pf = paragraph.paragraph_format
            pf.space_before = Pt(14)
            pf.space_after = Pt(4)
            pf.keep_with_next = True


def set_cell_width(cell, width_twips):
    """Set a cell's width in twips."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    for existing in tcPr.findall(qn("w:tcW")):
        tcPr.remove(existing)
    tcW = parse_xml(
        f'<w:tcW {nsdecls("w")} w:w="{width_twips}" w:type="dxa"/>'
    )
    tcPr.insert(0, tcW)


def set_table_font_size(table, size_pt=9):
    """Set font size for all text in a table."""
    half_pts = size_pt * 2  # Word uses half-points
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(size_pt)
                pPr = paragraph._p.get_or_add_pPr()
                rPr = pPr.find(qn("w:rPr"))
                if rPr is None:
                    rPr = parse_xml(f'<w:rPr {nsdecls("w")}></w:rPr>')
                    pPr.append(rPr)
                for existing in rPr.findall(qn("w:sz")):
                    rPr.remove(existing)
                for existing in rPr.findall(qn("w:szCs")):
                    rPr.remove(existing)
                rPr.append(parse_xml(
                    f'<w:sz {nsdecls("w")} w:val="{half_pts}"/>'
                ))
                rPr.append(parse_xml(
                    f'<w:szCs {nsdecls("w")} w:val="{half_pts}"/>'
                ))


def reduce_cell_padding(table):
    """Reduce cell margins/padding for tighter tables."""
    tbl = table._tbl
    tblPr = tbl.tblPr
    if tblPr is None:
        return

    for existing in tblPr.findall(qn("w:tblCellMar")):
        tblPr.remove(existing)

    margins = parse_xml(
        f'<w:tblCellMar {nsdecls("w")}>'
        '  <w:top w:w="30" w:type="dxa"/>'
        '  <w:left w:w="60" w:type="dxa"/>'
        '  <w:bottom w:w="30" w:type="dxa"/>'
        '  <w:right w:w="60" w:type="dxa"/>'
        '</w:tblCellMar>'
    )
    tblPr.append(margins)


def fix_table_column_widths(table):
    """Distribute column widths proportionally. Units: twips."""
    num_cols = len(table.columns)
    if num_cols == 0:
        return

    # Page width: 6.5" usable (letter 8.5" minus 1" margins each side)
    total = inches_to_twips(6.5)

    if num_cols == 5:
        widths = [
            inches_to_twips(0.6),
            inches_to_twips(2.5),
            inches_to_twips(1.0),
            inches_to_twips(1.0),
            total - inches_to_twips(0.6 + 2.5 + 1.0 + 1.0),
        ]
    elif num_cols == 4:
        widths = [
            inches_to_twips(2.0),
            inches_to_twips(1.5),
            inches_to_twips(1.5),
            total - inches_to_twips(2.0 + 1.5 + 1.5),
        ]
    elif num_cols == 3:
        widths = [
            inches_to_twips(1.5),
            inches_to_twips(1.5),
            total - inches_to_twips(3.0),
        ]
    elif num_cols == 2:
        widths = [inches_to_twips(2.0), total - inches_to_twips(2.0)]
    else:
        per_col = total // num_cols
        widths = [per_col] * num_cols

    tbl = table._tbl
    tblPr = tbl.tblPr
    if tblPr is not None:
        for existing in tblPr.findall(qn("w:tblLayout")):
            tblPr.remove(existing)
        tblPr.append(parse_xml(
            f'<w:tblLayout {nsdecls("w")} w:type="fixed"/>'
        ))

    tblGrid = tbl.find(qn("w:tblGrid"))
    if tblGrid is not None:
        grid_cols = tblGrid.findall(qn("w:gridCol"))
        for i, gc in enumerate(grid_cols):
            if i < len(widths):
                gc.set(qn("w:w"), str(widths[i]))

    for row in table.rows:
        for i, cell in enumerate(row.cells):
            if i < len(widths):
                set_cell_width(cell, widths[i])


def fix_table_rows(table):
    """Prevent rows from splitting across pages."""
    for row in table.rows:
        trPr = row._tr.get_or_add_trPr()
        for existing in trPr.findall(qn("w:cantSplit")):
            trPr.remove(existing)
        trPr.append(parse_xml(
            f'<w:cantSplit {nsdecls("w")} w:val="true"/>'
        ))


def fix_table_header_repeat(table):
    """Make header row repeat on every page."""
    if len(table.rows) < 2:
        return
    trPr = table.rows[0]._tr.get_or_add_trPr()
    for existing in trPr.findall(qn("w:tblHeader")):
        trPr.remove(existing)
    trPr.append(parse_xml(
        f'<w:tblHeader {nsdecls("w")} w:val="true"/>'
    ))


def fix_table_borders(table):
    """Clean grey borders."""
    tblPr = table._tbl.tblPr
    if tblPr is None:
        return
    for existing in tblPr.findall(qn("w:tblBorders")):
        tblPr.remove(existing)
    tblPr.append(parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        '  <w:top w:val="single" w:sz="4" w:space="0" w:color="999999"/>'
        '  <w:left w:val="single" w:sz="4" w:space="0" w:color="999999"/>'
        '  <w:bottom w:val="single" w:sz="4" w:space="0" w:color="999999"/>'
        '  <w:right w:val="single" w:sz="4" w:space="0" w:color="999999"/>'
        '  <w:insideH w:val="single" w:sz="4" w:space="0" w:color="CCCCCC"/>'
        '  <w:insideV w:val="single" w:sz="4" w:space="0" w:color="CCCCCC"/>'
        '</w:tblBorders>'
    ))


def shade_header_row(table):
    """Light grey background + bold on header row."""
    if len(table.rows) < 1:
        return
    for cell in table.rows[0].cells:
        tcPr = cell._tc.get_or_add_tcPr()
        for existing in tcPr.findall(qn("w:shd")):
            tcPr.remove(existing)
        tcPr.append(parse_xml(
            f'<w:shd {nsdecls("w")} w:fill="E8E8E8" w:val="clear"/>'
        ))
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.bold = True


def postprocess(filepath, logo_path=None, footer_logo_path=None, mkdocs_path=None,
                title_override=None, subtitle_override=None):
    """Apply all fixes to the docx file."""
    doc = Document(filepath)

    # Cover page (built only if we have any source for title/logo)
    if logo_path or mkdocs_path or title_override:
        title = "Documentation"
        subtitle = ""
        if mkdocs_path:
            site_name, site_description = read_mkdocs_config(mkdocs_path)
            if site_name:
                title = site_name
            if site_description:
                subtitle = site_description
        if title_override:
            title = title_override
        if subtitle_override:
            subtitle = subtitle_override
        build_cover_page(doc, logo_path, title, subtitle)

    # Footer logo
    if footer_logo_path:
        add_footer_logo(doc, footer_logo_path)

    # Strip broken .md hyperlinks → plain text
    strip_internal_hyperlinks(doc)

    # Page break after TOC
    add_page_break_after_toc(doc)

    # Heading spacing and section page breaks
    fix_heading_spacing(doc)

    # Fix all tables
    for table in doc.tables:
        fix_table_column_widths(table)
        fix_table_rows(table)
        fix_table_header_repeat(table)
        fix_table_borders(table)
        shade_header_row(table)
        set_table_font_size(table, size_pt=9)
        reduce_cell_padding(table)

    doc.save(filepath)
    print(f"Post-processed: {filepath}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Post-process pandoc-generated .docx for client-ready output."
    )
    parser.add_argument("file", help="Path to the .docx file to post-process")
    parser.add_argument("--logo", help="Path to combination logo PNG for cover page", default=None)
    parser.add_argument("--footer-logo", help="Path to logomark PNG for footer", default=None)
    parser.add_argument("--mkdocs", help="Path to mkdocs.yml for title/subtitle", default=None)
    parser.add_argument("--title", help="Override cover page title", default=None)
    parser.add_argument("--subtitle", help="Override cover page subtitle", default=None)
    args = parser.parse_args()

    postprocess(
        args.file,
        logo_path=args.logo,
        footer_logo_path=args.footer_logo,
        mkdocs_path=args.mkdocs,
        title_override=args.title,
        subtitle_override=args.subtitle,
    )
