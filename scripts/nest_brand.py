"""
Wrap a NEST markdown document in the house brand.

Markdown carries no brand. Every document that leaves this machine and is read
by a client, a partner or a regulator should look like NEST produced it, and
hand-building each one does not scale. This applies the palette, type and
figure treatment from docs/reference/brand-and-voice.md to any .md file.

    python scripts/nest_brand.py <file.md> [--out out.html]
                                [--audience client|internal]
                                [--title "..."] [--subtitle "..."]

  client    (default) no confidence tags shown, footer carries the
            not-a-registered-placement-agent language
  internal  keeps HAND_SET / verified / NEEDS SOURCING markers visible and
            stamps the page INTERNAL

Open the result in a browser and print to PDF. A print stylesheet flips it to
light for paper.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import pathlib
import re
import sys

BRAND_CSS = """
:root{
  --void:#030A06; --forest:#0D2218; --green:#1E4A2E; --pine:#2D6B3D;
  --gold:#C4A048; --gold-hi:#E8C87A; --sage:#7A9A82; --cream:#EDE8DC;
  --serif:"Cormorant Garamond",Georgia,"Times New Roman",serif;
  --sans:"Space Grotesk",-apple-system,"Segoe UI",Roboto,sans-serif;
  --mono:"IBM Plex Mono",Consolas,"Courier New",monospace;
}
*{box-sizing:border-box}
body{margin:0;background:var(--void);color:var(--cream);font-family:var(--sans);
  font-weight:300;font-size:15.5px;line-height:1.65;-webkit-font-smoothing:antialiased}
.page{max-width:980px;margin:0 auto;padding:0 28px 96px}
header.mast{padding:52px 0 30px;border-bottom:1px solid var(--green);margin-bottom:42px}
.mark{display:flex;align-items:baseline;gap:14px;margin-bottom:26px}
.mark .n{font-family:var(--serif);font-size:36px;font-weight:600;letter-spacing:.16em;line-height:1}
.mark .rule{flex:1;height:1px;background:linear-gradient(90deg,var(--gold),transparent)}
.mark .tag{font-family:var(--mono);font-size:10.5px;letter-spacing:.22em;
  text-transform:uppercase;color:var(--gold);white-space:nowrap}
.stamp{display:inline-block;font-family:var(--mono);font-size:9.5px;letter-spacing:.18em;
  text-transform:uppercase;color:var(--void);background:var(--gold);
  padding:3px 9px;border-radius:2px;margin-bottom:16px;font-weight:500}
.doctitle{font-family:var(--serif);font-weight:400;font-size:42px;line-height:1.12;
  margin:0 0 12px;letter-spacing:-.01em}
.docsub{color:var(--sage);font-size:16px;margin:0 0 20px;font-weight:300}
.meta{display:flex;flex-wrap:wrap;gap:26px;font-family:var(--mono);font-size:11px;
  letter-spacing:.1em;text-transform:uppercase;color:var(--sage)}
.meta b{color:var(--gold);font-weight:500}

h1{font-family:var(--serif);font-weight:400;font-size:34px;margin:52px 0 8px;
  padding-top:22px;border-top:1px solid var(--green);letter-spacing:-.005em}
h2{font-family:var(--serif);font-weight:400;font-size:27px;margin:40px 0 10px}
h3{font-family:var(--sans);font-weight:600;font-size:15px;margin:30px 0 10px;letter-spacing:.01em}
h4{font-family:var(--mono);font-weight:500;font-size:11.5px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--gold);margin:26px 0 8px}
p{margin:0 0 15px}
strong{font-weight:500;color:var(--gold-hi)}
em{color:var(--sage);font-style:italic}
a{color:var(--gold);text-decoration:none;border-bottom:1px solid rgba(196,160,72,.35)}
hr{border:0;height:1px;background:var(--green);margin:38px 0}
ol,ul{margin:0 0 15px;padding-left:22px}
li{margin-bottom:8px}
li::marker{color:var(--gold)}
blockquote{margin:20px 0;padding:16px 22px;background:var(--forest);
  border-left:2px solid var(--gold);border-radius:2px;color:var(--cream)}
blockquote p:last-child{margin-bottom:0}
code{font-family:var(--mono);font-size:.9em;color:var(--gold-hi);
  background:rgba(30,74,46,.45);padding:1px 5px;border-radius:2px}
pre{background:var(--forest);border:1px solid var(--green);border-radius:3px;
  padding:18px 20px;overflow-x:auto;margin:20px 0}
pre code{background:none;padding:0;color:var(--cream)}

.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:20px 0}
table{width:100%;border-collapse:collapse;font-size:14px;min-width:520px}
th{text-align:left;font-family:var(--mono);font-size:10px;letter-spacing:.13em;
  text-transform:uppercase;color:var(--sage);font-weight:500;
  padding:0 14px 10px 0;border-bottom:1px solid var(--green)}
td{padding:11px 14px 11px 0;border-bottom:1px solid rgba(30,74,46,.5);vertical-align:top}
th.n,td.n{text-align:right;padding-right:0}
td.n{color:var(--gold);font-family:var(--mono);font-variant-numeric:tabular-nums;font-weight:500}
tbody tr:last-child td{border-bottom:none}
tr.total td{border-top:1px solid var(--gold);border-bottom:none;font-weight:500}
tr.total td.n{color:var(--gold-hi)}

/* every financial figure in mono gold, per brand */
.fig{font-family:var(--mono);color:var(--gold);font-variant-numeric:tabular-nums;font-weight:500}
.tag-hand{font-family:var(--mono);font-size:9.5px;letter-spacing:.1em;color:var(--sage);
  border:1px solid var(--green);padding:1px 6px;border-radius:2px;white-space:nowrap}
.tag-need{font-family:var(--mono);font-size:9.5px;letter-spacing:.1em;color:var(--void);
  background:var(--gold);padding:1px 6px;border-radius:2px;white-space:nowrap;font-weight:500}

footer{border-top:1px solid var(--green);margin-top:56px;padding-top:24px;
  color:var(--sage);font-size:12.5px}
footer .mono{font-family:var(--mono);font-size:10.5px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--gold);margin-bottom:12px}

@media print{
  body{background:#fff;color:#111}
  .page{max-width:100%;padding:0}
  h1,h2,h3,.mark .n,.doctitle{color:#0D2218}
  h4{color:#8A6D1F}
  .fig,td.n,strong{color:#8A6D1F}
  blockquote,pre{background:#F7F5F0;border-color:#D8D2C4}
  h1,h2,table{page-break-inside:avoid}
  .stamp{background:#8A6D1F;color:#fff}
}
@media(max-width:620px){.doctitle{font-size:30px}h1{font-size:26px}h2{font-size:22px}}
"""

# Fonts are embedded, not linked. A linked webfont makes the document render
# differently depending on where it is opened: headless Chromium does not wait
# for the fetch when printing, so every PDF fell back to Georgia and Segoe UI
# while the same HTML looked correct in a browser. Embedding makes a branded
# document self-contained -- identical on screen, in print, and when emailed.
# Regenerate with scripts/fetch_brand_fonts.py.
try:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    from assets.brand_fonts import FONT_FACE_CSS
    FONTS = f"<style>{FONT_FACE_CSS}</style>"
except ImportError:  # fonts not fetched yet -- degrade loudly, not silently
    FONTS = ""
    print("WARNING: assets/brand_fonts.py missing — output will NOT be "
          "NEST-branded. Run: python scripts/fetch_brand_fonts.py",
          file=sys.stderr)

CLIENT_FOOTER = (
    "NEST Advisors is not a registered broker-dealer or placement agent. No "
    "transaction-based compensation accrues, is earned, or is payable prior to "
    "registration becoming effective. This document is a proposal and is not an "
    "offer to sell or a solicitation of an offer to buy any security. Tax and "
    "securities matters require the opinion of bond counsel and securities "
    "counsel.")

INTERNAL_FOOTER = (
    "Internal working document. Figures are produced by running the platform "
    "engines; thresholds marked HAND_SET are judgments, not measurements. NEST "
    "currently holds zero market-derived thresholds — no closed deals, no "
    "verified EMMA filings. Items marked NEEDS SOURCING are unresolved and must "
    "not be quoted externally.")


# --------------------------------------------------------------------------
# Minimal markdown -> html. Deliberately small: it handles what NEST documents
# actually contain (headings, tables, lists, quotes, code, emphasis) and
# nothing else, rather than pulling a dependency for a formatting job.
# --------------------------------------------------------------------------

MONEY = re.compile(r"(?<![\w>])(\$[\d,]+(?:\.\d+)?(?:\s?(?:million|billion|M|B))?|"
                   r"\d+(?:\.\d+)?%|\d+(?:\.\d+)?\s?bp)(?![\w<])")


def inline(s: str) -> str:
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    # Confidence and provenance markers get a visible chip.
    s = re.sub(r"\b(HAND_SET[A-Z_]*|RULE_BASED|MARKET_DERIVED|verified|asserted|assumed)\b",
               r'<span class="tag-hand">\1</span>', s)
    s = s.replace("NEEDS SOURCING", '<span class="tag-need">NEEDS SOURCING</span>')
    # Financial figures in mono gold, but never inside an existing tag.
    parts = re.split(r"(<[^>]+>)", s)
    for i, p in enumerate(parts):
        if not p.startswith("<"):
            parts[i] = MONEY.sub(r'<span class="fig">\1</span>', p)
    return "".join(parts)


def is_numeric(cell: str) -> bool:
    t = re.sub(r"<[^>]+>", "", cell).strip()
    return bool(t) and bool(re.match(r"^[\$\-—]?[\d,.]+\s*(%|bp|M|B)?$", t))


def render_table(rows: list[str]) -> str:
    header = [c.strip() for c in rows[0].strip().strip("|").split("|")]
    body = rows[2:]
    out = ['<div class="scroll"><table><thead><tr>']
    for h in header:
        out.append(f"<th>{inline(h)}</th>")
    out.append("</tr></thead><tbody>")
    for r in body:
        cells = [c.strip() for c in r.strip().strip("|").split("|")]
        first = re.sub(r"[^a-z]", "", cells[0].lower())
        cls = ' class="total"' if first.startswith("total") else ""
        out.append(f"<tr{cls}>")
        for c in cells:
            rendered = inline(c)
            out.append(f'<td class="n">{rendered}</td>' if is_numeric(rendered)
                       else f"<td>{rendered}</td>")
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def md_to_html(md: str) -> str:
    lines = md.replace("\ufeff", "").split("\n")
    out: list[str] = []
    i = 0
    list_stack: list[str] = []

    def close_lists():
        while list_stack:
            out.append(f"</{list_stack.pop()}>")

    while i < len(lines):
        ln = lines[i]
        stripped = ln.strip()

        if stripped.startswith("```"):
            close_lists()
            i += 1
            buf = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(html.escape(lines[i]))
                i += 1
            out.append("<pre><code>" + "\n".join(buf) + "</code></pre>")
            i += 1
            continue

        if stripped.startswith("|") and i + 1 < len(lines) and \
                re.match(r"^\|[\s:\-|]+\|$", lines[i + 1].strip()):
            close_lists()
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(lines[i])
                i += 1
            out.append(render_table(block))
            continue

        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            close_lists()
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>")
            i += 1
            continue

        if re.match(r"^(---+|\*\*\*+)$", stripped):
            close_lists()
            out.append("<hr>")
            i += 1
            continue

        if stripped.startswith(">"):
            close_lists()
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip().lstrip(">").strip())
                i += 1
            out.append("<blockquote><p>" +
                       "</p><p>".join(inline(b) for b in buf if b) + "</p></blockquote>")
            continue

        m = re.match(r"^(\s*)([-*+]|\d+\.)\s+(.*)$", ln)
        if m:
            tag = "ol" if m.group(2)[0].isdigit() else "ul"
            if not list_stack or list_stack[-1] != tag:
                close_lists()
                out.append(f"<{tag}>")
                list_stack.append(tag)
            out.append(f"<li>{inline(m.group(3))}</li>")
            i += 1
            continue

        if not stripped:
            close_lists()
            i += 1
            continue

        close_lists()
        buf = [stripped]
        i += 1
        while i < len(lines) and lines[i].strip() and \
                not re.match(r"^(#{1,4}\s|\||>|```|---|\s*([-*+]|\d+\.)\s)", lines[i]):
            buf.append(lines[i].strip())
            i += 1
        out.append("<p>" + inline(" ".join(buf)) + "</p>")

    close_lists()
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", type=pathlib.Path)
    ap.add_argument("--out", type=pathlib.Path)
    ap.add_argument("--audience", choices=("client", "internal"), default="client")
    ap.add_argument("--title")
    ap.add_argument("--subtitle", default="")
    args = ap.parse_args()

    md = args.source.read_text(encoding="utf-8", errors="replace")
    lines = md.replace("\ufeff", "").split("\n")

    # Lift the first H1 as the document title, and an immediately following
    # H2/H3 as the subtitle, so they render in the masthead rather than twice.
    title = args.title
    subtitle = args.subtitle
    consumed = 0
    for idx, ln in enumerate(lines[:8]):
        m = re.match(r"^#\s+(.*)$", ln.strip())
        if m:
            title = title or m.group(1)
            consumed = idx + 1
            for j in range(idx + 1, min(idx + 4, len(lines))):
                m2 = re.match(r"^#{2,3}\s+(.*)$", lines[j].strip())
                if m2 and not subtitle:
                    subtitle = m2.group(1)
                    consumed = j + 1
                elif lines[j].strip():
                    break
            break
    body_md = "\n".join(lines[consumed:])
    title = title or args.source.stem.replace("_", " ").title()

    stamp = '<div class="stamp">Internal</div>' if args.audience == "internal" else ""
    footer = INTERNAL_FOOTER if args.audience == "internal" else CLIENT_FOOTER

    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} — NEST Advisors</title>
{FONTS}
<style>{BRAND_CSS}</style></head>
<body><div class="page">
<header class="mast">
  <div class="mark"><span class="n">NEST</span><span class="rule"></span>
  <span class="tag">Advisors</span></div>
  {stamp}
  <div class="doctitle">{html.escape(title)}</div>
  {f'<p class="docsub">{html.escape(subtitle)}</p>' if subtitle else ''}
  <div class="meta"><span>Prepared <b>{dt.date.today().strftime('%d %B %Y')}</b></span></div>
</header>
{md_to_html(body_md)}
<footer><div class="mono">NEST Advisors · Arden Edge Capital</div>
<p>{footer}</p></footer>
</div></body></html>"""

    out = args.out or args.source.with_suffix(".html")
    out.write_text(page, encoding="utf-8")
    print(f"branded -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
