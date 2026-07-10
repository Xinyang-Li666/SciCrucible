#!/bin/bash
# forge-ingest.sh — 提取 PDF 文本并输出到临时文件，供 LLM 编译
# 用法:
#   ./forge-ingest.sh             批量处理 new-papers/ 中所有 PDF
#   ./forge-ingest.sh <pdf_path>  处理单个 PDF

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/../.kiro/.ingest_cache"
mkdir -p "$OUTPUT_DIR"

extract_one() {
    local pdf="$1"
    local name
    name=$(basename "$pdf" .pdf)
    local out="$OUTPUT_DIR/${name}.txt"
    echo "  提取: $pdf"
    python "$SCRIPT_DIR/extract_pdf.py" "$pdf" "$out"
    echo "  → $out"
    echo "$out"
}

if [ $# -ge 1 ]; then
    # 单文件模式（兼容旧行为）
    PDF_PATH="$1"
    if [ ! -f "$PDF_PATH" ]; then
        echo "错误: 文件不存在: $PDF_PATH"
        exit 1
    fi
    extract_one "$PDF_PATH"
else
    # 批量模式：处理 new-papers/ 中所有 PDF
    NEW_PAPERS_DIR="$SCRIPT_DIR/../raw/new-papers"
    if [ ! -d "$NEW_PAPERS_DIR" ]; then
        echo "错误: new-papers/ 目录不存在"
        exit 1
    fi

    pdfs=$(find "$NEW_PAPERS_DIR" -name "*.pdf" -type f | sort)
    if [ -z "$pdfs" ]; then
        echo "new-papers/ 中没有 PDF 文件"
        exit 0
    fi

    echo "=== 批量提取开始 ==="
    echo "发现以下 PDF:"
    echo "$pdfs" | while read f; do echo "  - $(basename "$f")"; done
    echo ""

    OUTPUT_FILES=""
    IFS=$'\n'
    for pdf in $pdfs; do
        out=$(extract_one "$pdf")
        OUTPUT_FILES="$OUTPUT_FILES$out"$'\n'
    done

    echo ""
    echo "=== 批量提取完成 ==="
    echo "提取的文件列表:"
    echo "$OUTPUT_FILES" | grep -v '^$'
    echo ""
    echo "--- 接下来在 Claude Code 中执行 /forge-ingest ---"
    echo "提示: 在 Claude Code 中运行 /forge-ingest 开始批量编译"
fi
