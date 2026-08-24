"""命令行入口：python -m kaoyan_toolkit <analyze|plan|mindmap|review>"""
import argparse
import os
import sys
from datetime import date

from .ai import analyze_subjects, generate_plan, review_wrong_question
from .analyze import analyze_text
from .cache import AICache
from .export import to_markdown
from .parse import parse_file
from .planner import compute_weeks, format_plan_markdown


def _validate_date(s: str) -> str:
    """验证日期格式 YYYY-MM-DD。"""
    try:
        date.fromisoformat(s)
        return s
    except ValueError:
        raise argparse.ArgumentTypeError(f"日期格式错误: '{s}'，应为 YYYY-MM-DD")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="kaoyan-toolkit",
        description="考研 AI 备考工作台 —— 考点分析 / 复习规划 / 思维导图 / 错题复盘",
    )
    parser.add_argument(
        "--version", action="version", version="%(prog)s 0.2.0"
    )
    sub = parser.add_subparsers(dest="cmd")

    # analyze
    pa = sub.add_parser("analyze", help="考点分析（需 API）")
    pa.add_argument("input", help="真题/资料文件 (txt/pdf/docx)")
    pa.add_argument("-o", "--output", default="output")
    pa.add_argument("--no-ai", action="store_true", help="仅本地统计，不调用 AI")

    # plan
    pp = sub.add_parser("plan", help="复习规划（纯本地）")
    pp.add_argument("--exam-date", required=True, type=_validate_date,
                    help="考试日期 YYYY-MM-DD")
    pp.add_argument("--daily-hours", type=float, default=4.0,
                    help="每天可用小时（默认 4）")
    pp.add_argument("-o", "--output", default="output")

    # mindmap
    pm = sub.add_parser("mindmap", help="思维导图导出")
    pm.add_argument("input", help="真题/资料文件")
    pm.add_argument("-o", "--output", default="output")

    # review
    pr = sub.add_parser("review", help="错题复盘（需 API）")
    pr.add_argument("input", help="错题文本文件")
    pr.add_argument("-o", "--output", default="output")

    # cache
    pc = sub.add_parser("cache", help="缓存管理")
    pc.add_argument("--clear", action="store_true", help="清空全部缓存")
    pc.add_argument("--stats", action="store_true", help="显示缓存统计")
    pc.add_argument("-o", "--output", default="output")

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
            print(f"缓存路径: {os.path.join(args.output, '.cache.sqlite')}")
            print(f"缓存条目: {cache.size}")
        return 0

    os.makedirs(args.output, exist_ok=True)

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
        return 0

    if args.cmd == "plan":
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
        mm = local["subject_distribution"]
        path = os.path.join(args.output, "mindmap.mmd")
        from .export import to_mermaid
        with open(path, "w", encoding="utf-8") as f:
            f.write(to_mermaid(mm))
        print(f"已生成: {path}")
        return 0

    if args.cmd == "review":
        text = parse_file(args.input)
        cache = AICache(os.path.join(args.output, ".cache.sqlite"))
        result = review_wrong_question(text, cache)
        path = os.path.join(args.output, "review.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write("# 错题复盘\n\n")
            for k, v in result.items():
                f.write(f"## {k}\n{v}\n\n")
        print(f"已生成: {path}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
