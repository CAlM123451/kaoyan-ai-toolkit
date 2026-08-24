"""复习规划算法：纯本地确定性计算（不依赖 AI），离线可用。"""
from datetime import date, timedelta


def compute_weeks(exam_date: str, daily_hours: float,
                  priorities: list[str] | None = None) -> list[dict]:
    """根据考试日期和每日时长，计算剩余周数并分配科目重点。

    参数:
        exam_date: "YYYY-MM-DD"
        daily_hours: 每天可用小时
        priorities: 科目优先级列表（从高到低）
    返回:
        [{"week": 1, "focus": "...", "daily_hours": x, "milestone": "..."}]
    """
    if priorities is None:
        priorities = ["生理学", "内科学", "病理学", "外科学", "生物化学", "医学人文"]

    exam = date.fromisoformat(exam_date)
    today = date.today()
    remaining_days = max((exam - today).days, 0)
    weeks = max(remaining_days // 7, 1)

    plan = []
    # 前 70% 时间按优先级轮转，后 30% 用于总复习
    study_weeks = max(int(weeks * 0.7), 1)
    for w in range(1, weeks + 1):
        if w <= study_weeks:
            focus = priorities[(w - 1) % len(priorities)]
            phase = "系统复习"
        else:
            focus = "综合复习 + 真题"
            phase = "冲刺总复习"
        plan.append({
            "week": w,
            "phase": phase,
            "focus": focus,
            "daily_hours": daily_hours,
            "milestone": f"完成「{focus}」一轮复习并刷对应章节真题",
        })
    return plan


def format_plan_markdown(plan: list[dict]) -> str:
    lines = ["# 考研复习周计划（本地算法生成）", ""]
    lines.append("| 周次 | 阶段 | 主攻 | 每日小时 | 里程碑 |")
    lines.append("|---|---|---|---|---|")
    for p in plan:
        lines.append(
            f"| {p['week']} | {p['phase']} | {p['focus']} | "
            f"{p['daily_hours']} | {p['milestone']} |"
        )
    lines.append("")
    lines.append("> 由本地确定性算法生成，可离线运行。")
    return "\n".join(lines)
