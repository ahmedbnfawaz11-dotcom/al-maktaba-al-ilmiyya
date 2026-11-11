#!/usr/bin/env python3
"""Fail the Pages build if any catalog text is missing or not cached offline."""
import re
import sys
from pathlib import Path

index = Path("index.html").read_text(encoding="utf-8")
service_worker = Path("sw.js").read_text(encoding="utf-8")

catalog_ids = re.findall(r'\{id:"([^"]+)",title:', index)
match = re.search(r'const textPath=\(\{([\s\S]*?)\}\)\[id\]', index)
if not match:
    raise SystemExit("VALIDATION ERROR: could not find the catalog text-path map")

mapping = dict(re.findall(r'(\w+):"texts/([^"]+)"', match.group(1)))
missing_ids = sorted(set(catalog_ids) - set(mapping))
if missing_ids:
    raise SystemExit("VALIDATION ERROR: catalog entries without text files: " + ", ".join(missing_ids))

offline_files = set(re.findall(r'["\']\./(texts/[^"\']+)["\']', service_worker))
missing_offline = sorted("texts/" + name for name in mapping.values()
                         if "texts/" + name not in offline_files)
if missing_offline:
    raise SystemExit("VALIDATION ERROR: text files not included in offline cache: " +
                     ", ".join(missing_offline))

for book_id, filename in sorted(mapping.items()):
    path = Path("texts") / filename
    if not path.is_file():
        raise SystemExit(f"VALIDATION ERROR: {book_id} points to missing file {path}")
    content = path.read_text(encoding="utf-8").strip()
    if len(content) < 500 or not content.startswith("# "):
        raise SystemExit(f"VALIDATION ERROR: {path} is empty, too short, or lacks a title header")

guide_match = re.search(r'const guidePath=\(\{([\s\S]*?)\}\)\[id\]', index)
if guide_match:
    guides = re.findall(r'\w+:"(texts/[^"]+)"', guide_match.group(1))
    for filename in guides:
        path = Path(filename)
        if not path.is_file() or filename not in offline_files:
            raise SystemExit(f"VALIDATION ERROR: study guide missing or not cached offline: {filename}")

print(f"VALIDATION OK: {len(catalog_ids)} catalog entries, {len(mapping)} readable text files, all included in offline cache.")
