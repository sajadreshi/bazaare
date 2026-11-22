"""Keep only simple formatting in rich text (paragraphs, bold, italic, lists, headings, links).

Descriptions come from the admin's small editor; anything else (scripts, styles, links,
attributes) is dropped so the shop can show the HTML as is.
"""

import re
from html import escape
from html.parser import HTMLParser

TAG = re.compile(r"</?[a-zA-Z]")

ALLOWED = {"p", "br", "strong", "b", "em", "i", "ul", "ol", "li", "h2", "h3", "a"}
SAFE_LINK = re.compile(r"^(https?://|mailto:|/|#)", re.IGNORECASE)
RENAME = {"b": "strong", "i": "em", "div": "p"}
VOID = {"br"}
DROP_CONTENT = {"script", "style", "template", "iframe", "object"}


class _Cleaner(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.open = []
        self.skipping = 0

    def handle_starttag(self, tag, attrs):
        if tag in DROP_CONTENT:
            self.skipping += 1
            return
        tag = RENAME.get(tag, tag)
        if self.skipping or tag not in ALLOWED:
            return
        if tag in ("li", "p") and self.open and self.open[-1] == tag:
            self.out.append(f"</{self.open.pop()}>")  # an <li> or <p> ends where the next one starts
        if tag == "a":
            href = (dict(attrs).get("href") or "").strip()
            if not SAFE_LINK.match(href):
                return  # links only to web pages, email addresses or this site
            external = href.lower().startswith("http")
            extra = ' target="_blank" rel="noopener"' if external else ""
            self.out.append(f'<a href="{escape(href, quote=True)}"{extra}>')
            self.open.append("a")
            return
        self.out.append(f"<{tag}>")
        if tag not in VOID:
            self.open.append(tag)

    def handle_startendtag(self, tag, attrs):
        if not self.skipping and RENAME.get(tag, tag) == "br":
            self.out.append("<br>")

    def handle_endtag(self, tag):
        if tag in DROP_CONTENT:
            self.skipping = max(0, self.skipping - 1)
            return
        tag = RENAME.get(tag, tag)
        if self.skipping or tag not in self.open:
            return
        while self.open:
            last = self.open.pop()
            self.out.append(f"</{last}>")
            if last == tag:
                break

    def handle_data(self, data):
        if not self.skipping:
            self.out.append(escape(data, quote=False))

    def result(self):
        while self.open:
            self.out.append(f"</{self.open.pop()}>")
        return "".join(self.out)


def clean_html(text):
    """Safe HTML for a description. Plain text (no tags) becomes paragraphs."""
    text = (text or "").strip()
    if not text:
        return ""
    if not TAG.search(text):
        paragraphs = [p.strip() for p in text.replace("\r\n", "\n").split("\n\n") if p.strip()]
        return "".join(f"<p>{escape(p, quote=False).replace(chr(10), '<br>')}</p>" for p in paragraphs)
    cleaner = _Cleaner()
    cleaner.feed(text)
    cleaner.close()
    html = cleaner.result()
    for empty in ("<p></p>", "<p><br></p>", "<li></li>"):
        html = html.replace(empty, "")
    return html.strip()
