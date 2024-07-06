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


def print_warning(message: str) -> None:
    """
    Prints a warning message in yellow text.
    """
    print(f"\033[93mWARNING: {message}\033[0m")


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


def make_html(md: str, css: str) -> str:
    """
    Converts Markdown content to HTML format, embedding the specified CSS and
    extracting the title from the first Markdown heading.
    """
    # Extract the title from the first Markdown heading
    title = None
    for line in md.splitlines():
        if line.startswith("# ") and not line.startswith("##"):
            title = line.strip("# ").strip()
            break

    if title is None:
        raise ValueError("No suitable Markdown h1 heading found for title.")

    preamble = (
        f"<html lang='en'>"
        f"<head>"
        f"<meta charset='UTF-8'>"
        f"<title>{title} - Resume</title>"
        f"<style>{css}</style>"
        f"</head>"
        f"<body>"
        f"<div id='resume'>"
    )
    postamble = "</div></body></html>"
    return (
        preamble
        + markdown.markdown(md, extensions=["smarty", "abbr", "tables"])
        + postamble
    )


def write_pdf(html: str, output_pdf: str, chrome_path: Optional[str] = None) -> int:
    """
    Generates a PDF file from HTML content using Chrome or Chromium and returns the number of pages in the PDF.
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

        result = subprocess.run(
            chrome_command + options, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if result.returncode != 0:
            print(f"Error: {result.stderr.decode('utf-8')}")
            print(result.stdout.decode("utf-8"))
            raise subprocess.CalledProcessError(result.returncode, result.args)

    # Check the number of pages in the generated PDF and return the count
    with fitz.open(output_pdf) as pdf_document:
        return pdf_document.page_count


def adjust_css(css_content: str, line_height: float) -> str:
    """
    Adjusts the CSS content to set the line height for print.
    """
    css_content = re.sub(
        r"line-height:\s*[\d.]+;", f"line-height: {line_height};", css_content
    )
    return css_content


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

    print("Reading input Markdown file...")
    with open(args.input_md, encoding="utf-8") as mdfp:
        md_content = mdfp.read()

    print("Checking spelling in the Markdown content...")
    check_spelling(md_content, args.input_dictionary)

    print("Reading CSS file...")
    with open(args.input_css, encoding="utf-8") as cssfp:
        css_content = cssfp.read()

    line_height = 1.2  # Starting line height
    prev_line_height = line_height

    first_iteration = True

    while True:
        line_height = round(line_height, 2)  # Round to two decimal places
        print(f"Adjusting CSS line height to {line_height}...")
        adjusted_css = adjust_css(css_content, line_height)
        html_content = make_html(md_content, adjusted_css)

        os.makedirs(output_dir, exist_ok=True)

        with open(output_html, "w", encoding="utf-8") as htmlfp:
            htmlfp.write(html_content)

        num_pages = write_pdf(html_content, output_pdf, args.chrome_path)

        if first_iteration:
            if num_pages > 1:
                print_warning("The generated PDF exceeds one page.")
                break
            first_iteration = False

        if num_pages > 1:
            print("Content exceeds one page, reverting to previous line height...")
            # If the content spills over to more than one page, revert to previous settings
            adjusted_css = adjust_css(css_content, prev_line_height)
            html_content = make_html(md_content, adjusted_css)

            print("Writing HTML content to file with reverted line height...")
            with open(output_html, "w", encoding="utf-8") as htmlfp:
                htmlfp.write(html_content)

            print("Generating final PDF with reverted line height...")
            write_pdf(html_content, output_pdf, args.chrome_path)
            break

        # Update previous settings
        prev_line_height = line_height

        # Increase line height for the next iteration
        line_height += 0.05
