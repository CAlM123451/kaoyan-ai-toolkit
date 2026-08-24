"""命令行入口：python -m kaoyan_toolkit <analyze|plan|mindmap|review>"""
import argparse
import json
import os
import sys
from datetime import date

from .ai import analyze_subjects, generate_plan, review_wrong_question
from .analyze import analyze_text
from .cache import AICache
from .export import to_markdown, to_markmap_html
from .parse import parse_file
from .planner import (compute_weeks, format_fsrs_markdown,
                      format_plan_markdown, fsrs_schedule)


def _validate_date(s: str) -> str:
    """验证日期格式 YYYY-MM-DD。"""
    try:
        date.fromisoformat(s)
        return s
    except ValueError:
        raise argparse.ArgumentTypeError(f"日期格式错误: '{s}'，应为 YYYY-MM-DD")


def _validate_hours(s: str) -> float:
    """验证每日学习时长（正数，最多 24 小时）。"""
    try:
        v = float(s)
    except ValueError:
        raise argparse.ArgumentTypeError(f"时间格式错误: '{s}'，应为数字（如 4.5）")
    if not 0 < v <= 24:
        raise argparse.ArgumentTypeError(f"每日时长应在 0~24 小时之间: '{s}'")
    return v


def _cmd_wrong(args) -> int:
    """错题本子命令分派。"""
    from .wrong_book import WrongBook, format_wrong_book

    book = WrongBook(args.book).load()

    if not args.wcmd:
        _print_wrong_stats(book)
        return 0

    if args.wcmd == "add":
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]
        it = book.add(args.question, args.my_answer, args.correct,
                      args.analysis, args.subject, args.source, tags)
        print(f"已添加错题 #{it['id']}（{it['subject'] or '未分类'}）")
        return 0

    if args.wcmd == "list":
        items = book.list_items(args.subject, args.keyword, args.unreviewed)
        if args.output_md:
            os.makedirs(os.path.dirname(os.path.abspath(args.output_md))
                        or ".", exist_ok=True)
            with open(args.output_md, "w", encoding="utf-8") as f:
                f.write(format_wrong_book(items))
            print(f"已导出 {len(items)} 条错题: {args.output_md}")
        else:
            for it in items:
                # 用 ASCII 标记（防 Windows GBK 控制台编码崩溃）
                flag = "[OK]" if it.get("reviewed_at") else "[待]"
                print(f"#{it['id']} {flag} {it.get('subject', '未分类')}: "
                      f"{it.get('question', '')[:60]}")
            print(f"\n共 {len(items)} 条")
        return 0

    if args.wcmd == "remove":
        ok = book.remove(args.id)
        print(f"已删除错题 #{args.id}" if ok else f"未找到错题 #{args.id}")
        return 0 if ok else 1

    if args.wcmd == "stats":
        _print_wrong_stats(book)
        return 0

    if args.wcmd == "export":
        items = book.list_items(args.subject, args.keyword, args.unreviewed)
        if not items:
            print("没有可导出的错题")
            return 0
        fmt = args.format
        if fmt == "anki":
            from .wrong_export import export_anki
            out = export_anki(items, args.output)
        elif fmt == "excel":
            from .wrong_export import export_excel
            out = export_excel(items, args.output)
        else:
            from .wrong_book import format_wrong_book
            os.makedirs(os.path.dirname(os.path.abspath(args.output)) or ".",
                        exist_ok=True)
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(format_wrong_book(items))
            out = args.output
        print(f"已导出 {len(items)} 条错题: {out}")
        return 0

    if args.wcmd == "review":
        cache = AICache(os.path.join(args.output, ".cache.sqlite"))
        from .ai import review_wrong_question
        targets = ([it for it in book.list_items() if it["id"] == args.id]
                   if args.id else book.list_items(only_unreviewed=True))
        if not targets:
            print("没有待复盘的错题")
            return 0
        for it in targets:
            print(f"AI 复盘 #{it['id']} …")
            text = "\n".join(filter(None, [
                it.get("question"), "我的答案: " + it.get("my_answer", ""),
                "正确答案: " + it.get("correct_answer", ""),
                "解析: " + it.get("analysis", ""),
            ]))
            try:
                result = review_wrong_question(text, cache)
            except RuntimeError as e:
                print(f"  AI 复盘失败: {e}")
                continue
            book.update(
                it["id"],
                analysis=(it.get("analysis", "") + "\n【AI复盘】\n"
                          + "\n".join(f"{k}: {v}" for k, v in result.items())),
            )
            book.mark_reviewed(it["id"])
            print(f"  [OK] 已写入复盘并标记完成")
        return 0

    print("用法: kaoyan-toolkit wrong <add|list|stats|remove|review>")
    return 1


def _print_wrong_stats(book) -> None:
    st = book.stats()
    print(f"错题总数: {st['total']} · 未复盘: {st['unreviewed']} · "
          f"反复错(>=3): {st['repeated_count']}")
    for subject, n in st["subjects"].items():
        print(f"  {subject}: {n}")


def _cmd_quiz(args) -> int:
    """AI 阅读出题子命令。"""
    from .ai_quiz import format_quiz_markdown, generate_quiz
    from .cache import AICache

    os.makedirs(args.output, exist_ok=True)
    text = parse_file(args.input)
    cache = AICache(os.path.join(args.output, ".cache.sqlite"))
    print(f"基于材料生成 {args.count} 道阅读题（AI 生成中…）")
    quiz = generate_quiz(text, n=args.count, cache=cache)
    md = format_quiz_markdown(quiz)
    path = os.path.join(args.output, "quiz.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"已生成: {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="kaoyan-toolkit",
        description="考研 AI 备考工作台 —— 考点分析 / 复习规划 / 思维导图 / 错题复盘",
    )
    parser.add_argument(
        "--version", action="version", version="%(prog)s 0.3.0"
    )
    sub = parser.add_subparsers(dest="cmd")

    # analyze
    pa = sub.add_parser("analyze", help="考点分析（需 API）")
    pa.add_argument("input", help="真题/资料文件 (txt/pdf/docx)")
    pa.add_argument("-o", "--output", default="output")
    pa.add_argument("--no-ai", action="store_true", help="仅本地统计，不调用 AI")
    pa.add_argument("--markmap", action="store_true",
                    help="额外生成 markmap 交互式 HTML 思维导图")

    # plan
    pp = sub.add_parser("plan", help="复习规划（纯本地）")
    pp.add_argument("--exam-date", required=True, type=_validate_date,
                    help="考试日期 YYYY-MM-DD")
    pp.add_argument("--daily-hours", type=_validate_hours, default=4.0,
                    help="每天可用小时（默认 4）")
    pp.add_argument("-o", "--output", default="output")
    pp.add_argument("--fsrs", action="store_true",
                    help="使用 FSRS 间隔重复调度（可选安装 py-fsrs）")

    # mindmap
    pm = sub.add_parser("mindmap", help="思维导图导出")
    pm.add_argument("input", help="真题/资料文件")
    pm.add_argument("-o", "--output", default="output")
    pm.add_argument("--html", action="store_true",
                    help="生成 markmap 交互式 HTML（默认只输出 .mmd）")

    # review
    pr = sub.add_parser("review", help="错题复盘（需 API）")
    pr.add_argument("input", help="错题文本文件")
    pr.add_argument("-o", "--output", default="output")

    # cache
    pc = sub.add_parser("cache", help="缓存管理")
    pc.add_argument("--clear", action="store_true", help="清空全部缓存")
    pc.add_argument("--stats", action="store_true", help="显示缓存统计")
    pc.add_argument("-o", "--output", default="output")

    # wrong book
    pw = sub.add_parser("wrong", help="错题本管理（增删查/统计/AI复盘）")
    wsub = pw.add_subparsers(dest="wcmd")

    # wrong 子命令共享参数：错题本路径（-b/--book）
    _book_parent = argparse.ArgumentParser(add_help=False)
    _book_parent.add_argument("-b", "--book", default="wrong_book.json",
                              help="错题本路径")

    wadd = wsub.add_parser("add", parents=[_book_parent], help="添加错题")
    wadd.add_argument("--question", required=True, help="题干")
    wadd.add_argument("--my-answer", default="", help="我的答案")
    wadd.add_argument("--correct", default="", help="正确答案")
    wadd.add_argument("--analysis", default="", help="解析")
    wadd.add_argument("--subject", default="", help="科目")
    wadd.add_argument("--source", default="", help="来源（如 2021年真题）")
    wadd.add_argument("--tags", default="", help="标签，逗号分隔")
    wlist = wsub.add_parser("list", parents=[_book_parent], help="列出错题")
    wlist.add_argument("--subject", default="", help="按科目筛选")
    wlist.add_argument("--keyword", default="", help="按关键词筛选")
    wlist.add_argument("--unreviewed", action="store_true", help="仅未复盘")
    wlist.add_argument("-o", "--output-md", default="", help="导出 Markdown 路径")
    wexp = wsub.add_parser("export", parents=[_book_parent],
                           help="导出错题（Anki/Excel/Markdown）")
    wexp.add_argument("--format", choices=["anki", "excel", "markdown"],
                      default="anki", help="导出格式")
    wexp.add_argument("-o", "--output", default="wrong_book.apkg",
                      help="输出文件路径")
    wexp.add_argument("--subject", default="", help="按科目筛选")
    wexp.add_argument("--keyword", default="", help="按关键词筛选")
    wexp.add_argument("--unreviewed", action="store_true", help="仅未复盘")
    wsub.add_parser("stats", parents=[_book_parent], help="错题统计")
    wrm = wsub.add_parser("remove", parents=[_book_parent], help="删除错题")
    wrm.add_argument("id", type=int, help="错题 ID")
    wrv = wsub.add_parser("review", parents=[_book_parent],
                          help="AI 复盘未复盘错题")
    wrv.add_argument("--id", type=int, default=0, help="指定 ID（默认全部未复盘）")
    wrv.add_argument("-o", "--output", default="output")

    # quiz
    pq = sub.add_parser("quiz", help="AI 阅读出题（需 API）")
    pq.add_argument("input", help="阅读材料文件 (txt/pdf/docx)")
    pq.add_argument("--count", type=int, default=3, help="题目数量（默认 3）")
    pq.add_argument("-o", "--output", default="output")

    # similar
    ps = sub.add_parser("similar", help="相似题检索（BM25 本地离线）")
    ps.add_argument("corpus", help="真题语料文件（作为检索库）")
    ps.add_argument("query", help="题目/关键词文本（文件名或直接文本）")
    ps.add_argument("--top", type=int, default=5, help="返回条数（默认 5）")
    ps.add_argument("-o", "--output", default="output")

    args = parser.parse_args(argv)

    if not args.cmd:
        parser.print_help()
        return 1

    # 缓存子命令
    if args.cmd == "cache":
        cache = AICache(os.path.join(args.output, ".cache.sqlite"))
        if args.clear:
            cache.clear()
            print("缓存已清空")
        if args.stats or not args.clear:
            st = cache.stats()
            print(f"缓存路径: {os.path.join(args.output, '.cache.sqlite')}")
            print(f"缓存条目: {st['entries']}")
            print(f"数据库大小: {st['db_size_kb']} KB")
            if st["oldest"] and st["newest"]:
                print(f"最早写入: {st['oldest']}  最新写入: {st['newest']}")
        return 0

    # 错题本
    if args.cmd == "wrong":
        return _cmd_wrong(args)

    # AI 阅读出题
    if args.cmd == "quiz":
        return _cmd_quiz(args)

    # 相似题检索
    if args.cmd == "similar":
        from .similar import SimilarSearcher, format_search_results

        corpus_text = parse_file(args.corpus)
        # query 参数若指向已存在的文件则读取文件，否则视为文本
        if os.path.isfile(args.query):
            query = parse_file(args.query)
        else:
            query = args.query
        searcher = SimilarSearcher(corpus_text)
        results = searcher.search(query, top=args.top)
        md = format_search_results(results)
        os.makedirs(args.output, exist_ok=True)
        path = os.path.join(args.output, "similar.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# 相似题检索结果（查询：{query[:60]}）\n\n{md}")
        print(f"已生成: {path}（本地 BM25 检索，未调 API）")
        return 0

    os.makedirs(args.output, exist_ok=True)

    try:
        if args.cmd == "analyze":
            text = parse_file(args.input)
            local = analyze_text(text)
            cache = AICache(os.path.join(args.output, ".cache.sqlite"))
            ai = None if args.no_ai else analyze_subjects(text, cache)
            md = to_markdown(local["subject_distribution"], local["top_keywords"], ai)
            path = os.path.join(args.output, "analysis.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write(md)
            print(f"已生成: {path}")
            if args.markmap:
                mm_path = os.path.join(args.output, "mindmap.html")
                html = to_markmap_html(local["subject_distribution"],
                                       local["top_keywords"], ai)
                with open(mm_path, "w", encoding="utf-8") as f:
                    f.write(html)
                print(f"已生成: {mm_path}（浏览器打开，交互式折叠）")
            return 0

        if args.cmd == "plan":
            if args.fsrs:
                from .planner import DEFAULT_PRIORITIES
                subjects = [name for name, _ in DEFAULT_PRIORITIES]
                daily_cap = max(int(args.daily_hours), 1)
                schedule = fsrs_schedule(subjects, daily_capacity=daily_cap)
                md = format_fsrs_markdown(schedule)
                path = os.path.join(args.output, "fsrs_plan.md")
            else:
                plan = compute_weeks(args.exam_date, args.daily_hours)
                md = format_plan_markdown(plan)
                path = os.path.join(args.output, "study_plan.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write(md)
            print(f"已生成: {path}（本地算法，未调 API）")
            return 0

        if args.cmd == "mindmap":
            text = parse_file(args.input)
            local = analyze_text(text)
            path = os.path.join(args.output, "mindmap.mmd")
            from .export import to_mermaid
            with open(path, "w", encoding="utf-8") as f:
                f.write(to_mermaid(local["subject_distribution"],
                                   local["top_keywords"]))
            print(f"已生成: {path}")
            if args.html:
                mm_path = os.path.join(args.output, "mindmap.html")
                html = to_markmap_html(local["subject_distribution"],
                                       local["top_keywords"], None)
                with open(mm_path, "w", encoding="utf-8") as f:
                    f.write(html)
                print(f"已生成: {mm_path}（浏览器打开，交互式折叠）")
            return 0

        if args.cmd == "review":
            text = parse_file(args.input)
            cache = AICache(os.path.join(args.output, ".cache.sqlite"))
            result = review_wrong_question(text, cache)
            path = os.path.join(args.output, "review.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write("# 错题复盘\n\n")
                for k, v in result.items():
                    f.write(f"## {k}\n")
                    if isinstance(v, (dict, list)):
                        f.write(f"```json\n{json.dumps(v, ensure_ascii=False, indent=2)}\n```\n")
                    else:
                        f.write(f"{v}\n")
                    f.write("\n")
            print(f"已生成: {path}")
            return 0
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
