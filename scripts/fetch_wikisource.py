#!/usr/bin/env python3
"""Fetch the public-domain Wikisource transcription of Kitab al-Tawhid for the Pages build."""
import json
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

TITLE = "كتاب التوحيد الذي هو حق الله على العبيد"
API = "https://ar.wikisource.org/w/api.php?" + urllib.parse.urlencode({
    "action": "parse",
    "page": TITLE,
    "prop": "text",
    "format": "json",
    "formatversion": "2",
})

class BookText(HTMLParser):
    BLOCKS = {"p", "h1", "h2", "h3", "h4", "li", "dd", "dt", "br", "blockquote"}
    SKIP = {"script", "style", "noscript"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_content = 0
        self.skip_depth = 0
        self.skip_tags = []
        self.parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set((attrs.get("class") or "").split())
        if tag == "div" and "mw-parser-output" in classes:
            self.in_content += 1
        if not self.in_content:
            return
        if tag in self.SKIP or classes.intersection({
            "mw-editsection", "reference", "mw-references-wrap", "navbox",
            "catlinks", "printfooter", "toc", "noprint", "mw-indicators"
        }):
            self.skip_depth += 1
            self.skip_tags.append(tag)
            return
        if self.skip_depth == 0 and tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if self.skip_depth:
            if self.skip_tags and self.skip_tags[-1] == tag:
                self.skip_tags.pop()
                self.skip_depth -= 1
            return
        if self.in_content and tag in self.BLOCKS:
            self.parts.append("\n")
        if tag == "div" and self.in_content:
            self.in_content -= 1

    def handle_data(self, data):
        if self.in_content and not self.skip_depth:
            self.parts.append(data)

def main():
    request = urllib.request.Request(API, headers={
        "User-Agent": "AlMaktabaAlIlmiyya/1.0 (educational text import)"
    })
    with urllib.request.urlopen(request, timeout=45) as response:
        payload = json.loads(response.read().decode("utf-8"))
    html = payload.get("parse", {}).get("text", "")
    if not html:
        raise RuntimeError("Wikisource API returned no parsed book text")
    parser = BookText()
    parser.feed(html)
    raw = "".join(parser.parts)
    lines = [re.sub(r"\\s+", " ", line).strip() for line in raw.splitlines()]
    lines = [line for line in lines if line]
    text = "\n\n".join(lines)
    if len(text) < 15000 or "باب فضل التوحيد" not in text:
        raise RuntimeError("Fetched text appears incomplete; refusing to publish a partial book")
    header = (
        "# كتاب التوحيد الذي هو حق الله على العبيد\n\n"
        "المؤلف: محمد بن عبد الوهاب رحمه الله.\n"
        "مصدر التفريغ: ويكي مصدر، والصفحة تصنف النص ضمن الملكية العامة.\n"
        "تنبيه: هذه طبعة نصية رقمية، وتحتاج مقابلة نهائية على النسخة المصورة قبل اعتمادها للتحقيق العلمي.\n"
        "المصدر: https://ar.wikisource.org/wiki/كتاب_التوحيد_الذي_هو_حق_الله_على_العبيد\n\n"
        "---\n\n"
    )
    output = Path("texts/kitab-al-tawhid.md")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(header + text + "\n", encoding="utf-8")
    print(f"Fetched {len(text)} characters into {output}")

if __name__ == "__main__":
    main()
