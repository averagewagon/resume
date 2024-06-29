# Jonathan Hendrickson's Resume

My personal resume, hosted at [jhendrickson.dev](https://jhendrickson.dev).

The resume.md, style.css, and generator.py files are heavily adapted from
[mikepqr/resume.md](https://github.com/mikepqr/resume.md), tuned to meet my use cases.

- **Markdown to HTML Conversion**: Easily convert Markdown content into HTML.
- **Custom CSS Styling**: Embed custom CSS for professional styling.
- **Formatted One-Page Resume**: Convert Markdown into a well-formatted, single-page resume.
- **Spell Checking**: Check for spelling errors, ignoring words in a custom dictionary.
- **PDF Generation**: Generate a PDF from HTML using Chrome or Chromium.
- **Line Height Adjustment**: Automatically adjust line height to fit content within one page.

## Prerequisites

- Python ≥ 3.6
- `pip install requirements.txt`
- Optional, required for PDF output: Google Chrome or Chromium

## Usage

Running `./generator.py` will convert `resume.md` and `style.css` into a webpage
(`index.html`) and a pdf (`Jonathan_Hendrickson_resume.pdf`).

Additional options are documented through `./generator.py --help`.

## Customization

Edit [style.css](style.css) to change the appearance of your resume. The
default style is extremely generic, which is perhaps what you want in a resume,
but CSS gives you a lot of flexibility. See, e.g. [The Tech Resume
Inside-Out](https://www.thetechinterview.com/) for good advice about what a
resume should look like (and what it should say).

Change the appearance of the PDF version (without affecting the HTML version) by
adding rules under the `@media print` CSS selector.

Change the margins and paper size of the PDF version by editing the [`@page` CSS
rule](https://developer.mozilla.org/en-US/docs/Web/CSS/%40page/size).

[python-markdown](https://python-markdown.github.io/) is by default a very basic
markdown compiler, but it has a number of optional extensions that you may want
to enable (by adding to [the list of extensions
here](https://github.com/mikepqr/resume.md/blob/f1b0699a9b66833cb67bb59111f45a09ed3c0f7e/resume.py#L112)).
[`attr_list`](https://python-markdown.github.io/extensions/attr_list/)
in particular may by useful if you are editing the CSS.
[abbreviations](https://python-markdown.github.io/extensions/abbreviations/)
extension is already enabled.
