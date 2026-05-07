#!/usr/bin/env python3
"""Resolve mkdocs.yml nav selectors to ordered file lists.

Modes:
  nav-resolve.py mkdocs.yml                          # All files in nav order
  nav-resolve.py mkdocs.yml "Technical Specification" # Files under that node
  nav-resolve.py mkdocs.yml --meta "EP02 ..."        # JSON: title, subtitle, filename
  nav-resolve.py mkdocs.yml --list                   # List selectable nav nodes
"""

import json
import re
import sys
import yaml


class _PermissiveLoader(yaml.SafeLoader):
    """YAML loader that ignores unknown tags (e.g. !!python/name:...).

    mkdocs-material uses python tags for emoji config; safe_load rejects them.
    """
    pass

_PermissiveLoader.add_multi_constructor("", lambda loader, suffix, node: None)


def parse_nav(nav, parent_labels=None):
    """Walk the nav tree, yielding (label_path, file_path) tuples."""
    if parent_labels is None:
        parent_labels = []
    for item in nav:
        if isinstance(item, str):
            yield (list(parent_labels), item)
        elif isinstance(item, dict):
            for label, value in item.items():
                path = parent_labels + [label]
                if isinstance(value, str):
                    yield (path, value)
                elif isinstance(value, list):
                    yield from parse_nav(value, path)


def slugify(text):
    """Convert label to slug for matching."""
    text = text.lower().strip()
    text = re.sub(r"[—–]", "-", text)
    text = re.sub(r"[^a-z0-9\-]", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text


def match_selector(selector, all_labels):
    """Match a selector against nav labels. Returns matching label strings.

    Priority: exact > prefix > slug > substring.
    """
    selector_lower = selector.strip().lower()
    selector_slug = slugify(selector)

    exact = [l for l in all_labels if l.lower() == selector_lower]
    if exact:
        return exact

    prefix = [l for l in all_labels if l.lower().startswith(selector_lower)]
    if prefix:
        return prefix

    slug = [l for l in all_labels if slugify(l) == selector_slug]
    if slug:
        return slug

    sub = [l for l in all_labels if selector_lower in l.lower()]
    if sub:
        return sub

    return []


def collect_nodes(entries):
    """Build a dict: label → list of (label_path, file) entries under that node."""
    nodes = {}
    for label_path, filepath in entries:
        for label in label_path:
            if label not in nodes:
                nodes[label] = []
            nodes[label].append((label_path, filepath))
    return nodes


def resolve(config, selectors_str=None):
    """Resolve selectors to ordered file list."""
    nav = config.get("nav", [])
    entries = list(parse_nav(nav))

    if not selectors_str:
        return [fp for _, fp in entries]

    nodes = collect_nodes(entries)
    all_labels = list(nodes.keys())

    selectors = [s.strip() for s in selectors_str.split(",") if s.strip()]
    result = []
    seen = set()

    for selector in selectors:
        matched_labels = match_selector(selector, all_labels)
        if not matched_labels:
            print(f"Warning: No match for selector '{selector}'", file=sys.stderr)
            continue
        label = matched_labels[0]
        for _, fp in nodes[label]:
            if fp not in seen:
                result.append(fp)
                seen.add(fp)

    return result


def meta(config, selectors_str):
    """Generate title/subtitle/filename metadata."""
    site_name = config.get("site_name", "Documentation")
    site_desc = config.get("site_description", "")
    nav = config.get("nav", [])
    entries = list(parse_nav(nav))
    nodes = collect_nodes(entries)
    all_labels = list(nodes.keys())

    selectors = [s.strip() for s in selectors_str.split(",") if s.strip()]
    matched = []
    for selector in selectors:
        labels = match_selector(selector, all_labels)
        if labels:
            matched.append(labels[0])

    if not matched:
        return {"title": site_name, "subtitle": site_desc, "filename": "full-documentation"}

    if len(matched) == 1:
        title = matched[0]
        subtitle = site_name
        filename = slugify(matched[0])
    else:
        title = site_name
        subtitle = " + ".join(matched)
        filename = "-".join(slugify(m) for m in matched)

    return {"title": title, "subtitle": subtitle, "filename": filename}


def list_nodes(config):
    """List all selectable nav nodes with their file counts."""
    nav = config.get("nav", [])
    entries = list(parse_nav(nav))
    nodes = collect_nodes(entries)

    for label in nodes:
        seen = set()
        unique = []
        for lp, fp in nodes[label]:
            if fp not in seen:
                unique.append((lp, fp))
                seen.add(fp)
        nodes[label] = unique

    seen_labels = []
    for label_path, _ in entries:
        for label in label_path:
            if label not in seen_labels:
                seen_labels.append(label)

    for label in seen_labels:
        count = len(nodes[label])
        print(f"  {label}  ({count} file{'s' if count != 1 else ''})")


def main():
    if len(sys.argv) < 2:
        print("Usage: nav-resolve.py <mkdocs.yml> [selector] [--list] [--meta selector]", file=sys.stderr)
        sys.exit(1)

    mkdocs_path = sys.argv[1]
    with open(mkdocs_path, "r", encoding="utf-8") as f:
        config = yaml.load(f, Loader=_PermissiveLoader)

    args = sys.argv[2:]

    if "--list" in args:
        list_nodes(config)
        return

    if "--meta" in args:
        idx = args.index("--meta")
        selector = args[idx + 1] if idx + 1 < len(args) else ""
        print(json.dumps(meta(config, selector)))
        return

    selector = args[0] if args else None
    files = resolve(config, selector)
    for f in files:
        print(f)


if __name__ == "__main__":
    main()
