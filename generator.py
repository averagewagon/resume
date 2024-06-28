#!/usr/bin/env python3
import argparse
import base64
import os
import subprocess
import tempfile
from typing import List, Optional
import re

import fitz
import markdown
from spellchecker import SpellChecker


def check_spelling(text: str, dictionary_path: str) -> None:
    """
    Checks for spelling errors in the given text, ignoring words in the custom dictionary.
    Prints a warning message if any misspelled words are found.
    """
    spell = SpellChecker()

    # Load custom dictionary words
    try:
        with open(dictionary_path, encoding="utf-8") as dictfp:
            custom_dictionary = dictfp.read().splitlines()
    except FileNotFoundError:
        custom_dictionary = []

    spell.word_frequency.load_words(custom_dictionary)
    words = re.findall(r"\b\w+\b", text)  # Extract words using regex
    misspelled = spell.unknown(words)

    if misspelled:
        print_warning(f"Spelling errors found: {', '.join(misspelled)}")


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

    preamble = f"<html lang='en'><head><meta charset='UTF-8'><title>{title(md)} - Resume</title><style>{css}</style></head><body><div id='resume'>"
    postamble = "</div></body></html>"
    return preamble + markdown.markdown(md, extensions=["smarty", "abbr"]) + postamble


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


def write_pdf(html: str, output_pdf: str, chrome_path: Optional[str] = None) -> None:
    """
    Generates a PDF file from HTML content using Chrome or Chromium.
    Checks if the PDF is multiple pages and ensures the resume takes up at least 90% of the page.
    Outputs a yellow warning text if the PDF is more than one page or if the content is too short.
    """
    # Guess the Chrome path if not provided
    chrome_command = chrome_path.split() if chrome_path else guess_chrome_path()
    html64 = base64.b64encode(html.encode("utf-8")).decode("utf-8")

    # Create a temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        # Define Chrome options for PDF generation
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

        # Run the Chrome command to generate the PDF
        subprocess.run(chrome_command + options, check=True)
        print(f"Wrote {output_pdf}")

        # Check the number of pages and content height in the generated PDF
        check_pdf_pages(output_pdf)
        check_pdf_content_height(output_pdf)


def check_pdf_pages(pdf_path: str) -> None:
    """
    Checks the number of pages in the PDF file and outputs a yellow warning if it is more than one.
    """
    with fitz.open(pdf_path) as pdf_document:
        num_pages = pdf_document.page_count
        if num_pages > 1:
            print_warning(
                f"The generated PDF has {num_pages} pages, which exceeds the allowed limit of one page."
            )


def check_pdf_content_height(pdf_path: str) -> None:
    """
    Checks that the content in the PDF file takes up at least 90% of the page height.
    Outputs a yellow warning if the content is too short.
    """
    with fitz.open(pdf_path) as pdf_document:
        page = pdf_document[0]
        page_height = page.rect.height
        content_height = 0

        for block in page.get_text("blocks"):
            _, _, _, block_bottom = block[:4]
            if block_bottom > content_height:
                content_height = block_bottom

        if content_height < 0.9 * page_height:
            print_warning(
                "The content in the generated PDF does not take up at least 90% of the page height."
            )


def print_warning(message: str) -> None:
    """
    Prints a warning message in yellow text.
    """
    print(f"\033[93mWARNING: {message}\033[0m")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--release",
        action="store_true",
        help="If specified, output files will be built in the docs/ folder. Otherwise, they will go in the build/ folder.",
    )
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
        "--input-dictionary",
        default="dictionary.txt",
        help="File containing custom dictionary words to ignore (default: dictionary.txt)",
    )
    parser.add_argument(
        "--output-html",
        default="index.html",
        help="HTML output file name (default: index.html)",
    )
    parser.add_argument(
        "--output-pdf",
        default="Jonathan_Hendrickson_resume.pdf",
        help="PDF output file name (default: Jonathan_Hendrickson_resume.pdf)",
    )
    parser.add_argument(
        "--chrome-path", help="Path to Chrome or Chromium executable for PDF generation"
    )

    args = parser.parse_args()

    output_dir = "docs" if args.release else "build"
    output_html = os.path.join(output_dir, args.output_html)
    output_pdf = os.path.join(output_dir, args.output_pdf)

    with open(args.input_md, encoding="utf-8") as mdfp:
        md_content = mdfp.read()

    # Check for spelling errors in the Markdown content
    check_spelling(md_content, args.input_dictionary)

    html_content = make_html(md_content, args.input_css)

    os.makedirs(output_dir, exist_ok=True)

    with open(output_html, "w", encoding="utf-8") as htmlfp:
        htmlfp.write(html_content)

    if args.output_pdf:
        write_pdf(html_content, output_pdf, args.chrome_path)
