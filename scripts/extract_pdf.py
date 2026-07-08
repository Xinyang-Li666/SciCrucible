"""Extract text from a PDF file using pymupdf (fitz)."""
import sys
import fitz

def extract_text(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    texts = []
    for page in doc:
        texts.append(page.get_text())
    doc.close()
    return "\n".join(texts)

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
