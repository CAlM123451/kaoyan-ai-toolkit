"""复习规划算法：纯本地确定性计算（不依赖 AI），离线可用。

支持两种复习调度：
1. 周计划轮转（默认，零依赖）—— compute_weeks()
2. FSRS 间隔重复调度（可选，MIT, https://github.com/open-spaced-repetition/py-fsrs）
   —— 按卡片记忆状态动态排期，更接近 Anki 的复习节奏
"""
from datetime import date, timedelta


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
# 阶段名 → 说明的快速映射（避免每次循环查找）
PHASE_DESC = {name: desc for name, _, desc in PHASES}


def compute_weeks(exam_date: str, daily_hours: float,
                  priorities: list[tuple[str, float]] | None = None) -> list[dict]:
    """根据考试日期和每日时长，计算剩余周数并按阶段分配科目重点。

    参数:
        exam_date: "YYYY-MM-DD"
        daily_hours: 每天可用小时
        priorities: [(科目名, 时间占比)]，占比之和应≈1.0
    返回:
        [{"week", "phase", "focus", "daily_hours", "milestone",
          "start_date", "end_date"}]
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
        for pname, ps, pe in phase_weeks:
            if ps < w <= pe:
                phase_name = pname
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

        # 本周日期范围：从今天算起，最后一周截止到考试日
        week_start = today + timedelta(days=(w - 1) * 7)
        week_end = min(week_start + timedelta(days=6), exam)

        plan.append({
            "week": w,
            "phase": phase_name,
            "phase_desc": PHASE_DESC[phase_name],
            "focus": focus,
            "daily_hours": daily_hours,
            "milestone": milestone,
            "start_date": week_start.isoformat(),
            "end_date": week_end.isoformat(),
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
            lines.append("| 周次 | 日期 | 主攻科目 | 每日小时 | 里程碑 |")
            lines.append("|---|---|---|---|---|")
        lines.append(
            f"| {p['week']} | {p['start_date']} ~ {p['end_date']} | "
            f"{p['focus']} | {p['daily_hours']} | {p['milestone']} |"
        )

    total_weeks = len(plan)
    total_hours = sum(p["daily_hours"] * 7 for p in plan)
    lines.append(f"\n> 共 {total_weeks} 周 / 约 {total_hours:.0f} 小时，"
                 f"由本地确定性算法生成，可离线运行。")
    return "\n".join(lines)


def fsrs_schedule(subjects: list[str], daily_capacity: int = 3,
                  start_date: str | None = None) -> list[dict]:
    """FSRS 间隔重复调度（可选依赖 py-fsrs，MIT 许可证）。

    把每个科目当作一张"卡片"，按 FSRS 算法生成复习日期序列，
    返回按天合并的复习安排。未安装 py-fsrs 时自动降级为
    1/2/4/7/15/30 天递进复习（与词卡项目 srs.py 的 SM-2 间隔一致）。

    参数:
        subjects: 科目列表
        daily_capacity: 每天最多复习的科目数
        start_date: "YYYY-MM-DD" 起始日，默认今天
    返回:
        [{"date": "YYYY-MM-DD", "weekday": "周一", "subjects": [...]}]
    """
    base = date.fromisoformat(start_date) if start_date else date.today()
    intervals: dict[str, list[int]] = {}

    try:
        # FSRS 后端：每个科目一张卡片，稳定后间隔按记忆状态生长
        from fsrs import Scheduler, Card, Rating
        for subj in subjects:
            sched = Scheduler()
            card = Card()
            seq: list[int] = []
            for _ in range(6):  # 前 6 次复习的间隔（天）
                interval = max(int(card.interval), 1)
                seq.append(interval)
                card = sched.review_card(card, Rating.Good).card
            intervals[subj] = seq
    except ImportError:
        # 降级：1/2/4/7/15/30 天递进
        for subj in subjects:
            intervals[subj] = [1, 2, 4, 7, 15, 30]

    # 按天合并：date -> subject 列表
    from collections import defaultdict
    day_map: dict[date, list[str]] = defaultdict(list)
    for subj in subjects:
        elapsed = 0
        for gap in intervals[subj]:
            elapsed += gap
            day_map[base + timedelta(days=elapsed)].append(subj)

    schedule = []
    for d in sorted(day_map):
        subs = day_map[d]
        # 超过每日容量时顺延到下一空闲天
        if len(subs) > daily_capacity:
            extra = subs[daily_capacity:]
            subs = subs[:daily_capacity]
            for s in extra:
                dd = d + timedelta(days=1)
                while dd in day_map:
                    dd += timedelta(days=1)
                day_map[dd].append(s)
        schedule.append({
            "date": d.isoformat(),
            "weekday": "周" + "一二三四五六日"[d.weekday()],
            "subjects": subs,
        })
    schedule.sort(key=lambda x: x["date"])
    return schedule


def format_fsrs_markdown(schedule: list[dict]) -> str:
    """FSRS 复习安排 → Markdown 表格。"""
    lines = ["# FSRS 间隔重复复习安排", ""]
    lines.append("| 日期 | 星期 | 复习科目 |")
    lines.append("|---|---|---|")
    for day in schedule:
        lines.append(
            f"| {day['date']} | {day['weekday']} | "
            f"{'、'.join(day['subjects'])} |"
        )
    lines.append("")
    lines.append("> 由 FSRS 算法生成；未安装 py-fsrs 时使用 1/2/4/7/15/30 天递进降级。")
    return "\n".join(lines)
