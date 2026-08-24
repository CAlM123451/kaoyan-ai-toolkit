"""复习规划算法：纯本地确定性计算（不依赖 AI），离线可用。"""
from datetime import date


# 西综六科推荐复习顺序与时间占比
DEFAULT_PRIORITIES = [
    ("生理学", 0.18),
    ("内科学", 0.25),
    ("病理学", 0.15),
    ("外科学", 0.20),
    ("生物化学", 0.12),
    ("医学人文", 0.10),
]

# 三阶段划分：基础→强化→冲刺
PHASES = [
    ("基础", 0.40, "系统过一遍教材 + 对应章节真题，建立知识框架"),
    ("强化", 0.35, "重点突破高频考点 + 错题整理，薄弱科目加时"),
    ("冲刺", 0.25, "全真模拟 + 查漏补缺 + 回顾错题本"),
]


def compute_weeks(exam_date: str, daily_hours: float,
                  priorities: list[tuple[str, float]] | None = None) -> list[dict]:
    """根据考试日期和每日时长，计算剩余周数并按阶段分配科目重点。

    参数:
        exam_date: "YYYY-MM-DD"
        daily_hours: 每天可用小时
        priorities: [(科目名, 时间占比)]，占比之和应≈1.0
    返回:
        [{"week", "phase", "focus", "daily_hours", "milestone"}]
    """
    if priorities is None:
        priorities = DEFAULT_PRIORITIES

    exam = date.fromisoformat(exam_date)
    today = date.today()
    remaining_days = max((exam - today).days, 0)
    total_weeks = max(remaining_days // 7, 1)

    # 按阶段划分周数
    phase_weeks = []
    start = 0
    for i, (phase_name, ratio, _) in enumerate(PHASES):
        if i == len(PHASES) - 1:
            end = total_weeks
        else:
            end = start + max(round(total_weeks * ratio), 1)
            end = min(end, total_weeks)
        phase_weeks.append((phase_name, start, end))
        start = end

    # 排序后的科目名列表（按占比降序）
    sorted_subjects = [name for name, _ in sorted(priorities, key=lambda x: -x[1])]

    plan = []
    for w in range(1, total_weeks + 1):
        # 确定当前阶段
        phase_name = "冲刺"
        phase_desc = PHASES[2][2]
        for pname, ps, pe in phase_weeks:
            if ps < w <= pe:
                phase_name = pname
                phase_desc = [d for n, _, d in PHASES if n == pname][0]
                break

        # 基础/强化阶段：按科目轮转；冲刺阶段：综合
        if phase_name in ("基础", "强化"):
            # 基础阶段顺序轮转，强化阶段按优先级加权（高优先级科目重复出现）
            if phase_name == "基础":
                focus = sorted_subjects[(w - 1) % len(sorted_subjects)]
            else:
                # 强化阶段：前两个科目各占更多周
                weighted = sorted_subjects[:3]  # 前三科
                focus = weighted[(w - 1) % len(weighted)]
            milestone = f"完成「{focus}」{phase_name}阶段复习并刷对应章节真题"
        else:
            focus = "综合模拟 + 错题回顾"
            milestone = "完成一套全真模拟卷并复盘错题"

        plan.append({
            "week": w,
            "phase": phase_name,
            "phase_desc": phase_desc,
            "focus": focus,
            "daily_hours": daily_hours,
            "milestone": milestone,
        })
    return plan


def format_plan_markdown(plan: list[dict]) -> str:
    """将周计划格式化为 Markdown 表格。"""
    lines = ["# 考研复习周计划（本地算法生成）", ""]

    # 按阶段分组输出
    current_phase = None
    for p in plan:
        if p["phase"] != current_phase:
            current_phase = p["phase"]
            desc = p.get("phase_desc", "")
            lines.append(f"\n## {current_phase}阶段")
            if desc:
                lines.append(f"> {desc}\n")
            lines.append("| 周次 | 主攻科目 | 每日小时 | 里程碑 |")
            lines.append("|---|---|---|---|")
        lines.append(
            f"| {p['week']} | {p['focus']} | "
            f"{p['daily_hours']} | {p['milestone']} |"
        )

    total_weeks = len(plan)
    total_hours = sum(p["daily_hours"] * 7 for p in plan)
    lines.append(f"\n> 共 {total_weeks} 周 / 约 {total_hours:.0f} 小时，"
                 f"由本地确定性算法生成，可离线运行。")
    return "\n".join(lines)
