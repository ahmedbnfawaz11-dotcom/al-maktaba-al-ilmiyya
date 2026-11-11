#!/usr/bin/env python3
"""Fetch complete, page-by-page text from the public Shamela reader."""
import html
import re
import sys
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

BASE = "https://shamela.ws"
UA = "Mozilla/5.0 (compatible; ArabicLibraryTextImporter/1.0; educational project)"
VOID = {"area","base","br","col","embed","hr","img","input","link","meta","param","source","track","wbr"}
BLOCK = {"p","div","section","article","h1","h2","h3","h4","h5","li","ul","ol","br","tr","blockquote"}

class NassParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.active = False
        self.depth = 0
        self.skip_depth = 0
        self.parts = []
        self.last_href = None
        self.after_goto = False
        self.following_anchors = []
        self.page_value = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "input" and a.get("id") == "fld_goto_bottom":
            self.after_goto = True
            self.following_anchors = []
            self.page_value = a.get("value")
        elif self.after_goto and tag == "a":
            href = a.get("href")
            if href:
                self.following_anchors.append(href)
                if len(self.following_anchors) == 2:
                    self.last_href = self.following_anchors[1]
                    self.after_goto = False
        elif self.after_goto and tag not in {"a"}:
            # Ignore whitespace, but stop if another real element intervenes.
            if tag not in {"span"}:
                self.after_goto = False

        classes = (a.get("class") or "").split()
        if not self.active and tag == "div" and "nass" in classes:
            self.active = True
            self.depth = 1
            self.parts.append("\n")
            return
        if not self.active:
            return
        if self.skip_depth:
            if tag not in VOID:
                self.skip_depth += 1
            return
        if tag == "a" and "btn_tag" in classes:
            self.skip_depth = 1
            return
        if tag not in VOID:
            self.depth += 1
        if tag in BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if self.skip_depth:
            self.skip_depth -= 1
            return
        if not self.active or tag in VOID:
            return
        if tag in BLOCK:
            self.parts.append("\n")
        self.depth -= 1
        if self.depth <= 0:
            self.active = False

    def handle_data(self, data):
        if self.active and not self.skip_depth:
            self.parts.append(data)

def request(url):
    last = None
    for attempt in range(7):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ar,en;q=0.8"})
            with urllib.request.urlopen(req, timeout=60) as response:
                return response.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 6:
                raise
            time.sleep(min(45, 2 ** (attempt + 1)))
        except Exception as exc:
            last = exc
            if attempt == 6:
                raise
            time.sleep(min(30, 2 ** (attempt + 1)))
    raise last

def page_count(parser, raw, book_id):
    if parser.last_href:
        path = urlparse(urljoin(BASE, parser.last_href)).path.rstrip("/")
        tail = path.split("/")[-1]
        if tail.isdigit():
            return int(tail)
    # Fallback to the greatest numeric reader link for this exact book.
    found = re.findall(r'href=["\'](?:https?://shamela\.ws)?/book/' + str(book_id) + r'/(\d+)["\']', raw)
    return max([int(x) for x in found], default=1)

def clean_text(raw):
    parser = NassParser()
    parser.feed(raw)
    text = "".join(parser.parts)
    text = html.unescape(text).replace("\xa0", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip(), parser

def main():
    if len(sys.argv) != 5:
        raise SystemExit("usage: fetch_shamela.py BOOK_ID SLUG TITLE MIN_CHARS")
    book_id, slug, title, min_chars = int(sys.argv[1]), sys.argv[2], sys.argv[3], int(sys.argv[4])
    base = f"{BASE}/book/{book_id}"
    first_raw = request(base + "/1")
    first_text, first_parser = clean_text(first_raw)
    total = page_count(first_parser, first_raw, book_id)
    if total < 1 or total > 3000:
        raise RuntimeError(f"Unreasonable page count for {title}: {total}")
    chunks = []
    total_chars = 0
    for page in range(1, total + 1):
        raw = first_raw if page == 1 else request(f"{base}/{page}")
        page_text, _ = clean_text(raw)
        if len(page_text) < 20:
            raise RuntimeError(f"Missing/short page {page}/{total} for {title}")
        chunks.append(f"## صفحة الشاملة {page}\n\n{page_text}")
        total_chars += len(page_text)
        print(f"{title}: page {page}/{total}, {len(page_text)} chars")
        if page < total:
            time.sleep(0.8)
    if total_chars < min_chars:
        raise RuntimeError(f"Text too short for {title}: {total_chars} < {min_chars}")
    header = (
        f"# {title}\n\n"
        f"- المؤلف: الإمام محمد بن عبد الوهاب رحمه الله\n"
        f"- المصدر الرقمي: المكتبة الشاملة، رقم الكتاب: {book_id}\n"
        f"- رابط المصدر: {base}\n"
        f"- ملاحظة تحريرية: هذا تفريغ رقمي لصفحات المصدر، مع إبقاء الحواشي الظاهرة فيه؛ "
        f"أرقام الصفحات أدناه هي صفحات قارئ المصدر وليست ترقيمًا ورقيًا مستقلًا.\n"
        f"- يلزم عند التحقيق العلمي مقابلة النص على النسخة المصورة، ولا تُعد هذه الملاحظة شرحًا للمؤلف.\n\n---\n\n"
    )
    out = Path("texts") / f"{slug}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(header + "\n\n".join(chunks) + "\n", encoding="utf-8")
    print(f"COMPLETE: {title}: {total} pages, {total_chars} characters -> {out}")

if __name__ == "__main__":
    main()
