#!/usr/bin/env python3
import argparse
import base64
import os
import re
import subprocess
import tempfile
from typing import List, Optional

import markdown


def guess_chrome_path() -> List[str]:
    """
    Attempt to detect the path for Google Chrome or Chromium installed via standard locations or Flatpak.
    Raises FileNotFoundError if no installation is found.
    """
    common_paths = [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/google-chrome-beta",
        "/usr/bin/google-chrome-unstable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/local/bin/google-chrome",
        "/usr/local/bin/google-chrome-stable",
        "/usr/local/bin/google-chrome-beta",
        "/usr/local/bin/google-chrome-unstable",
        "/usr/local/bin/chromium",
        "/usr/local/bin/chromium-browser",
        "/opt/google/chrome/chrome",
        "/opt/google/chrome-beta/chrome",
        "/opt/google/chrome-unstable/chrome",
        "/snap/bin/chromium",
        "/snap/bin/google-chrome",
        "/snap/bin/google-chrome-stable",
        "/snap/bin/google-chrome-beta",
        "/snap/bin/google-chrome-unstable",
    ]
    for path in common_paths:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return [path]

    try:
        flatpak_output = subprocess.run(
            ["flatpak", "list"], capture_output=True, text=True
        ).stdout
        if "com.google.Chrome" in flatpak_output:
            return ["flatpak", "run", "com.google.Chrome"]
        elif "org.chromium.Chromium" in flatpak_output:
            return ["flatpak", "run", "org.chromium.Chromium"]
    except FileNotFoundError:
        pass

    raise FileNotFoundError(
        "Chrome or Chromium browser not found. Please ensure it is installed."
    )


def title(md: str) -> str:
    """
    Extracts the title from the first Markdown heading.
    """
    for line in md.splitlines():
        if line.startswith("# ") and not line.startswith("##"):
            return line.strip("# ").strip()
    raise ValueError("No suitable Markdown h1 heading found for title.")


def make_html(md: str, css_file: str) -> str:
    """
    Converts Markdown content to HTML format, embedding the specified CSS.
    """
    try:
        with open(css_file) as cssfp:
            css = cssfp.read()
    except FileNotFoundError:
        css = ""
        print(f"{css_file} not found. Output will be unstyled.")

    preamble = f"<html lang='en'><head><meta charset='UTF-8'><title>{title(md)}</title><style>{css}</style></head><body><div id='resume'>"
    postamble = "</div></body></html>"
    return preamble + markdown.markdown(md, extensions=["smarty", "abbr"]) + postamble


def write_pdf(html: str, output_pdf: str, chrome_path: Optional[str] = None) -> None:
    """
    Generates a PDF file from HTML content using Chrome or Chromium.
    """
    chrome_command = chrome_path.split() if chrome_path else guess_chrome_path()
    html64 = base64.b64encode(html.encode("utf-8")).decode("utf-8")
    with tempfile.TemporaryDirectory() as tmpdir:
        options = [
            "--no-sandbox",
            "--headless",
            "--print-to-pdf-no-header",
            "--no-pdf-header-footer",
            "--enable-logging=stderr",
            "--log-level=2",
            "--in-process-gpu",
            "--disable-gpu",
            f"--crash-dumps-dir={tmpdir}",
            f"--user-data-dir={tmpdir}",
            f"--print-to-pdf={output_pdf}",
            f"data:text/html;base64,{html64}",
        ]
        subprocess.run(chrome_command + options, check=True)
        print(f"Wrote {output_pdf}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-md",
        default="resume.md",
        help="Markdown input file (default: resume.md)",
    )
    parser.add_argument(
        "--input-css",
        default="style.css",
        help="CSS input file for styling (default: style.css)",
    )
    parser.add_argument(
        "--output-html",
        default="index.html",
        help="HTML output file (default: index.html)",
    )
    parser.add_argument(
        "--output-pdf",
        default="Jonathan_Hendrickson_resume.pdf",
        help="PDF output file (default: Jonathan_Hendrickson_resume.pdf)",
    )
    parser.add_argument(
        "--chrome-path", help="Path to Chrome or Chromium executable for PDF generation"
    )

    args = parser.parse_args()

    with open(args.input_md, encoding="utf-8") as mdfp:
        md_content = mdfp.read()

    html_content = make_html(md_content, args.input_css)

    with open(args.output_html, "w", encoding="utf-8") as htmlfp:
        htmlfp.write(html_content)

    if args.output_pdf:
        write_pdf(html_content, args.output_pdf, args.chrome_path)
