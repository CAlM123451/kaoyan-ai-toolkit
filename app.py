"""Gradio Web 界面：python app.py → http://127.0.0.1:7860"""
import os

import gradio as gr

from kaoyan_toolkit.ai import analyze_subjects, generate_plan, review_wrong_question
from kaoyan_toolkit.analyze import analyze_text
from kaoyan_toolkit.cache import AICache
from kaoyan_toolkit.export import to_markdown
from kaoyan_toolkit.parse import parse_file
from kaoyan_toolkit.planner import compute_weeks, format_plan_markdown

CACHE = AICache(os.path.join(os.path.dirname(__file__), ".cache.sqlite"))


def fn_analyze(file, use_ai: bool) -> str:
    if not file:
        return "请先上传文件（txt/pdf/docx）"
    try:
        text = parse_file(file)
        local = analyze_text(text)
        ai = None
        if use_ai:
            try:
                ai = analyze_subjects(text, CACHE)
            except Exception as e:
                ai = None
                return f"AI 调用失败（{e}），已回退到本地统计：\n\n" + to_markdown(
                    local["subject_distribution"], local["top_keywords"], None
                )
        return to_markdown(local["subject_distribution"], local["top_keywords"], ai)
    except Exception as e:
        return f"出错: {e}"


def fn_plan(exam_date: str, daily_hours: float, use_ai: bool) -> str:
    priorities = ["生理学", "内科学", "病理学", "外科学", "生物化学", "医学人文"]
    try:
        plan = compute_weeks(exam_date, daily_hours, priorities)
        md = format_plan_markdown(plan)
        if use_ai:
            try:
                ai = generate_plan(
                    exam_date, daily_hours, " → ".join(priorities), CACHE
                )
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
        result = review_wrong_question(wrong_text, CACHE)
        lines = ["# 错题复盘", ""]
        for k, v in result.items():
            lines.append(f"## {k}")
            lines.append(str(v))
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"AI 调用失败: {e}\n\n请确认已设置 DEEPSEEK_API_KEY 环境变量。"


def build_demo():
    with gr.Blocks(title="考研 AI 备考工作台", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 考研 AI 备考工作台\n\n上传你**自己拥有的**真题/资料，本地解析 + DeepSeek AI 辅助分析。数据合规：仓库不含任何版权内容，API Key 走环境变量。")

        with gr.Tab("考点分析"):
            with gr.Row():
                file_in = gr.File(label="上传真题/资料 (txt/pdf/docx)")
                use_ai = gr.Checkbox(label="启用 AI 深度分析（需 DEEPSEEK_API_KEY）", value=False)
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

        analyze_btn.click(fn_analyze, [file_in, use_ai], analyze_out)
        plan_btn.click(fn_plan, [exam_date, daily_hours, plan_use_ai], plan_out)
        review_btn.click(fn_review, [wrong_text], review_out)

    return demo


if __name__ == "__main__":
    build_demo().launch()
