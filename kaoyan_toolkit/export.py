"""导出：考点分析结果 → Markdown / Mermaid 思维导图 / Markmap 交互式 HTML。

- Mermaid：文本格式，可在支持 Mermaid 的工具中渲染
- Markmap（可选，MIT, https://github.com/markmap/markmap）：生成可交互
  折叠的 HTML 思维导图，浏览器双击即用
"""
import json


def _md_escape(s) -> str:
    """Markdown 单元格转义：竖线/换行会破坏表格结构。"""
    return str(s).replace("|", "\\|").replace("\n", " ")


def _mm_escape(s) -> str:
    """Mermaid mindmap 节点名转义：括号/引号会破坏语法。"""
    return str(s).replace("(", "（").replace(")", "）").replace('"', "'")


def to_mermaid(subject_dist: dict[str, int],
               top_keywords: list[tuple[str, int]] | None = None) -> str:
    """科目分布 → Mermaid mindmap 语法（含高频关键词子节点）。"""
    lines = ["mindmap", "  西综306考点分布"]
    for subject, hits in subject_dist.items():
        lines.append(f"    {_mm_escape(subject)}({hits})")
        # 如果有高频关键词，给每个科目添加子节点
        if top_keywords:
            # 简单启发式：把关键词归到命中的科目下
            from .extract import SUBJECT_KEYWORDS
            subject_kws = SUBJECT_KEYWORDS.get(subject, [])
            matched = [(w, c) for w, c in top_keywords
                       if any(kw in w for kw in subject_kws)]
            for w, c in matched[:5]:  # 每科最多 5 个子节点
                lines.append(f"      {_mm_escape(w)}({c})")
    return "\n".join(lines)


def to_markdown(subject_dist: dict[str, int], top_keywords: list[tuple],
                ai_result: dict | None = None) -> str:
    """生成考点分析 Markdown 报告。"""
    out = ["# 考点分析报告", ""]

    if ai_result and ai_result.get("subjects"):
        out.append("## AI 分析")
        for s in ai_result["subjects"]:
            out.append(f"- **{_md_escape(s.get('name', ''))}**（覆盖率 {_md_escape(s.get('coverage', '?'))}）：")
            kps = s.get("key_points", [])
            if kps:
                out.append("  - 高频考点：" + "、".join(_md_escape(k) for k in kps[:8]))
            diff = s.get("difficulty_hint")
            if diff:
                out.append(f"  - 常见难点：{_md_escape(diff)}")
        if ai_result.get("overall"):
            out.append(f"\n**总评**：{_md_escape(ai_result['overall'])}")
        if ai_result.get("suggested_priority"):
            out.append("\n**建议复习顺序**：" + " → ".join(
                _md_escape(x) for x in ai_result["suggested_priority"]))
        out.append("")

    out.append("## 科目分布（本地统计）")
    total_hits = sum(subject_dist.values()) or 1
    for subject, hits in subject_dist.items():
        pct = hits / total_hits * 100
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        out.append(f"- {subject}: {bar} {hits} 次 ({pct:.0f}%)")
    out.append("")

    if top_keywords:
        out.append("## 高频关键词 Top 20")
        out.append("| 排名 | 关键词 | 出现次数 |")
        out.append("|---|---|---|")
        for i, (w, c) in enumerate(top_keywords[:20], 1):
            out.append(f"| {i} | {_md_escape(w)} | {c} |")
        out.append("")

    out.append("## Mermaid 思维导图")
    out.append("```mermaid")
    out.append(to_mermaid(subject_dist, top_keywords))
    out.append("```")
    out.append("")

    out.append("> 本报告由本地规则 + DeepSeek AI 辅助生成，仅供参考。")
    return "\n".join(out)


def to_markmap_html(subject_dist: dict[str, int],
                    top_keywords: list[tuple[str, int]] | None = None,
                    ai_result: dict | None = None) -> str:
    """生成 Markmap 交互式思维导图 HTML（单文件，双击即用）。

    Markmap（MIT 许可证）通过 jsDelivr CDN 加载，页面无需构建工具。
    包含：科目分布、高频关键词、AI 分析要点，节点可交互折叠。
    """
    # 构建 Markdown 层级结构（markmap 按标题层级渲染）
    md_lines = ["# 西综306考点分析思维导图", ""]

    md_lines.append("## 科目分布（本地统计）")
    for subject, hits in subject_dist.items():
        md_lines.append(f"### {_md_escape(subject)}（{hits} 次命中）")
        # 若 AI 结果含该科目考点，展开子节点
        if ai_result and ai_result.get("subjects"):
            for s in ai_result["subjects"]:
                if s.get("name") == subject:
                    kps = s.get("key_points", [])
                    if kps:
                        for kp in kps[:6]:
                            md_lines.append(f"- {_md_escape(kp)}")
    md_lines.append("")

    if top_keywords:
        md_lines.append("## 高频关键词")
        for w, c in top_keywords[:20]:
            md_lines.append(f"- {_md_escape(w)}（{c} 次）")
        md_lines.append("")

    if ai_result and ai_result.get("overall"):
        md_lines.append("## AI 总评")
        md_lines.append(f"{_md_escape(ai_result['overall'])}")
        md_lines.append("")
    if ai_result and ai_result.get("suggested_priority"):
        md_lines.append("## 建议复习顺序")
        md_lines.append(" → ".join(_md_escape(x) for x in ai_result["suggested_priority"]))
        md_lines.append("")

    markdown = "\n".join(md_lines)
    return _MARKMAP_TEMPLATE.replace("__MARKDOWN_JSON__", json.dumps(markdown, ensure_ascii=False))


# markmap 单文件 HTML 模板（占位符 __MARKDOWN_JSON__ 在运行时替换）
_MARKMAP_TEMPLATE = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>西综306考点分析思维导图</title>
<style>
  html, body { margin:0; height:100%; overflow:hidden; background:#f8fbff; }
  #mindmap { position:fixed; inset:0; }
  .tip { position:fixed; top:10px; left:50%; transform:translateX(-50%);
         background:#fff; border:1px solid #e2e8f0; border-radius:8px;
         padding:6px 14px; font:13px "Microsoft YaHei",sans-serif;
         color:#64748b; z-index:10; box-shadow:0 1px 4px rgba(0,0,0,.06); }
</style>
</head>
<body>
<div class="tip">滚轮缩放 · 拖拽平移 · 点击节点展开/折叠</div>
<svg id="mindmap"></svg>
<script src="https://cdn.jsdelivr.net/npm/markmap-view@0.18.4/dist/browser/index.js"></script>
<script>
  const markdown = __MARKDOWN_JSON__;
  const { Transformer } = window.markmap;
  const transformer = new Transformer();
  const { root } = transformer.transform(markdown);
  const { Markmap } = window.markmap;
  Markmap.create('#mindmap', { autoFit: true }, root);
</script>
</body>
</html>"""
