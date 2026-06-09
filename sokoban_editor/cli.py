"""命令行接口"""

import argparse
import os
import sys
from datetime import datetime
from typing import List, Optional

from .models import Level, Position, Box, Target, Switch, Door
from .parser import MapParser
from .validator import LevelValidator, ValidationIssue
from .preview import TerminalPreview
from .packer import LevelPacker
from .stats import StatsGenerator


def cmd_new(args):
    """new 命令 - 创建或编辑关卡"""
    output_dir = args.output or os.path.join(os.getcwd(), "levels")
    os.makedirs(output_dir, exist_ok=True)

    if args.from_map:
        if not os.path.exists(args.from_map):
            print(f"错误: 地图文件不存在: {args.from_map}")
            sys.exit(1)
        level = MapParser.from_file(args.from_map, args.name)
        print(f"已从文本地图导入: {args.from_map}")
    else:
        level = Level(
            name=args.name,
            width=args.width or 10,
            height=args.height or 10
        )
        print(f"已创建空白关卡: {level.width}x{level.height}")

    if args.title:
        level.title = args.title
    if args.chapter:
        level.chapter = args.chapter
    if args.hint:
        level.hint = args.hint
    if args.difficulty is not None:
        level.difficulty = args.difficulty
    if args.author:
        level.author = args.author
    if args.step_limit is not None:
        level.step_limit = args.step_limit
    if args.notes:
        level.notes = args.notes

    if not level.created_at:
        level.created_at = datetime.now().isoformat()

    level.save(output_dir)
    print(f"关卡已保存: {os.path.join(output_dir, level.name)}.json")

    if args.preview:
        print()
        print(TerminalPreview.render(level, use_color=not args.no_color, show_ids=args.show_ids))


def cmd_check(args):
    """check 命令 - 验证关卡"""
    target = args.target
    issues: List[ValidationIssue] = []

    if os.path.isdir(target):
        levels = LevelPacker.load_all_levels(target)
        if not levels:
            print(f"警告: 目录中没有找到关卡文件: {target}")
            sys.exit(0)

        print(f"正在检查 {len(levels)} 个关卡...\n")
        for level in levels:
            level_issues = LevelValidator.validate(level)
            issues.extend(level_issues)
            if level_issues:
                print(f"--- 关卡 {level.name} ---")
                for issue in level_issues:
                    print(f"  {issue}")
                print()
    else:
        if not os.path.exists(target):
            print(f"错误: 文件不存在: {target}")
            sys.exit(1)

        level = Level.load(target)
        print(f"正在检查关卡: {level.name}\n")
        issues = LevelValidator.validate(level)
        for issue in issues:
            print(issue)

    if not issues:
        print("✓ 所有检查通过，未发现问题。")
        sys.exit(0)
    else:
        error_count = sum(1 for i in issues if i.severity == "error")
        warning_count = sum(1 for i in issues if i.severity == "warning")
        info_count = sum(1 for i in issues if i.severity == "info")

        print(f"\n总计: {len(issues)} 个问题 "
              f"(错误: {error_count}, 警告: {warning_count}, 信息: {info_count})")

        if error_count > 0 and args.strict:
            sys.exit(1)


def cmd_preview(args):
    """preview 命令 - 在终端预览关卡"""
    filepath = args.file

    if not os.path.exists(filepath):
        print(f"错误: 文件不存在: {filepath}")
        sys.exit(1)

    level = Level.load(filepath)
    output = TerminalPreview.render(
        level,
        use_color=not args.no_color,
        show_ids=args.show_ids
    )
    print(output)

    if args.text:
        print("\n文本地图格式:")
        print(MapParser.to_text_map(level))


def cmd_pack(args):
    """pack 命令 - 批量处理关卡"""
    directory = args.directory

    if not os.path.isdir(directory):
        print(f"错误: 目录不存在: {directory}")
        sys.exit(1)

    if args.rename:
        print("批量重命名关卡...")
        renamed = LevelPacker.batch_rename(
            directory,
            pattern=args.pattern or "level_{index:03d}",
            start_index=args.start_index or 1,
            chapter_filter=args.chapter,
            dry_run=args.dry_run
        )

        if renamed:
            for old, new in renamed:
                print(f"  {old} -> {new}")
            print(f"\n共重命名 {len(renamed)} 个关卡" + (" (试运行)" if args.dry_run else ""))
        else:
            print("无需重命名。")

    if args.pack:
        output_dir = args.output or os.path.join(os.getcwd(), "output")
        print(f"\n生成关卡包: {args.pack_name or 'levelpack'}")
        pack_path = LevelPacker.generate_levelpack(
            directory,
            output_dir,
            pack_name=args.pack_name or "levelpack",
            include_chapters=not args.flat
        )
        print(f"关卡包已生成: {pack_path}")


def cmd_stats(args):
    """stats 命令 - 统计与导出"""
    target = args.target

    if os.path.isdir(target):
        stats_list = StatsGenerator.analyze_directory(target)
    else:
        if not os.path.exists(target):
            print(f"错误: 文件不存在: {target}")
            sys.exit(1)
        level = Level.load(target)
        stats_list = [StatsGenerator.analyze_level(level)]

    if not stats_list:
        print("未找到关卡数据。")
        sys.exit(0)

    if args.list_missing_titles:
        missing = StatsGenerator.list_missing_titles(stats_list)
        if missing:
            print(f"缺少标题的关卡 ({len(missing)}):")
            for s in missing:
                chapter = s.chapter or "未分类"
                print(f"  [{chapter}] {s.name}")
        else:
            print("✓ 所有关卡都有标题。")
        return

    if args.export_readme:
        output_dir = args.output or os.path.join(os.getcwd(), "output")
        output_file = StatsGenerator.export_readme(
            stats_list,
            output_dir,
            pack_name=args.pack_name or "关卡包"
        )
        print(f"说明文档已导出: {output_file}")
        return

    metrics = StatsGenerator.calculate_difficulty_metrics(stats_list)
    chapters = StatsGenerator.group_by_chapter(stats_list)

    print("=" * 50)
    print("关卡统计报告")
    print("=" * 50)
    print(f"关卡总数:       {metrics.get('total_levels', 0)}")
    print(f"章节数:         {len(chapters)}")
    print(f"箱子总数:       {metrics.get('total_boxes', 0)}")
    print(f"平均每关箱子:   {metrics.get('avg_boxes_per_level', 0):.1f}")
    print(f"平均可行走面积: {metrics.get('avg_walkable_area', 0):.1f}")
    if metrics.get('avg_difficulty'):
        print(f"平均难度:       {metrics.get('avg_difficulty'):.1f}")
    print(f"验证错误:       {metrics.get('error_count', 0)}")
    print(f"验证警告:       {metrics.get('warning_count', 0)}")
    print(f"缺少标题:       {metrics.get('levels_without_title', 0)}")
    print()

    print("按章节统计:")
    print("-" * 50)
    for chapter_name in sorted(chapters.keys()):
        chapter_stats = chapters[chapter_name]
        avg_boxes = sum(s.box_count for s in chapter_stats) / len(chapter_stats)
        difficulties = [s.difficulty for s in chapter_stats if s.difficulty is not None]
        avg_diff = sum(difficulties) / len(difficulties) if difficulties else "-"
        missing = sum(1 for s in chapter_stats if not s.has_title)

        print(f"\n{chapter_name} ({len(chapter_stats)} 关)")
        print(f"  平均箱子数: {avg_boxes:.1f}")
        print(f"  平均难度:   {avg_diff}")
        if missing > 0:
            print(f"  缺少标题:   {missing} 个")

    if args.list_missing_titles or metrics.get('levels_without_title', 0) > 0:
        missing = StatsGenerator.list_missing_titles(stats_list)
        if missing:
            print("\n缺少标题的关卡:")
            for s in missing:
                chapter = s.chapter or "未分类"
                print(f"  [{chapter}] {s.name}")


def build_parser():
    """构建命令行解析器"""
    parser = argparse.ArgumentParser(
        prog="sokoban-editor",
        description="推箱子类益智解谜关卡编辑命令行工具"
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    new_parser = subparsers.add_parser("new", help="创建新关卡草稿或导入文本地图")
    new_parser.add_argument("name", help="关卡名称（文件名）")
    new_parser.add_argument("--from-map", "-m", help="从文本格式地图文件导入")
    new_parser.add_argument("--width", "-W", type=int, help="关卡宽度")
    new_parser.add_argument("--height", "-H", type=int, help="关卡高度")
    new_parser.add_argument("--title", "-t", help="关卡标题")
    new_parser.add_argument("--chapter", "-c", help="所属章节")
    new_parser.add_argument("--hint", help="关卡提示")
    new_parser.add_argument("--difficulty", "-d", type=int, help="难度等级 (1-10)")
    new_parser.add_argument("--author", "-a", help="作者")
    new_parser.add_argument("--step-limit", "-s", type=int, help="步数限制")
    new_parser.add_argument("--notes", help="备注")
    new_parser.add_argument("--output", "-o", help="输出目录 (默认: ./levels)")
    new_parser.add_argument("--preview", "-p", action="store_true", help="创建后预览")
    new_parser.add_argument("--show-ids", action="store_true", help="显示坐标编号")
    new_parser.add_argument("--no-color", action="store_true", help="禁用彩色输出")
    new_parser.set_defaults(func=cmd_new)

    check_parser = subparsers.add_parser("check", help="检查关卡问题")
    check_parser.add_argument("target", help="关卡文件或目录路径")
    check_parser.add_argument("--strict", action="store_true", help="发现错误时返回非零退出码")
    check_parser.set_defaults(func=cmd_check)

    preview_parser = subparsers.add_parser("preview", help="在终端预览关卡网格")
    preview_parser.add_argument("file", help="关卡 JSON 文件路径")
    preview_parser.add_argument("--show-ids", action="store_true", help="显示坐标编号")
    preview_parser.add_argument("--no-color", action="store_true", help="禁用彩色输出")
    preview_parser.add_argument("--text", "-t", action="store_true", help="同时输出文本地图格式")
    preview_parser.set_defaults(func=cmd_preview)

    pack_parser = subparsers.add_parser("pack", help="批量处理关卡（重命名、打包）")
    pack_parser.add_argument("directory", help="关卡目录")
    pack_parser.add_argument("--rename", "-r", action="store_true", help="批量重命名关卡")
    pack_parser.add_argument("--pattern", help="命名模式 (默认: level_{index:03d})")
    pack_parser.add_argument("--start-index", type=int, help="起始序号 (默认: 1)")
    pack_parser.add_argument("--chapter", help="仅处理指定章节的关卡")
    pack_parser.add_argument("--dry-run", action="store_true", help="试运行，不实际重命名")
    pack_parser.add_argument("--pack", "-p", action="store_true", help="生成关卡包")
    pack_parser.add_argument("--pack-name", help="关卡包名称 (默认: levelpack)")
    pack_parser.add_argument("--flat", action="store_true", help="不按章节分组")
    pack_parser.add_argument("--output", "-o", help="输出目录 (默认: ./output)")
    pack_parser.set_defaults(func=cmd_pack)

    stats_parser = subparsers.add_parser("stats", help="统计难度指标并导出说明文档")
    stats_parser.add_argument("target", help="关卡文件或目录路径")
    stats_parser.add_argument("--list-missing-titles", action="store_true", help="列出缺少标题的关卡")
    stats_parser.add_argument("--export-readme", action="store_true", help="按章节导出说明文档")
    stats_parser.add_argument("--pack-name", help="关卡包名称（用于文档标题）")
    stats_parser.add_argument("--output", "-o", help="输出目录 (默认: ./output)")
    stats_parser.set_defaults(func=cmd_stats)

    return parser


def main():
    """主入口"""
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
