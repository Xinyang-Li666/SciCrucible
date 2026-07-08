#!/bin/bash
# forge-health.sh — 扫描 wiki/ 检测断链和孤立页面
# 用法：./forge-health.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WIKI_DIR="$SCRIPT_DIR/../wiki"

echo "=== 知识库健康检查 ==="
echo ""

# 1. 收集所有页面
echo "--- 页面列表 ---"
PAGES=$(find "$WIKI_DIR" -name "*.md" -type f)
echo "$PAGES" | sed 's|.*/SciCrucible/wiki/||'
echo ""

# 2. 提取所有 [[wiki-link]] 目标
echo "--- 出链统计 ---"
declare -A LINK_COUNTS
declare -A PAGE_TARGETS

for page in $PAGES; do
    page_slug=$(basename "$page" .md)
    # 提取 [[...]] 中的内容
    links=$(grep -oP '\[\[([^\]|]+)(\|[^\]]+)?\]\]' "$page" 2>/dev/null | sed 's/.*\[\[//;s/|.*//;s/\]\]//' || true)
    for link in $links; do
        PAGE_TARGETS["$link"]=1
    done
done

echo ""

# 3. 检测断链（链接目标没有对应 .md 文件）
echo "--- 断链检测 ---"
BROKEN=0
for target in "${!PAGE_TARGETS[@]}"; do
    target_file="$WIKI_DIR/concepts/$target.md"
    if [ ! -f "$target_file" ]; then
        target_file="$WIKI_DIR/literature/$target.md"
    fi
    if [ ! -f "$target_file" ]; then
        target_file="$WIKI_DIR/methods/$target.md"
    fi
    if [ ! -f "$target_file" ]; then
        target_file="$WIKI_DIR/projects/$target.md"
    fi
    if [ ! -f "$target_file" ]; then
        echo "  [断链] [[$target]] — 目标页面不存在"
        BROKEN=$((BROKEN + 1))
    fi
done
[ $BROKEN -eq 0 ] && echo "  无断链"
echo ""

# 4. 检测孤立页面（没有被任何页面链接到，排除 index.md）
echo "--- 孤立页面检测 ---"
for page in $PAGES; do
    page_slug=$(basename "$page" .md)
    [ "$page_slug" = "index" ] && continue
    is_referenced=false
    for p in $PAGES; do
        if grep -q "\[\[$page_slug\]\]" "$p" 2>/dev/null; then
            is_referenced=true
            break
        fi
    done
    if ! $is_referenced; then
        echo "  [孤立] $page_slug — 无任何页面链接到此页面"
    fi
done

echo ""
echo "=== 检查完成 ==="
