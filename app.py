"""Gradio Web 界面：python app.py → http://127.0.0.1:7860

六个功能页签 + 使用说明书，自定义主题美化。
"""
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


# ===================== 使用说明书 =====================
USE_GUIDE = """
## 🎓 欢迎使用考研 AI 备考工作台

本工具帮你在**自己拥有的真题资料**上完成：考点分析 → 复习规划 → 错题复盘 → 错题本管理 → AI 阅读出题。数据默认保存在本地，仅在你主动启用 AI 功能时调用 DeepSeek API。

---

### 📋 功能一览

| 页签 | 功能 | 是否需要 API |
|---|---|---|
| 考点分析 | 真题考频统计 + 科目分布 + 思维导图 + AI 深度分析 | 可选（AI 深度分析需） |
| 复习规划 | 按考试日期生成三阶段周计划（基础/强化/冲刺） | 可选（AI 优化需） |
| 错题复盘 | 粘贴错题 → AI 输出错因/知识点/同类题预测 | 需要 |
| 错题本 | 错题结构化管理 + AI 批量复盘 + 反复错统计 | 复盘需 |
| AI 阅读出题 | 基于你的材料生成考研风格四选一阅读题 | 需要 |
| 缓存管理 | 查看/清空 AI 调用缓存（省钱） | — |

---

### ⚙️ 首次配置（AI 功能）

在启动本程序前设置环境变量（PowerShell）：

```powershell
$env:DEEPSEEK_API_KEY = "sk-你的key"
```

> 没有 API Key 也不影响使用：考点分析可"纯本地统计"、复习规划完全离线生成。

### 🚀 各页签使用说明

**1. 考点分析**：上传 txt/pdf/docx → 勾选"启用 AI 深度分析"→ 点「开始分析」。输出包含：AI 考点点评、科目分布进度条、高频关键词 Top20、Mermaid 思维导图（可复制到支持 Mermaid 的笔记软件渲染）。

**2. 复习规划**：填入考试日期（YYYY-MM-DD，如 2027-12-25）+ 每天可用小时 → 生成三阶段周计划（含每周日期、主攻科目、里程碑）。勾选 AI 优化后可获得额外学习建议。

**3. 错题复盘**：粘贴一道错题（题干 + 你的选项 + 正确答案/解析）→ 点「AI 复盘」。输出：核心知识点、做错原因、知识脉络、同类题预测、复习建议。

**4. 错题本**：录入错题（科目/来源便于分类）→ 「查看错题列表」管理 → 点「AI 复盘全部未复盘错题」批量生成复盘记录并写入错题。反复错 ≥3 次的题会重点标出。

**5. AI 阅读出题**：上传一段你自己的阅读材料 → 选择题目数量 → 生成考研风格选择题（细节/主旨/推理/词义/态度），答案与解析默认折叠，可自行练习。

**6. 缓存管理**：AI 调用结果会缓存到 `.cache.sqlite`，相同内容不重复扣费。可查看条目数/占用空间/写入时间，随时清空。

---

### 🖥️ 命令行等效操作

```bash
python -m kaoyan_toolkit analyze 真题.txt -o output --no-ai   # 纯本地分析
python -m kaoyan_toolkit plan --exam-date 2027-12-25 -o output
python -m kaoyan_toolkit review 错题.txt -o output
python -m kaoyan_toolkit wrong add --question "..." --subject 内科学
python -m kaoyan_toolkit quiz 阅读材料.txt -o output
```

### 🔒 数据与合规

- 仓库**不含任何版权真题内容**，请导入你自己拥有的资料（自用合法）
- API Key 只走环境变量，不落盘、不硬编码
- 本地统计/规划完全离线，不产生任何网络请求
"""

# 快捷填充示例（供演示）
SAMPLE_WRONG = ("男，62岁，反复胸痛3年，活动后加重。心电图示V1-V4导联ST段抬高。"
                "最可能的诊断是？\n我的答案：B. 心绞痛\n正确答案：A. 心肌梗死")
SAMPLE_ANALYZE_HINT = "支持 txt / pdf / docx，可多文件分析；AI 深度分析需配置 API Key"


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


# ===================== 界面构建 =====================
def build_demo():
    # 自定义主题：医学蓝 + 青色点缀，统一圆角与字体
    theme = gr.themes.Soft(
        primary_hue=gr.themes.colors.blue,
        secondary_hue=gr.themes.colors.cyan,
        neutral_hue=gr.themes.colors.slate,
        font=["Noto Sans SC", "Microsoft YaHei", "PingFang SC", "sans-serif"],
        radius_size=gr.themes.sizes.radius_md,
        spacing_size=gr.themes.sizes.spacing_md,
    )

    with gr.Blocks(title="考研 AI 备考工作台", theme=theme,
                   css=_CSS) as demo:
        # ---------- 顶部 Hero ----------
        gr.Markdown(
            """
            <div class="hero">
              <div class="hero-title">🎓 考研 AI 备考工作台</div>
              <div class="hero-sub">用 AI 把真题榨干：考点分析 · 复习规划 · 错题复盘 · 错题本 · AI 出题</div>
              <div class="hero-badges">
                <span class="badge">🔒 数据本地优先</span>
                <span class="badge">🧠 DeepSeek 辅助</span>
                <span class="badge">📖 首次使用请看「使用说明书」</span>
              </div>
            </div>
            """
        )
        # 动态统计面板（错题/缓存，页面加载时刷新）
        dashboard = gr.Markdown()
        demo.load(fn_dashboard, outputs=dashboard)

        # ---------- 使用说明书 ----------
        with gr.Tab("📖 使用说明书"):
            gr.Markdown(USE_GUIDE)

        # ---------- 考点分析 ----------
        with gr.Tab("📊 考点分析"):
            gr.Markdown(
                "<div class='tab-desc'>上传**你自己拥有的**真题/资料，"
                "一键生成考点考频统计与 AI 深度分析。</div>"
            )
            with gr.Group():
                with gr.Row():
                    file_in = gr.File(label="📄 上传真题/资料 (txt/pdf/docx)",
                                      scale=3)
                    use_ai = gr.Checkbox(
                        label="🧠 启用 AI 深度分析（需 DEEPSEEK_API_KEY）",
                        value=False, scale=1)
                analyze_btn = gr.Button("🚀 开始分析", variant="primary",
                                        size="lg")
            analyze_out = gr.Markdown(label="分析结果")

        # ---------- 复习规划 ----------
        with gr.Tab("📅 复习规划"):
            gr.Markdown(
                "<div class='tab-desc'>输入考试日期与每日可用时长，"
                "生成三阶段（基础/强化/冲刺）周计划。</div>"
            )
            with gr.Group():
                with gr.Row():
                    exam_date = gr.Textbox(
                        label="考试日期", placeholder="2027-12-25",
                        info="格式 YYYY-MM-DD", scale=1)
                    daily_hours = gr.Slider(
                        1, 12, value=4, step=0.5,
                        label="每天可用小时", scale=1)
                with gr.Row():
                    plan_use_ai = gr.Checkbox(
                        label="🧠 启用 AI 优化建议（需 API）", value=False)
                    plan_btn = gr.Button("📋 生成计划", variant="primary",
                                         size="lg")
            plan_out = gr.Markdown(label="复习计划")

        # ---------- 错题复盘 ----------
        with gr.Tab("🔍 错题复盘"):
            gr.Markdown(
                "<div class='tab-desc'>粘贴一道做错的题，"
                "AI 输出：核心知识点 / 错因 / 知识脉络 / 同类题预测 / 复习动作。</div>"
            )
            with gr.Group():
                wrong_text = gr.Textbox(
                    label="粘贴错题（含选项/解析）", lines=8,
                    placeholder="题干…\n我的答案：…\n正确答案：…")
                with gr.Row():
                    fill_btn = gr.Button("✨ 填入示例", size="sm")
                    review_btn = gr.Button("🧠 AI 复盘", variant="primary",
                                           size="lg")
            review_out = gr.Markdown(label="复盘结果")

        # ---------- 缓存管理 ----------
        with gr.Tab("💾 缓存管理"):
            gr.Markdown(
                "<div class='tab-desc'>AI 调用结果缓存到本地，"
                "相同内容不重复扣费。定期清空可释放磁盘空间。</div>"
            )
            with gr.Group():
                with gr.Row():
                    stats_btn = gr.Button("📊 查看缓存", size="lg")
                    clear_btn = gr.Button("🗑️ 清空缓存", variant="stop",
                                          size="lg")
            cache_out = gr.Markdown(label="缓存信息")

        # ---------- 错题本 ----------
        with gr.Tab("📚 错题本"):
            gr.Markdown(
                "<div class='tab-desc'>结构化管理错题 → AI 自动复盘 → "
                "反复错题重点盯防。数据保存在 wrong_book.json。</div>"
            )
            with gr.Accordion("✍️ 录入错题", open=True):
                with gr.Row():
                    w_question = gr.Textbox(
                        label="题干（必填）",
                        placeholder="把做错的题粘贴到这里", lines=3, scale=3)
                with gr.Row():
                    w_my = gr.Textbox(label="我的答案", lines=2, scale=1)
                    w_correct = gr.Textbox(label="正确答案", lines=2, scale=1)
                with gr.Row():
                    w_subject = gr.Dropdown(
                        ["生理学", "内科学", "病理学", "外科学", "生物化学",
                         "医学人文", "政治", "英语", "其他"],
                        label="科目", scale=1)
                    w_source = gr.Textbox(
                        label="来源（如 2021年真题）", scale=1)
                w_add_btn = gr.Button("➕ 添加错题", variant="primary")
                w_add_out = gr.Markdown()
            with gr.Accordion("📋 错题管理", open=True):
                with gr.Row():
                    w_list_btn = gr.Button("查看错题列表", size="lg")
                    w_review_btn = gr.Button(
                        "🧠 AI 复盘全部未复盘错题", variant="secondary",
                        size="lg")
                with gr.Row():
                    w_del_id = gr.Textbox(
                        label="删除 ID", placeholder="输入错题 ID", scale=1)
                    w_del_btn = gr.Button("🗑️ 删除", variant="stop", scale=1)
                w_list_out = gr.Markdown(label="错题列表")
                w_review_out = gr.Markdown(label="AI 复盘结果")

        # ---------- AI 阅读出题 ----------
        with gr.Tab("📝 AI 阅读出题"):
            gr.Markdown(
                "<div class='tab-desc'>上传**你自己的**阅读材料，"
                "AI 按考研风格命制四选一阅读题（答案折叠，可自测）。</div>"
            )
            with gr.Group():
                with gr.Row():
                    quiz_file = gr.File(label="📄 阅读材料 (txt/pdf/docx)",
                                        scale=3)
                    quiz_count = gr.Slider(
                        1, 10, value=3, step=1, label="题目数量", scale=1)
                quiz_btn = gr.Button("📝 生成练习题", variant="primary",
                                     size="lg")
            quiz_out = gr.Markdown(label="练习题")

        # ---------- 页脚 ----------
        gr.Markdown(
            "<div class='footer'>考研 AI 备考工作台 v0.5.0 · "
            "缝合 litellm/FSRS/Markmap/PaddleOCR/pkuseg · "
            "数据合规：仓库不含任何版权内容，API Key 走环境变量</div>"
        )

        # ---------- 事件绑定 ----------
        analyze_btn.click(fn_analyze, [file_in, use_ai], analyze_out)
        plan_btn.click(fn_plan, [exam_date, daily_hours, plan_use_ai], plan_out)
        review_btn.click(fn_review, [wrong_text], review_out)
        fill_btn.click(lambda: SAMPLE_WRONG, outputs=wrong_text)
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


# 全局样式：Hero / 描述条 / 页脚 / 输出美化
_CSS = """
/* ---------- 页面背景与整体 ---------- */
.gradio-container {
  background:
    radial-gradient(1200px 500px at 50% -100px, rgba(37,99,235,.08), transparent 60%),
    radial-gradient(900px 400px at 90% -50px, rgba(8,145,178,.06), transparent 55%),
    linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
}
.gradio-container .main { max-width: 1180px; }

/* ---------- Hero ---------- */
.hero { text-align: center; padding: 26px 8px 10px; position: relative; }
.hero::after {
  content: ""; display: block; width: 90px; height: 4px; margin: 18px auto 0;
  border-radius: 4px;
  background: linear-gradient(90deg, #2563eb, #0891b2, #2563eb);
  background-size: 200% 100%; animation: hero-shine 3s linear infinite;
}
@keyframes hero-shine { from { background-position: 0% 0; } to { background-position: 200% 0; } }
.hero-title { font-size: 30px; font-weight: 800;
              background: linear-gradient(120deg, #1d4ed8, #0891b2 55%, #2563eb);
              -webkit-background-clip: text; -webkit-text-fill-color: transparent;
              letter-spacing: 1.5px; }
.hero-sub { color: #64748b; margin-top: 8px; font-size: 14px; letter-spacing: .5px; }
.hero-badges { margin-top: 14px; display: flex; gap: 8px; justify-content: center;
               flex-wrap: wrap; }
.hero-badges .badge { background: #eef2ff; color: #3730a3; border: 1px solid #c7d2fe;
                      border-radius: 999px; padding: 5px 14px; font-size: 12px;
                      transition: transform .15s, box-shadow .15s; cursor: default; }
.hero-badges .badge:hover { transform: translateY(-2px);
                            box-shadow: 0 4px 10px rgba(37,99,235,.12); }

/* ---------- 动态统计面板 ---------- */
.hero-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
              gap: 12px; margin: 20px auto 4px; max-width: 760px; }
.hero-stats .stat-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 14px;
                         padding: 14px 10px 10px; text-align: center;
                         box-shadow: 0 2px 8px rgba(15,23,42,.04);
                         transition: transform .2s, box-shadow .2s; }
.hero-stats .stat-card:hover { transform: translateY(-3px);
                               box-shadow: 0 8px 20px rgba(15,23,42,.08); }
.hero-stats .stat-num { font-size: 24px; font-weight: 800; color: #1e40af;
                        line-height: 1.2; }
.hero-stats .stat-label { font-size: 12px; color: #64748b; margin-top: 4px; }

/* ---------- 页签 ---------- */
.tabs { border: 1px solid #e2e8f0; border-radius: 14px; overflow: hidden;
        background: #fff; box-shadow: 0 2px 12px rgba(15,23,42,.05); }
.tab-nav button { font-size: 14px; transition: background .15s, color .15s; }
.tab-nav button:hover { background: #eef2ff; }

/* ---------- 描述条 ---------- */
.tab-desc { color: #475569; font-size: 13px; margin: 0 0 12px;
            padding: 10px 14px; background: linear-gradient(90deg, #f8fafc 0%, #eef2ff 100%);
            border-left: 3px solid #2563eb; border-radius: 0 10px 10px 0; }

/* ---------- 输入区卡片 ---------- */
.group { background: #fff; border: 1px solid #e2e8f0; border-radius: 14px !important;
         padding: 6px; box-shadow: 0 2px 10px rgba(15,23,42,.04) !important; }
.group:hover { border-color: #c7d2fe; }

/* ---------- 按钮 ---------- */
button.primary { background: linear-gradient(135deg, #2563eb, #0891b2) !important;
                 border: none !important; transition: all .2s ease !important;
                 position: relative; overflow: hidden; }
button.primary:hover { transform: translateY(-2px);
                       box-shadow: 0 8px 20px rgba(37,99,235,.35) !important; }
button.primary:active { transform: translateY(0); }
button.primary::after { content: ""; position: absolute; inset: 0;
                        background: linear-gradient(135deg, transparent, rgba(255,255,255,.2), transparent);
                        transform: translateX(-100%); transition: transform .5s; }
button.primary:hover::after { transform: translateX(100%); }
button.secondary { transition: all .2s ease !important; }
button.secondary:hover { transform: translateY(-1px);
                         box-shadow: 0 4px 12px rgba(15,23,42,.12) !important; }
button.stop:hover { box-shadow: 0 4px 12px rgba(220,38,38,.25) !important; }

/* ---------- 加载动画 ---------- */
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: .5; } }
.loading { animation: pulse 1.5s ease-in-out infinite; }

/* ---------- 输出 Markdown 美化 ---------- */
.prose h1 { border-bottom: 2px solid #eef2ff; padding-bottom: 8px; color: #1e293b; }
.prose h2 { color: #1e40af; margin-top: 18px; padding-left: 10px;
            border-left: 4px solid #2563eb; border-radius: 2px; }
.prose h3 { color: #334155; }
.prose table { border-collapse: separate; border-spacing: 0; width: 100%;
               border: 1px solid #e2e8f0; border-radius: 10px; overflow: hidden; }
.prose table th { background: #eef2ff; color: #1e40af; font-weight: 600;
                  padding: 8px 12px; text-align: left; }
.prose table td { padding: 8px 12px; border-top: 1px solid #f1f5f9; }
.prose table tr:nth-child(even) td { background: #f8fafc; }
.prose blockquote { border-left: 3px solid #93c5fd; background: #f8fafc;
                    padding: 6px 12px; border-radius: 0 8px 8px 0; color: #64748b; }
.prose code { background: #eef2ff; color: #1d4ed8; border-radius: 5px;
              padding: 1px 6px; font-size: 13px; }
.prose pre { background: #0f172a; border-radius: 10px; padding: 12px 14px; }
.prose pre code { background: transparent; color: #e2e8f0; }

/* ---------- Accordion ---------- */
.accordion { border: 1px solid #e2e8f0 !important; border-radius: 12px !important;
             margin-bottom: 10px !important; background: #fff !important; }

/* ---------- 页脚 ---------- */
.footer { text-align: center; color: #94a3b8; font-size: 12px;
          margin-top: 28px; padding-top: 14px; border-top: 1px dashed #e2e8f0;
          letter-spacing: .5px; }

@media (prefers-color-scheme: dark) {
  .gradio-container {
    background:
      radial-gradient(1200px 500px at 50% -100px, rgba(37,99,235,.12), transparent 60%),
      linear-gradient(180deg, #0f172a 0%, #111827 100%);
  }
  .hero-stats .stat-card { background: #1e293b; border-color: #334155; }
  .hero-stats .stat-num { color: #93c5fd; }
  .tabs { background: #111827; border-color: #334155; }
  .group { background: #1e293b; border-color: #334155; }
  .tab-desc { background: linear-gradient(90deg, #1e293b, #172554); color: #94a3b8;
              border-left-color: #3b82f6; }
  .prose table { border-color: #334155; }
  .prose table th { background: #1e3a5f; color: #93c5fd; }
  .prose table td { border-top-color: #334155; }
  .prose table tr:nth-child(even) td { background: #1e293b; }
  .prose h1 { color: #e2e8f0; border-bottom-color: #334155; }
  .hero-sub { color: #94a3b8; }
  .footer { color: #64748b; border-top-color: #334155; }
}
"""


def fn_dashboard() -> str:
    """生成顶部统计面板（错题数 / 待复盘 / 缓存条目）。"""
    stats_html = []
    try:
        st = _get_book().stats()
        stats_html.append(
            f"<div class='stat-card'><div class='stat-num'>{st['total']}</div>"
            f"<div class='stat-label'>📚 错题总数</div></div>")
        stats_html.append(
            f"<div class='stat-card'><div class='stat-num'>{st['unreviewed']}</div>"
            f"<div class='stat-label'>🔍 待复盘</div></div>")
        stats_html.append(
            f"<div class='stat-card'><div class='stat-num'>{st['repeated_count']}</div>"
            f"<div class='stat-label'>⚠️ 反复错≥3次</div></div>")
    except Exception:
        stats_html.append("<div class='stat-card'><div class='stat-num'>—</div>"
                          "<div class='stat-label'>📚 错题本</div></div>")
    try:
        c = _get_cache().stats()
        stats_html.append(
            f"<div class='stat-card'><div class='stat-num'>{c['entries']}</div>"
            f"<div class='stat-label'>💾 缓存条目</div></div>")
    except Exception:
        stats_html.append("<div class='stat-card'><div class='stat-num'>—</div>"
                          "<div class='stat-label'>💾 缓存</div></div>")
    return f"<div class='hero-stats'>{''.join(stats_html)}</div>"


if __name__ == "__main__":
    build_demo().launch()