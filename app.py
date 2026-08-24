"""Gradio Web 界面：python app.py → http://127.0.0.1:7860"""
import os

import gradio as gr

from kaoyan_toolkit.ai import analyze_subjects, generate_plan, review_wrong_question
from kaoyan_toolkit.analyze import analyze_text
from kaoyan_toolkit.cache import AICache
from kaoyan_toolkit.export import to_markdown
from kaoyan_toolkit.parse import parse_file
from kaoyan_toolkit.planner import compute_weeks, format_plan_markdown
from kaoyan_toolkit.wrong_book import WrongBook, format_wrong_book

# 延迟初始化缓存（避免 import 时就创建文件）
_CACHE: AICache | None = None
_BOOK: WrongBook | None = None


def _get_cache() -> AICache:
    global _CACHE
    if _CACHE is None:
        _CACHE = AICache(os.path.join(os.path.dirname(__file__), ".cache.sqlite"))
    return _CACHE


def _get_book() -> WrongBook:
    global _BOOK
    if _BOOK is None:
        _BOOK = WrongBook(
            os.path.join(os.path.dirname(__file__), "wrong_book.json")
        ).load()
    return _BOOK


def fn_analyze(file, use_ai: bool) -> str:
    if not file:
        return "请先上传文件（txt/pdf/docx）"
    try:
        text = parse_file(file)
        local = analyze_text(text)
        ai = None
        if use_ai:
            try:
                ai = analyze_subjects(text, _get_cache())
            except Exception as e:
                return (
                    f"AI 调用失败（{e}），已回退到本地统计：\n\n"
                    + to_markdown(local["subject_distribution"],
                                  local["top_keywords"], None)
                )
        return to_markdown(local["subject_distribution"], local["top_keywords"], ai)
    except Exception as e:
        return f"出错: {e}"


def fn_plan(exam_date: str, daily_hours: float, use_ai: bool) -> str:
    from kaoyan_toolkit.planner import DEFAULT_PRIORITIES
    try:
        plan = compute_weeks(exam_date, daily_hours)
        md = format_plan_markdown(plan)
        if use_ai:
            try:
                priority_str = " → ".join(name for name, _ in DEFAULT_PRIORITIES)
                ai = generate_plan(exam_date, daily_hours, priority_str, _get_cache())
                md += "\n\n## AI 优化建议\n"
                md += "\n".join(f"- {t}" for t in ai.get("tips", []))
                weeks = ai.get("weeks", [])
                if weeks and isinstance(weeks[0], dict) and "daily_plan" in weeks[0]:
                    md += "\n\n## AI 细化日程（第一周示例）\n"
                    md += "\n".join(f"- {d}" for d in weeks[0]["daily_plan"])
            except Exception as e:
                md += f"\n\n> AI 优化失败（{e}），已展示本地算法结果"
        return md
    except Exception as e:
        return f"出错: {e}（考试日期格式 YYYY-MM-DD）"


def fn_review(wrong_text: str) -> str:
    if not wrong_text.strip():
        return "请粘贴错题内容"
    try:
        result = review_wrong_question(wrong_text, _get_cache())
        lines = ["# 错题复盘", ""]
        for k, v in result.items():
            lines.append(f"## {k}")
            lines.append(str(v))
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"AI 调用失败: {e}\n\n请确认已设置 DEEPSEEK_API_KEY 环境变量。"


def fn_cache_stats() -> str:
    """显示缓存统计信息。"""
    st = _get_cache().stats()
    lines = [
        f"- 缓存条目数: **{st['entries']}**",
        f"- 数据库大小: {st['db_size_kb']} KB",
    ]
    if st["oldest"] and st["newest"]:
        lines.append(f"- 最早写入: {st['oldest']}")
        lines.append(f"- 最新写入: {st['newest']}")
    return "\n".join(lines)


def fn_cache_clear() -> str:
    """清空缓存并返回提示。"""
    _get_cache().clear()
    return "缓存已清空"


def fn_wrong_add(question, my_answer, correct, subject, source) -> str:
    """添加错题。"""
    if not question or not question.strip():
        return "请填写题干"
    it = _get_book().add(question, my_answer or "", correct or "",
                         subject=subject or "", source=source or "")
    return f"已添加错题 #{it['id']}（{it.get('subject') or '未分类'}）"


def fn_wrong_list() -> str:
    """列出错题（Markdown 表格）。"""
    items = _get_book().list_items()
    if not items:
        return "暂无错题。"
    rows = ["| ID | 状态 | 科目 | 题干 | 来源 |", "|---|---|---|---|---|"]
    for it in items[:50]:
        flag = "✓已复盘" if it.get("reviewed_at") else "⚠待复盘"
        q = (it.get("question") or "").replace("|", "\\|")[:48]
        rows.append(
            f"| {it['id']} | {flag} | {it.get('subject') or '—'} | "
            f"{q} | {it.get('source') or '—'} |"
        )
    st = _get_book().stats()
    rows.append("")
    rows.append(f"**共 {st['total']} 条** · 未复盘 {st['unreviewed']} · "
                f"反复错≥3次 {st['repeated_count']}")
    return "\n".join(rows)


def fn_wrong_remove(item_id: str) -> str:
    """按 ID 删除错题。"""
    try:
        iid = int(item_id)
    except (TypeError, ValueError):
        return "无效 ID"
    ok = _get_book().remove(iid)
    return f"已删除 #{iid}" if ok else f"未找到 #{iid}"


def fn_wrong_review() -> str:
    """AI 复盘全部未复盘错题。"""
    book = _get_book()
    targets = book.list_items(only_unreviewed=True)
    if not targets:
        return "没有待复盘的错题 🎉"
    lines = []
    for it in targets:
        text = "\n".join(filter(None, [
            it.get("question"), "我的答案: " + it.get("my_answer", ""),
            "正确答案: " + it.get("correct_answer", ""),
        ]))
        try:
            result = review_wrong_question(text, _get_cache())
            book.update(
                it["id"],
                analysis=(it.get("analysis", "") + "\n【AI复盘】\n" +
                          "\n".join(f"{k}: {v}" for k, v in result.items())),
            )
            book.mark_reviewed(it["id"])
            lines.append(f"## #{it['id']} {it.get('question', '')[:40]}")
            lines.append(f"**知识点**：{result.get('knowledge_point', '')}")
            lines.append(f"**出错原因**：{result.get('mistake_reason', '')}")
            lines.append("")
        except RuntimeError as e:
            lines.append(f"## #{it['id']} AI 复盘失败：{e}")
    return "\n".join(lines) or "复盘完成"


def fn_quiz(file, count) -> str:
    """AI 阅读出题。"""
    if not file:
        return "请上传阅读材料（txt/pdf/docx）"
    try:
        text = parse_file(file)
        from kaoyan_toolkit.ai_quiz import format_quiz_markdown, generate_quiz
        quiz = generate_quiz(text, n=max(1, min(count, 10)), cache=_get_cache())
        return format_quiz_markdown(quiz)
    except Exception as e:
        return f"出题失败: {e}\n\n请确认已设置 DEEPSEEK_API_KEY 环境变量。"


def build_demo():
    with gr.Blocks(title="考研 AI 备考工作台", theme=gr.themes.Soft()) as demo:
        gr.Markdown(
            "# 考研 AI 备考工作台\n\n"
            "上传你**自己拥有的**真题/资料，本地解析 + DeepSeek AI 辅助分析。\n\n"
            "数据合规：仓库不含任何版权内容，API Key 走环境变量。"
        )

        with gr.Tab("考点分析"):
            with gr.Row():
                file_in = gr.File(label="上传真题/资料 (txt/pdf/docx)")
                use_ai = gr.Checkbox(label="启用 AI 深度分析（需 DEEPSEEK_API_KEY）",
                                     value=False)
            analyze_btn = gr.Button("开始分析", variant="primary")
            analyze_out = gr.Markdown()

        with gr.Tab("复习规划"):
            exam_date = gr.Textbox(label="考试日期", placeholder="2027-12-25")
            daily_hours = gr.Slider(1, 12, value=4, step=0.5, label="每天可用小时")
            plan_use_ai = gr.Checkbox(label="启用 AI 优化（需 API）", value=False)
            plan_btn = gr.Button("生成计划", variant="primary")
            plan_out = gr.Markdown()

        with gr.Tab("错题复盘"):
            wrong_text = gr.Textbox(label="粘贴错题（含选项/解析）", lines=8)
            review_btn = gr.Button("AI 复盘", variant="primary")
            review_out = gr.Markdown()

        with gr.Tab("缓存管理"):
            gr.Markdown("查看或清空 AI 调用缓存（缓存可节省 API 费用）。")
            with gr.Row():
                stats_btn = gr.Button("查看缓存")
                clear_btn = gr.Button("清空缓存", variant="stop")
            cache_out = gr.Markdown()

        with gr.Tab("错题本"):
            gr.Markdown("**录入错题 → AI 自动复盘 → 周期回顾**，数据保存在 "
                        "wrong_book.json。")
            with gr.Row():
                w_question = gr.Textbox(label="题干（必填）",
                                        placeholder="把做错的题粘贴到这里",
                                        lines=3)
                w_my = gr.Textbox(label="我的答案", lines=2)
                w_correct = gr.Textbox(label="正确答案", lines=2)
            with gr.Row():
                w_subject = gr.Dropdown(
                    ["生理学", "内科学", "病理学", "外科学", "生物化学",
                     "医学人文", "政治", "英语", "其他"],
                    label="科目")
                w_source = gr.Textbox(label="来源（如 2021年真题）")
            w_add_btn = gr.Button("添加错题", variant="primary")
            w_add_out = gr.Markdown()
            w_list_btn = gr.Button("查看错题列表")
            w_list_out = gr.Markdown()
            with gr.Row():
                w_del_id = gr.Textbox(label="删除 ID", placeholder="输入错题 ID")
                w_del_btn = gr.Button("删除", variant="stop")
            w_review_btn = gr.Button("AI 复盘全部未复盘错题", variant="secondary")
            w_review_out = gr.Markdown()

        with gr.Tab("AI 阅读出题"):
            gr.Markdown("上传**你自己的**阅读材料，AI 按考研风格命制选择题。")
            with gr.Row():
                quiz_file = gr.File(label="阅读材料 (txt/pdf/docx)")
                quiz_count = gr.Slider(1, 10, value=3, step=1,
                                       label="题目数量")
            quiz_btn = gr.Button("生成练习题", variant="primary")
            quiz_out = gr.Markdown()

        analyze_btn.click(fn_analyze, [file_in, use_ai], analyze_out)
        plan_btn.click(fn_plan, [exam_date, daily_hours, plan_use_ai], plan_out)
        review_btn.click(fn_review, [wrong_text], review_out)
        stats_btn.click(fn_cache_stats, outputs=cache_out)
        clear_btn.click(fn_cache_clear, outputs=cache_out)

        w_add_btn.click(fn_wrong_add,
                        [w_question, w_my, w_correct, w_subject, w_source],
                        w_add_out)
        w_list_btn.click(fn_wrong_list, outputs=w_list_out)
        w_del_btn.click(fn_wrong_remove, [w_del_id], w_list_out)
        w_review_btn.click(fn_wrong_review, outputs=w_review_out)
        quiz_btn.click(fn_quiz, [quiz_file, quiz_count], quiz_out)

    return demo


if __name__ == "__main__":
    build_demo().launch()
