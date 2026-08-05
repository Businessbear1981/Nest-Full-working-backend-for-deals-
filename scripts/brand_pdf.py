"""
Brand a markdown document and print it to PDF in one step.

    python scripts/brand_pdf.py docs/FOO.md
    python scripts/brand_pdf.py docs/FOO.md --audience client
    python scripts/brand_pdf.py docs/*.md --outdir "C:/Users/Sean Gilmore/Desktop"

Defaults to Sean's real desktop -- NOT the OneDrive one, which holds older
drafts under the same filenames.

Uses headless Edge/Chrome for printing. Fonts are embedded by nest_brand.py,
so the PDF renders identically to the browser with no network at print time.
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]
BRAND = REPO / "scripts" / "nest_brand.py"
DESKTOP = pathlib.Path(r"C:\Users\Sean Gilmore\Desktop")

BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def find_browser() -> str | None:
    for b in BROWSERS:
        if pathlib.Path(b).exists():
            return b
    return None


def to_pdf(browser: str, html: pathlib.Path, pdf: pathlib.Path,
           profile: pathlib.Path) -> bool:
    subprocess.run([
        browser,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        # Embedded data: fonts still need a beat to decode and lay out. Without
        # a budget the print can fire mid-layout and drop the last page.
        "--virtual-time-budget=15000",
        f"--user-data-dir={profile}",
        f"--print-to-pdf={pdf}",
        html.resolve().as_uri(),
    ], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return pdf.exists() and pdf.stat().st_size > 1024


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("sources", nargs="+", type=pathlib.Path)
    ap.add_argument("--audience", choices=["client", "internal"],
                    default="internal")
    ap.add_argument("--outdir", type=pathlib.Path, default=DESKTOP)
    ap.add_argument("--keep-html", action="store_true",
                    help="also leave the .html beside the .pdf")
    args = ap.parse_args()

    browser = find_browser()
    if not browser:
        print("No Edge or Chrome found — cannot print to PDF.", file=sys.stderr)
        return 1

    args.outdir.mkdir(parents=True, exist_ok=True)
    ok = failed = 0

    with tempfile.TemporaryDirectory() as tmp:
        profile = pathlib.Path(tmp) / "profile"
        for src in args.sources:
            if not src.exists():
                print(f"  ! missing {src}", file=sys.stderr)
                failed += 1
                continue

            html = (args.outdir / f"{src.stem}.html" if args.keep_html
                    else pathlib.Path(tmp) / f"{src.stem}.html")
            r = subprocess.run(
                [sys.executable, str(BRAND), str(src),
                 "--audience", args.audience, "--out", str(html)],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace")
            if r.returncode != 0 or not html.exists():
                print(f"  ! brand failed {src.name}", file=sys.stderr)
                if r.stderr.strip():
                    print("    " + r.stderr.strip().splitlines()[-1],
                          file=sys.stderr)
                failed += 1
                continue
            if r.stderr.strip():           # the missing-fonts warning
                print("    " + r.stderr.strip().splitlines()[-1],
                      file=sys.stderr)

            pdf = args.outdir / f"{src.stem}.pdf"
            if to_pdf(browser, html, pdf, profile):
                print(f"  + {pdf.name}  ({pdf.stat().st_size // 1024} KB)")
                ok += 1
            else:
                print(f"  ! pdf failed {src.name}", file=sys.stderr)
                failed += 1

    print(f"\n{ok} PDF{'s' if ok != 1 else ''} -> {args.outdir}")
    if failed:
        print(f"{failed} failed", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
