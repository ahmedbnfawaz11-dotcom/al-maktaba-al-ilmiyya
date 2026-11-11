#!/usr/bin/env python3
"""Fetch a public-domain work by Muhammad ibn Abd al-Wahhab from Wikisource."""
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

TITLE = sys.argv[1] if len(sys.argv) > 1 else "كتاب التوحيد الذي هو حق الله على العبيد"

API = "https://ar.wikisource.org/w/api.php?" + urllib.parse.urlencode({
    "action": "parse", "page": TITLE, "prop": "text",
    "format": "json", "formatversion": "2",
})

class BookText(HTMLParser):
    BLOCKS = {"p", "h1", "h2", "h3", "h4", "li", "dd", "dt", "br", "blockquote"}
    SKIP = {"script", "style", "noscript"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.active = False
        self.div_depth = 0
        self.skip_tags = []
        self.parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set((attrs.get("class") or "").split())
        if not self.active:
            if tag == "div" and "mw-parser-output" in classes:
                self.active = True
                self.div_depth = 1
            return
        if self.skip_tags:
            self.skip_tags.append(tag)
            return
        if tag in self.SKIP or classes.intersection({
            "mw-editsection", "reference", "mw-references-wrap", "navbox",
            "catlinks", "printfooter", "toc", "noprint", "mw-indicators"
        }):
            self.skip_tags.append(tag)
            return
        if tag == "div":
            self.div_depth += 1
        if tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if self.skip_tags:
            if tag in self.skip_tags:
                index = len(self.skip_tags) - 1 - self.skip_tags[::-1].index(tag)
                self.skip_tags = self.skip_tags[:index]
            return
        if not self.active:
            return
        if tag in self.BLOCKS:
            self.parts.append("\n")
        if tag == "div":
            self.div_depth -= 1
            if self.div_depth <= 0:
                self.active = False

    def handle_data(self, data):
        if self.active and not self.skip_tags:
            self.parts.append(data)

def main():
    request = urllib.request.Request(API, headers={
        "User-Agent": "AlMaktabaAlIlmiyya/1.0 (educational text import)"
    })
    payload = None
    for attempt in range(6):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt == 5:
                raise
            time.sleep(2 ** (attempt + 1))
    time.sleep(1)
    html = payload.get("parse", {}).get("text", "")
    if not html:
        raise RuntimeError("Wikisource API returned no parsed text")
    parser = BookText()
    parser.feed(html)
    raw = "".join(parser.parts)
    lines = [re.sub(r"\s+", " ", line).strip() for line in raw.splitlines()]
    text = "\n\n".join(line for line in lines if line)
    minimum = 15000 if TITLE == "كتاب التوحيد الذي هو حق الله على العبيد" else 2500
    if len(text) < minimum:
        raise RuntimeError("Fetched text appears incomplete; refusing to publish partial book")
    if TITLE == "كتاب التوحيد الذي هو حق الله على العبيد" and "باب فضل التوحيد" not in text:
        raise RuntimeError("Fetched Kitab al-Tawhid is missing a required chapter")
    source_url = "https://ar.wikisource.org/wiki/" + urllib.parse.quote(TITLE.replace(" ", "_"))
    header = (
        "# " + TITLE + "\n\n"
        "المؤلف: محمد بن عبد الوهاب رحمه الله.\n"
        "مصدر التفريغ: ويكي مصدر؛ والنص منسوب للمؤلف في فهرس المؤلفات.\n"
        "تنبيه: هذه طبعة نصية رقمية تحتاج مقابلة على النسخة المصورة قبل اعتمادها للتحقيق العلمي.\n"
        "المصدر: " + source_url + "\n\n---\n\n"
    )
    slug = (
        "mufid-al-mustafid" if "مفيد المستفيد" in TITLE else
        "adab-al-mashy" if TITLE == "آداب المشي إلى الصلاة" else
        "arba-qawaid" if TITLE == "أربع قواعد تدور الأحكام عليها" else
        "radd-al-rawafid" if TITLE == "رسالة الرد على الرافضة" else
        "mabahith-al-ijtihad" if TITLE == "مبحث الاجتهاد والخلاف" else
        "mukhtasar-sirat-al-rasul" if TITLE == "مختصر سيرة الرسول صلى الله عليه وسلم" else
        "aqidat-al-firqa-al-najiya" if TITLE == "عقيدة الفرقة الناجية أهل السنة والجماعة" else
        "kitab-al-kabair" if TITLE == "كتاب الكبائر لمحمد بن عبد الوهاب" else
        "kitab-al-tawhid" if TITLE == "كتاب التوحيد الذي هو حق الله على العبيد" else
        "kashf-al-shubuhat" if TITLE == "كشف الشبهات" else
        "fadl-al-islam" if TITLE == "فضل الإسلام" else
        "usul-al-iman" if TITLE == "كتاب أصول الإيمان" else
        "masail-al-jahiliyyah" if TITLE == "مسائل الجاهلية" else
        None
    )
    if not slug:
        raise RuntimeError("No unique output slug configured for this title")
    output = Path("texts/" + slug + ".md")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(header + text + "\n", encoding="utf-8")
    print(f"Fetched {len(text)} characters into {output}")

if __name__ == "__main__":
    main()
