"""PyMuPDF4LLM 封装 — PDF → Markdown 批量提取（forge-extract Step 3）

用法: python extract_pdf_to_md.py --input raw/extract/papers/ --output raw/extract/md/
      python extract_pdf_to_md.py --pdf single.pdf --output raw/extract/md/
"""
import sys
import os
from pathlib import Path

try:
    import pymupdf4llm
except ImportError:
    print("❌ pymupdf4llm 未安装。运行: pip install pymupdf4llm")
    sys.exit(1)


def extract_pdf(pdf_path: Path, output_dir: Path) -> Path:
    """提取单篇 PDF 为 Markdown"""
    md_text = pymupdf4llm.to_markdown(str(pdf_path), show_progress=False)
    md_path = output_dir / (pdf_path.stem + ".md")
    md_path.write_text(md_text, encoding="utf-8")
    return md_path


def main():
    input_path = None
    output_dir = None
    single_mode = False

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--input" and i + 1 < len(args):
            input_path = Path(args[i + 1])
            i += 2
        elif args[i] == "--pdf" and i + 1 < len(args):
            input_path = Path(args[i + 1])
            single_mode = True
            i += 2
        elif args[i] == "--output" and i + 1 < len(args):
            output_dir = Path(args[i + 1])
            i += 2
        else:
            i += 1

    if not input_path or not output_dir:
        print("用法: python extract_pdf_to_md.py --input <dir> --output <dir>")
        print("      python extract_pdf_to_md.py --pdf <file> --output <dir>")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    if single_mode:
        if not input_path.suffix.lower() == ".pdf":
            print(f"⚠️ 跳过非 PDF 文件: {input_path.name}")
            sys.exit(1)
        md_path = extract_pdf(input_path, output_dir)
        print(f"✅ {input_path.name} → {md_path.name} ({md_path.stat().st_size} bytes)")
    else:
        pdf_files = sorted(input_path.glob("*.pdf"))
        if not pdf_files:
            print(f"⚠️ {input_path} 中没有 PDF 文件")
            sys.exit(0)

        succeeded, failed = 0, 0
        for pdf in pdf_files:
            try:
                md_path = extract_pdf(pdf, output_dir)
                print(f"✅ {pdf.name} → {md_path.name} ({md_path.stat().st_size} bytes)")
                succeeded += 1
            except Exception as e:
                print(f"❌ {pdf.name}: {e}")
                failed += 1

        print(f"\n完成: {succeeded} 成功, {failed} 失败")


if __name__ == "__main__":
    main()
