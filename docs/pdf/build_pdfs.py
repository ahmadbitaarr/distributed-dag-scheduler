"""Rebuild the MS3 PDFs from their Markdown sources after editing them.

    python3 -m pip install markdown          # once
    python3 docs/pdf/build_pdfs.py           # from the repository root

Needs a Chromium-family browser for printing: chromium, google-chrome or Microsoft Edge.
Writes docs/pdf/MS3-Specification.pdf, MS3-Progress-Report.pdf and MS3-Test-Matrix.pdf.
"""
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[2]
DOCS = {"MS3-Specification": "docs/specification.md",
        "MS3-Progress-Report": "docs/ms3-progress-report.md",
        "MS3-Test-Matrix": "docs/test-matrix.md"}
CSS = """
@page { size: Letter; margin: 0.9in; }
body { font-family: "Segoe UI", Calibri, Arial, sans-serif; font-size: 10.5pt; line-height: 1.38; color: #111; }
h1 { font-size: 17pt; margin: 0 0 10pt; }
h2 { font-size: 13pt; margin: 14pt 0 6pt; border-bottom: 1px solid #ccc; padding-bottom: 2pt; page-break-after: avoid; }
h3 { font-size: 11pt; margin: 10pt 0 4pt; }
p, li { margin: 4pt 0; }
blockquote { margin: 6pt 0; padding: 4pt 10pt; border-left: 3px solid #999; color: #333; background: #f6f6f6; }
code { font-family: Consolas, "Courier New", monospace; font-size: 9pt; background: #f2f2f2; padding: 0 2px; }
pre { background: #f6f6f6; padding: 6pt; font-size: 8.5pt; white-space: pre-wrap; }
table { border-collapse: collapse; margin: 6pt 0; font-size: 9pt; width: 100%; }
tr { page-break-inside: avoid; }
th, td { border: 1px solid #bbb; padding: 3pt 5pt; text-align: left; vertical-align: top; }
th { background: #eee; }
"""


def browser():
    for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable", "msedge", "microsoft-edge"):
        if shutil.which(name):
            return shutil.which(name)
    for path in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                 r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                 r"C:\Program Files\Google\Chrome\Application\chrome.exe"):
        if Path(path).exists():
            return path
    sys.exit("No Chromium-family browser found (chromium, google-chrome or msedge).")


def main():
    exe = browser()
    with tempfile.TemporaryDirectory() as tmp:
        for name, source in DOCS.items():
            text = (ROOT / source).read_text(encoding="utf-8")
            body = markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])
            title = text.splitlines()[0].lstrip("# ").strip()
            page = Path(tmp) / f"{name}.html"
            page.write_text(f"<!doctype html><html><head><meta charset='utf-8'><title>{title}</title>"
                            f"<style>{CSS}</style></head><body>{body}</body></html>", encoding="utf-8")
            out = ROOT / "docs" / "pdf" / f"{name}.pdf"
            out.unlink(missing_ok=True)
            subprocess.run([exe, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--print-to-pdf-no-header",
                            f"--print-to-pdf={out}", page.as_uri()], capture_output=True, timeout=120)
            for _ in range(30):
                if out.exists() and out.stat().st_size > 0:
                    break
                time.sleep(1)
            print(f"{out.relative_to(ROOT)}: {'ok' if out.exists() else 'FAILED'}")


if __name__ == "__main__":
    main()
