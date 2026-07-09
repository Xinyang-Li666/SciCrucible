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

# 2. 建立页面 slug 索引 + 提取所有 [[wiki-link]] 目标
#    slug = basename 去扩展名，覆盖整个 wiki/ 树（含 archive/ 子目录按课题分层）
#    目标规范化：剥离 #锚点 与 路径/ 前缀，只保留末段文件名
echo "--- 出链统计 ---"
declare -A PAGE_SLUGS      # 所有存在的页面 slug
declare -A PAGE_TARGETS    # 所有被引用的目标 slug（已规范化）

for page in $PAGES; do
    PAGE_SLUGS["$(basename "$page" .md)"]=1
done

for page in $PAGES; do
    # 提取 [[...]] 中的内容（去掉 |别名）
    links=$(grep -oP '\[\[([^\]|]+)(\|[^\]]+)?\]\]' "$page" 2>/dev/null | sed 's/.*\[\[//;s/|.*//;s/\]\]//' || true)
    while IFS= read -r link; do
        [ -z "$link" ] && continue
        norm="${link%%#*}"    # 剥离 #锚点
        norm="${norm##*/}"    # 剥离路径前缀，取末段文件名
        [ -z "$norm" ] && continue    # 纯锚点链接 [[#...]] 跳过
        PAGE_TARGETS["$norm"]=1
    done <<< "$links"
done

echo ""

# 3. 检测断链（目标 slug 在整个 wiki/ 树中无对应 .md 文件）
echo "--- 断链检测 ---"
BROKEN=0
for target in "${!PAGE_TARGETS[@]}"; do
    if [ -z "${PAGE_SLUGS[$target]+x}" ]; then
        echo "  [断链] [[$target]] — 目标页面不存在"
        BROKEN=$((BROKEN + 1))
    fi
done
[ $BROKEN -eq 0 ] && echo "  无断链"
echo ""

# 4. 检测孤立页面（slug 未被任何页面引用，排除 index.md）
echo "--- 孤立页面检测 ---"
ORPHAN=0
for page in $PAGES; do
    page_slug=$(basename "$page" .md)
    [ "$page_slug" = "index" ] && continue
    if [ -z "${PAGE_TARGETS[$page_slug]+x}" ]; then
        echo "  [孤立] $page_slug — 无任何页面链接到此页面"
        ORPHAN=$((ORPHAN + 1))
    fi
done
[ $ORPHAN -eq 0 ] && echo "  无孤立页面"

echo ""
echo "=== 检查完成 ==="
