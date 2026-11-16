"""Page-addressable extraction; PyMuPDF or installed Poppler, no downloads."""
import sys
import re
import shutil
import subprocess


def extract_pages(pdf_path):
    try:
        import fitz
    except ImportError:
        if not shutil.which('pdftotext') or not shutil.which('pdfinfo'):
            raise RuntimeError('Install PyMuPDF or provide pdfinfo and pdftotext on PATH')
        info = subprocess.run(['pdfinfo', str(pdf_path)], capture_output=True,
                              timeout=60, check=True)
        match = re.search(rb'Pages:\s+(\d+)', info.stdout)
        if not match:
            raise ValueError('Cannot determine PDF page count')
        count = int(match.group(1))
        output = subprocess.run(['pdftotext', '-layout', '-enc', 'UTF-8', str(pdf_path), '-'],
                                capture_output=True, timeout=120, check=True)
        pages = output.stdout.decode('utf-8').split('\f')
        if pages and not pages[-1].strip():
            pages.pop()
        if len(pages) != count:
            raise ValueError('PDF page count and extracted page boundaries disagree')
        return pages
    with fitz.open(pdf_path) as doc:
        if doc.needs_pass:
            raise ValueError('Encrypted PDF requires a password')
        return [page.get_text() for page in doc]


def render_pages(pages):
    return '\n\n'.join(f'<!-- PDF page {i} -->\n{text}'
                        for i, text in enumerate(pages, 1))

def extract_text(pdf_path: str) -> str:
    return render_pages(extract_pages(pdf_path))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_pdf.py <pdf_path> [output_file]", file=sys.stderr)
        sys.exit(1)
    try:
        text = extract_text(sys.argv[1])
        if len(sys.argv) >= 3:
            with open(sys.argv[2], 'w', encoding='utf-8') as f:
                f.write(text)
        else:
            sys.stdout.reconfigure(encoding='utf-8')
            print(text)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
