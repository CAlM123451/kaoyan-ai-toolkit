"""导出：考点分析结果 → Markdown / Mermaid 思维导图。"""


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
