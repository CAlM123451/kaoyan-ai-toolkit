"""导出：考点分析结果 → Markdown / Mermaid 思维导图。"""


def to_mermaid(subject_dist: dict[str, int]) -> str:
    """科目分布 → Mermaid mindmap 语法。"""
    lines = ["mindmap", "  西综306考点分布"]
    for subject, hits in subject_dist.items():
        lines.append(f"    {subject}({hits})")
    return "\n".join(lines)


def to_markdown(subject_dist: dict[str, int], top_keywords: list[tuple],
                ai_result: dict | None = None) -> str:
    """生成考点分析 Markdown 报告。"""
    out = ["# 考点分析报告", ""]

    if ai_result and ai_result.get("subjects"):
        out.append("## AI 分析")
        for s in ai_result["subjects"]:
            out.append(f"- **{s.get('name','')}**（覆盖率 {s.get('coverage','?')}）：")
            kps = s.get("key_points", [])
            if kps:
                out.append("  - 高频考点：" + "、".join(kps[:8]))
        if ai_result.get("overall"):
            out.append(f"\n**总评**：{ai_result['overall']}")
        if ai_result.get("suggested_priority"):
            out.append("\n**建议复习顺序**：" + " → ".join(ai_result["suggested_priority"]))
        out.append("")

    out.append("## 科目分布（本地统计）")
    for subject, hits in subject_dist.items():
        out.append(f"- {subject}: {hits} 次关键词命中")
    out.append("")

    if top_keywords:
        out.append("## 高频关键词")
        out.append("、".join(f"{w}({c})" for w, c in top_keywords[:20]))
        out.append("")

    out.append("## Mermaid 思维导图")
    out.append("```mermaid")
    out.append(to_mermaid(subject_dist))
    out.append("```")
    out.append("")

    out.append("> 本报告由本地规则 + DeepSeek AI 辅助生成，仅供参考。")
    return "\n".join(out)
