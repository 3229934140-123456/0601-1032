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
from .packer import LevelPacker, RenameResult, PackResult, RenameConflict
from .stats import StatsGenerator
from .editor import LevelEditor, EditResult
from .batch_edit import (
    BatchEditor, BatchFilter, BatchResult, PublishConfig, ReleaseDiff
)


def _print_edit_result(result: EditResult):
    """打印编辑结果"""
    if result.success:
        print(result.message)
    else:
        if result.position:
            print(f"❌ [{result.position.x},{result.position.y}] {result.message}")
        else:
            print(f"❌ {result.message}")
    for warning in result.warnings:
        print(f"  ⚠️  {warning}")


def cmd_new(args):
    """new 命令 - 创建或编辑关卡"""
    output_dir = args.output or os.path.join(os.getcwd(), "levels")
    os.makedirs(output_dir, exist_ok=True)

    filepath = os.path.join(output_dir, f"{args.name}.json")
    if os.path.exists(filepath) and not args.force:
        print(f"错误: 关卡文件已存在: {filepath}")
        print("使用 --force 覆盖，或使用 edit 命令修改已有关卡")
        sys.exit(1)

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

    if args.bind_switch:
        for binding in args.bind_switch:
            parts = binding.split(":")
            if len(parts) < 2:
                print(f"  ⚠️  绑定格式错误 '{binding}'，应为 '开关ID:门ID1,门ID2'")
                continue
            try:
                switch_id = int(parts[0])
                door_ids = [int(d) for d in parts[1].split(",")]
                result = LevelEditor.bind_switch_to_doors(level, switch_id, door_ids)
                _print_edit_result(result)
                level = result.level
            except ValueError:
                print(f"  ⚠️  绑定格式错误 '{binding}'，ID 必须是数字")

    if not level.created_at:
        level.created_at = datetime.now().isoformat()

    level.save(output_dir)
    print(f"关卡已保存: {os.path.join(output_dir, level.name)}.json")

    if args.preview:
        print()
        print(TerminalPreview.render(
            level, use_color=not args.no_color, show_ids=args.show_ids
        ))

    if args.check:
        print("\n验证结果:")
        issues = LevelValidator.validate(level)
        if issues:
            for issue in issues:
                print(f"  {issue}")
        else:
            print("  ✓ 所有检查通过")


def cmd_edit(args):
    """edit 命令 - 编辑已有关卡"""
    filepath = args.file

    if not os.path.exists(filepath):
        print(f"错误: 文件不存在: {filepath}")
        sys.exit(1)

    level = Level.load(filepath)
    directory = os.path.dirname(filepath)
    modified = False

    if any([
        args.title is not None, args.chapter is not None, args.hint is not None,
        args.difficulty is not None, args.step_limit is not None,
        args.notes is not None, args.author is not None
    ]):
        level = LevelEditor.set_metadata(
            level,
            title=args.title,
            chapter=args.chapter,
            hint=args.hint,
            difficulty=args.difficulty,
            step_limit=args.step_limit,
            notes=args.notes,
            author=args.author
        )
        modified = True
        print("已更新元数据")

    if args.add_box:
        for coord in args.add_box:
            try:
                x, y = map(int, coord.split(","))
                result = LevelEditor.add_box(level, x, y)
                level = result.level
                _print_edit_result(result)
                if result.success:
                    modified = True
            except ValueError:
                print(f"❌ 坐标格式错误 '{coord}'，应为 x,y")

    if args.remove_box:
        for coord in args.remove_box:
            try:
                if "," in coord:
                    x, y = map(int, coord.split(","))
                    result = LevelEditor.remove_box(level, x, y)
                else:
                    result = LevelEditor.remove_box_by_id(level, int(coord))
                level = result.level
                _print_edit_result(result)
                if result.success:
                    modified = True
            except ValueError:
                print(f"❌ 参数格式错误 '{coord}'")

    if args.add_target:
        for coord in args.add_target:
            try:
                x, y = map(int, coord.split(","))
                result = LevelEditor.add_target(level, x, y)
                level = result.level
                _print_edit_result(result)
                if result.success:
                    modified = True
            except ValueError:
                print(f"❌ 坐标格式错误 '{coord}'，应为 x,y")

    if args.remove_target:
        for coord in args.remove_target:
            try:
                if "," in coord:
                    x, y = map(int, coord.split(","))
                    result = LevelEditor.remove_target(level, x, y)
                else:
                    result = LevelEditor.remove_target_by_id(level, int(coord))
                level = result.level
                _print_edit_result(result)
                if result.success:
                    modified = True
            except ValueError:
                print(f"❌ 参数格式错误 '{coord}'")

    if args.add_wall:
        for coord in args.add_wall:
            try:
                x, y = map(int, coord.split(","))
                result = LevelEditor.add_wall(level, x, y)
                level = result.level
                _print_edit_result(result)
                if result.success:
                    modified = True
            except ValueError:
                print(f"❌ 坐标格式错误 '{coord}'，应为 x,y")

    if args.remove_wall:
        for coord in args.remove_wall:
            try:
                x, y = map(int, coord.split(","))
                result = LevelEditor.remove_wall(level, x, y)
                level = result.level
                _print_edit_result(result)
                if result.success:
                    modified = True
            except ValueError:
                print(f"❌ 坐标格式错误 '{coord}'，应为 x,y")

    if args.set_player:
        try:
            x, y = map(int, args.set_player.split(","))
            result = LevelEditor.set_player(level, x, y)
            level = result.level
            _print_edit_result(result)
            if result.success:
                modified = True
        except ValueError:
            print(f"❌ 坐标格式错误 '{args.set_player}'，应为 x,y")

    if args.add_switch:
        for item in args.add_switch:
            parts = item.split(":")
            coord = parts[0]
            try:
                x, y = map(int, coord.split(","))
                door_ids = []
                if len(parts) > 1 and parts[1]:
                    door_ids = [int(d) for d in parts[1].split(",")]
                result = LevelEditor.add_switch(level, x, y, door_ids=door_ids)
                level = result.level
                _print_edit_result(result)
                if result.success:
                    modified = True
            except ValueError:
                print(f"❌ 参数格式错误 '{item}'")

    if args.remove_switch:
        for coord in args.remove_switch:
            try:
                if "," in coord:
                    x, y = map(int, coord.split(","))
                    result = LevelEditor.remove_switch(level, x, y)
                else:
                    result = LevelEditor.remove_switch_by_id(level, int(coord))
                level = result.level
                _print_edit_result(result)
                if result.success:
                    modified = True
            except ValueError:
                print(f"❌ 参数格式错误 '{coord}'")

    if args.add_door:
        for coord in args.add_door:
            try:
                x, y = map(int, coord.split(","))
                result = LevelEditor.add_door(level, x, y)
                level = result.level
                _print_edit_result(result)
                if result.success:
                    modified = True
            except ValueError:
                print(f"❌ 坐标格式错误 '{coord}'，应为 x,y")

    if args.remove_door:
        for coord in args.remove_door:
            try:
                if "," in coord:
                    x, y = map(int, coord.split(","))
                    result = LevelEditor.remove_door(level, x, y)
                else:
                    result = LevelEditor.remove_door_by_id(level, int(coord))
                level = result.level
                _print_edit_result(result)
                if result.success:
                    modified = True
            except ValueError:
                print(f"❌ 参数格式错误 '{coord}'")

    if args.bind_switch:
        for binding in args.bind_switch:
            parts = binding.split(":")
            if len(parts) < 2:
                print(f"❌ 绑定格式错误 '{binding}'，应为 '开关ID:门ID1,门ID2'")
                continue
            try:
                switch_id = int(parts[0])
                door_ids = [int(d) for d in parts[1].split(",")]
                result = LevelEditor.bind_switch_to_doors(level, switch_id, door_ids)
                level = result.level
                _print_edit_result(result)
                if result.success:
                    modified = True
            except ValueError:
                print(f"❌ 绑定格式错误 '{binding}'，ID 必须是数字")

    if args.add_door_binding:
        for binding in args.add_door_binding:
            parts = binding.split(":")
            if len(parts) < 2:
                print(f"❌ 绑定格式错误 '{binding}'，应为 '开关ID:门ID'")
                continue
            try:
                switch_id = int(parts[0])
                door_id = int(parts[1])
                result = LevelEditor.add_door_binding(level, switch_id, door_id)
                level = result.level
                _print_edit_result(result)
                if result.success:
                    modified = True
            except ValueError:
                print(f"❌ 绑定格式错误 '{binding}'，ID 必须是数字")

    if args.remove_door_binding:
        for binding in args.remove_door_binding:
            parts = binding.split(":")
            if len(parts) < 2:
                print(f"❌ 解绑格式错误 '{binding}'，应为 '开关ID:门ID'")
                continue
            try:
                switch_id = int(parts[0])
                door_id = int(parts[1])
                result = LevelEditor.remove_door_binding(level, switch_id, door_id)
                level = result.level
                _print_edit_result(result)
                if result.success:
                    modified = True
            except ValueError:
                print(f"❌ 解绑格式错误 '{binding}'，ID 必须是数字")

    if args.unbind_switch:
        for switch_id_str in args.unbind_switch:
            try:
                switch_id = int(switch_id_str)
                result = LevelEditor.unbind_switch_doors(level, switch_id)
                level = result.level
                _print_edit_result(result)
                if result.success:
                    modified = True
            except ValueError:
                print(f"❌ 开关 ID 必须是数字: {switch_id_str}")

    if args.toggle_door:
        for door_id_str in args.toggle_door:
            try:
                door_id = int(door_id_str)
                result = LevelEditor.toggle_door(level, door_id)
                level = result.level
                _print_edit_result(result)
                if result.success:
                    modified = True
            except ValueError:
                print(f"❌ 门 ID 必须是数字: {door_id_str}")

    if args.rename:
        old_name = level.name
        new_name = args.rename
        new_filepath = os.path.join(directory, f"{new_name}.json")

        if os.path.exists(new_filepath) and new_name != old_name:
            print(f"❌ 目标名称已存在: {new_filepath}")
        else:
            level.name = new_name
            if old_name != new_name:
                if os.path.exists(filepath):
                    os.remove(filepath)
                print(f"已重命名: {old_name} -> {new_name}")
                modified = True

    if modified:
        level.save(directory)
        save_path = os.path.join(directory, f"{level.name}.json")
        print(f"\n关卡已保存: {save_path}")
    else:
        print("未进行任何修改。")

    if args.preview or args.check:
        print()

    if args.preview:
        print(TerminalPreview.render(
            level, use_color=not args.no_color, show_ids=args.show_ids
        ))

    if args.check:
        print("\n验证结果:")
        issues = LevelValidator.validate(level)
        if issues:
            for issue in issues:
                print(f"  {issue}")
        else:
            print("  ✓ 所有检查通过")


def cmd_batch_edit(args):
    """batch-edit 命令 - 批量修改关卡元数据"""
    directory = args.directory

    if not os.path.isdir(directory):
        print(f"错误: 目录不存在: {directory}")
        sys.exit(1)

    bf = BatchFilter()

    if args.chapter:
        bf.chapters = args.chapter.split(",")
    if args.difficulty_min is not None:
        bf.difficulty_min = args.difficulty_min
    if args.difficulty_max is not None:
        bf.difficulty_max = args.difficulty_max
    if args.missing_title:
        bf.missing_title_only = True
    if args.has_errors:
        bf.has_errors_only = True
    if args.no_step_limit:
        bf.no_step_limit_only = True
    if args.level_names:
        bf.level_names = args.level_names.split(",")

    dry_run = not args.apply

    if dry_run:
        print("=== 批量编辑 (试运行) ===")
    else:
        print("=== 批量编辑 (执行) ===")

    filter_parts = []
    if bf.chapters:
        filter_parts.append(f"章节={bf.chapters}")
    if bf.difficulty_min is not None or bf.difficulty_max is not None:
        filter_parts.append(
            f"难度=[{bf.difficulty_min or '*'}, {bf.difficulty_max or '*'}]"
        )
    if bf.missing_title_only:
        filter_parts.append("仅缺少标题的")
    if bf.has_errors_only:
        filter_parts.append("仅有错误的")
    if bf.no_step_limit_only:
        filter_parts.append("仅无步数限制的")
    if filter_parts:
        print(f"筛选条件: {' & '.join(filter_parts)}")

    result: BatchResult = BatchEditor.batch_edit_metadata(
        directory,
        bf,
        set_chapter=args.set_chapter,
        set_title=args.set_title,
        set_author=args.set_author,
        set_hint=args.set_hint,
        set_notes=args.set_notes,
        set_step_limit=args.set_step_limit,
        set_difficulty=args.set_difficulty,
        difficulty_min=args.auto_diff_min,
        difficulty_max=args.auto_diff_max,
        default_step_limit=args.default_step_limit,
        prepend_title=args.prepend_title,
        append_title=args.append_title,
        dry_run=dry_run
    )

    print(f"总关卡: {result.total}, 匹配条件: {result.matched}, "
          f"已修改: {result.modified}, 跳过: {result.skipped}")
    print()

    for change in result.changes:
        if change.changes:
            status = "[试运行]" if dry_run else "[已修改]"
            print(f"{status} {change.level_name}:")
            for c in change.changes:
                print(f"  - {c}")
        elif change.skipped and args.verbose:
            print(f"[跳过] {change.level_name}: {change.skip_reason}")

    if result.errors:
        print("\n错误:")
        for err in result.errors:
            print(f"  ❌ {err}")

    if not dry_run:
        print(f"\n✅ 已保存 {result.modified} 个关卡。stats/pack 可立即看到最新结果。")


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
        show_ids=args.show_ids,
        show_issues=not args.hide_issues,
        show_bindings=args.bindings
    )
    print(output)

    if args.text:
        print("\n文本地图格式:")
        print(MapParser.to_text_map(level))

    if args.bindings:
        if level.switches:
            print("\n开关-门绑定关系:")
            for switch in level.switches:
                bound = ", ".join(f"#{d}" for d in switch.door_ids) if switch.door_ids else "无"
                print(f"  开关 #{switch.id} @ ({switch.position.x},{switch.position.y}) -> 门: {bound}")
        if level.doors:
            print("\n门列表:")
            for door in level.doors:
                status = "开" if door.is_open else "关"
                print(f"  门 #{door.id} @ ({door.position.x},{door.position.y}) [{status}]")


def cmd_pack(args):
    """pack 命令 - 批量处理关卡"""
    directory = args.directory

    if not os.path.isdir(directory):
        print(f"错误: 目录不存在: {directory}")
        sys.exit(1)

    config = None
    if args.config:
        config = BatchEditor.load_config(args.config)
        if config:
            print(f"已加载发布配置: {args.config}")
            if config.name and not args.pack_name:
                args.pack_name = config.name
            if config.chapters and not args.chapter:
                args.chapter = ",".join(config.chapters)
            if config.skip_with_errors and not args.skip_errors:
                args.skip_errors = True
        else:
            print(f"⚠️  未找到配置文件: {args.config}")

    if args.save_config:
        cfg = PublishConfig(
            name=args.pack_name or "levelpack",
            chapters=args.chapter.split(",") if args.chapter else None,
            skip_with_errors=args.skip_errors,
            include_warnings_in_readme=True,
            default_step_limit=args.default_step_limit if hasattr(args, "default_step_limit") else None,
        )
        BatchEditor.save_config(args.save_config, cfg)
        print(f"发布配置已保存: {args.save_config}")

    if (args.pack_name or args.export_readme or args.skip_errors or args.flat
            or args.output or args.compare_with or args.config) and not args.pack:
        args.pack = True

    release_diff = None
    if args.compare_with:
        print("\n--- 与上次发布对比 ---")
        release_diff = BatchEditor.compare_releases(
            args.compare_with, directory, config
        )
        print(BatchEditor.format_diff(release_diff))
        print()

    if args.rename:
        print("批量重命名关卡...")
        result: RenameResult = LevelPacker.batch_rename(
            directory,
            pattern=args.pattern or "level_{index:03d}",
            start_index=args.start_index or 1,
            chapter_filter=args.chapter.split(",") if args.chapter else None,
            dry_run=args.dry_run,
            force=args.force
        )

        if result.conflicts:
            print("\n⚠️ 发现命名冲突:")
            for conflict in result.conflicts:
                extra = f" (已存在: {conflict.existing_file})" if conflict.existing_file else ""
                print(f"  {conflict.old_name} -> {conflict.proposed_name}: {conflict.conflict_type}{extra}")
            print(f"\n共 {len(result.conflicts)} 个冲突，重命名已中止。使用 --force 强制覆盖。")
            if args.strict:
                sys.exit(1)
        elif result.renamed:
            for old, new in result.renamed:
                print(f"  {old} -> {new}")
            mode = " (试运行)" if args.dry_run else ""
            print(f"\n共重命名 {len(result.renamed)} 个关卡{mode}")
        else:
            print("无需重命名。")

    if args.pack:
        output_dir = args.output or os.path.join(os.getcwd(), "output")
        pack_name = args.pack_name or "levelpack"
        skip_with_errors = args.skip_errors

        if skip_with_errors:
            print(f"\n生成关卡包: {pack_name} (仅打包无 error 关卡)")
        else:
            print(f"\n生成关卡包: {pack_name}")

        pack_result: PackResult = LevelPacker.generate_levelpack(
            directory,
            output_dir,
            pack_name=pack_name,
            include_chapters=not args.flat,
            skip_with_errors=skip_with_errors
        )

        print(f"关卡包已生成: {pack_result.levelpack_path}")
        print(f"  总计: {pack_result.total_levels} 个关卡")
        print(f"  已打包: {pack_result.packed_levels} 个关卡")

        if pack_result.skipped_levels:
            print(f"  已跳过: {len(pack_result.skipped_levels)} 个关卡")
            print("\n跳过的关卡:")

            skipped_by_chapter = {}
            all_levels = LevelPacker.load_all_levels(directory)
            for level_name, reasons in pack_result.skipped_levels:
                level = None
                for lvl in all_levels:
                    if lvl.name == level_name:
                        level = lvl
                        break
                chapter = level.chapter if level else "未分类"
                if chapter not in skipped_by_chapter:
                    skipped_by_chapter[chapter] = []
                skipped_by_chapter[chapter].append((level_name, reasons))

            for chapter in sorted(skipped_by_chapter.keys()):
                print(f"\n  [{chapter}]")
                for level_name, reasons in skipped_by_chapter[chapter]:
                    reason_str = "; ".join(reasons)
                    print(f"    - {level_name}: {reason_str}")

        if args.export_readme:
            from .stats import StatsGenerator
            stats_list = StatsGenerator.analyze_directory(directory)
            if skip_with_errors:
                stats_list = [s for s in stats_list if s.publishable]
            readme_path = StatsGenerator.export_readme(
                stats_list,
                output_dir,
                pack_name=pack_name,
                skip_with_errors=skip_with_errors,
                include_warnings=True,
                release_diff=release_diff
            )
            print(f"\n说明文档已导出: {readme_path}")


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

    release_diff = None
    if args.compare_with:
        if os.path.isdir(target):
            release_diff = BatchEditor.compare_releases(args.compare_with, target)
        print("\n--- 与上次发布对比 ---")
        print(BatchEditor.format_diff(release_diff))
        print()
        if args.list_missing_titles or args.list_unpublishable or args.export_readme:
            pass
        else:
            return

    if args.list_missing_titles:
        missing = StatsGenerator.list_missing_titles(stats_list)
        if missing:
            print(f"缺少标题的关卡 ({len(missing)}):")
            for s in missing:
                chapter = s.chapter or "未分类"
                status = " 🚫" if not s.publishable else ""
                print(f"  [{chapter}] {s.name}{status}")
        else:
            print("✓ 所有关卡都有标题。")
        return

    if args.list_unpublishable:
        unpublishable = [s for s in stats_list if not s.publishable]
        if unpublishable:
            print(f"暂不可发布的关卡 ({len(unpublishable)}):")
            for s in unpublishable:
                chapter = s.chapter or "未分类"
                errors = [i.message for i in s.issues if i.severity == "error"]
                error_str = "; ".join(errors)
                print(f"  [{chapter}] {s.name}: {error_str}")
        else:
            print("✓ 所有关卡都可发布。")
        return

    if args.export_readme:
        output_dir = args.output or os.path.join(os.getcwd(), "output")
        output_file = StatsGenerator.export_readme(
            stats_list,
            output_dir,
            pack_name=args.pack_name or "关卡包",
            skip_with_errors=args.skip_errors,
            include_warnings=True,
            release_diff=release_diff
        )
        print(f"说明文档已导出: {output_file}")
        return

    metrics = StatsGenerator.calculate_difficulty_metrics(stats_list)
    chapters = StatsGenerator.group_by_chapter(stats_list)
    publishable_count = sum(1 for s in stats_list if s.publishable)

    print("=" * 50)
    print("关卡统计报告")
    print("=" * 50)
    print(f"关卡总数:       {metrics.get('total_levels', 0)}")
    print(f"可发布关卡:     {publishable_count}")
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
        unpublishable = sum(1 for s in chapter_stats if not s.publishable)

        print(f"\n{chapter_name} ({len(chapter_stats)} 关)")
        print(f"  平均箱子数: {avg_boxes:.1f}")
        print(f"  平均难度:   {avg_diff}")
        print(f"  可发布:     {len(chapter_stats) - unpublishable}/{len(chapter_stats)}")
        if missing > 0:
            print(f"  缺少标题:   {missing} 个")

    if metrics.get('levels_without_title', 0) > 0:
        missing = StatsGenerator.list_missing_titles(stats_list)
        if missing:
            print("\n缺少标题的关卡:")
            for s in missing:
                chapter = s.chapter or "未分类"
                status = " 🚫" if not s.publishable else ""
                print(f"  [{chapter}] {s.name}{status}")


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
    new_parser.add_argument("--bind-switch", action="append", metavar="SID:DID1,DID2",
                            help="绑定开关到门，可多次使用，格式: 开关ID:门ID1,门ID2")
    new_parser.add_argument("--output", "-o", help="输出目录 (默认: ./levels)")
    new_parser.add_argument("--force", "-f", action="store_true", help="覆盖已存在的关卡文件")
    new_parser.add_argument("--preview", "-p", action="store_true", help="创建后预览")
    new_parser.add_argument("--check", action="store_true", help="创建后验证")
    new_parser.add_argument("--show-ids", action="store_true", help="显示坐标编号")
    new_parser.add_argument("--no-color", action="store_true", help="禁用彩色输出")
    new_parser.set_defaults(func=cmd_new)

    edit_parser = subparsers.add_parser("edit", help="编辑已有关卡")
    edit_parser.add_argument("file", help="关卡 JSON 文件路径")
    edit_parser.add_argument("--rename", help="重命名关卡")
    edit_parser.add_argument("--title", "-t", help="设置关卡标题 (空字符串清除)")
    edit_parser.add_argument("--chapter", "-c", help="设置所属章节")
    edit_parser.add_argument("--hint", help="设置关卡提示")
    edit_parser.add_argument("--difficulty", "-d", type=int, help="设置难度等级 (1-10)")
    edit_parser.add_argument("--author", "-a", help="设置作者")
    edit_parser.add_argument("--step-limit", "-s", type=int, help="设置步数限制 (0 清除)")
    edit_parser.add_argument("--notes", help="设置备注")

    edit_parser.add_argument("--add-box", action="append", metavar="X,Y",
                             help="添加箱子，格式: x,y")
    edit_parser.add_argument("--remove-box", action="append", metavar="X,Y|ID",
                             help="移除箱子，按坐标或ID")
    edit_parser.add_argument("--add-target", action="append", metavar="X,Y",
                             help="添加目标点，格式: x,y")
    edit_parser.add_argument("--remove-target", action="append", metavar="X,Y|ID",
                             help="移除目标点，按坐标或ID")
    edit_parser.add_argument("--add-wall", action="append", metavar="X,Y",
                             help="添加墙，格式: x,y")
    edit_parser.add_argument("--remove-wall", action="append", metavar="X,Y",
                             help="移除墙，格式: x,y")
    edit_parser.add_argument("--set-player", metavar="X,Y",
                             help="设置玩家位置，格式: x,y")

    edit_parser.add_argument("--add-switch", action="append", metavar="X,Y[:DID1,DID2]",
                             help="添加开关(可选绑定门)，格式: x,y 或 x,y:门ID1,门ID2")
    edit_parser.add_argument("--remove-switch", action="append", metavar="X,Y|ID",
                             help="移除开关，按坐标或ID")
    edit_parser.add_argument("--add-door", action="append", metavar="X,Y",
                             help="添加门，格式: x,y")
    edit_parser.add_argument("--remove-door", action="append", metavar="X,Y|ID",
                             help="移除门(自动清理开关绑定)，按坐标或ID")
    edit_parser.add_argument("--toggle-door", action="append", metavar="ID",
                             help="切换门的开关状态")
    edit_parser.add_argument("--bind-switch", action="append", metavar="SID:DID1,DID2",
                             help="替换开关绑定(覆盖全部)，格式: 开关ID:门ID1,门ID2")
    edit_parser.add_argument("--add-door-binding", action="append", metavar="SID:DID",
                             help="追加单个门到开关绑定，格式: 开关ID:门ID")
    edit_parser.add_argument("--remove-door-binding", action="append", metavar="SID:DID",
                             help="从开关绑定中移除单个门，格式: 开关ID:门ID")
    edit_parser.add_argument("--unbind-switch", action="append", metavar="SID",
                             help="解绑开关的所有门连接")

    edit_parser.add_argument("--preview", "-p", action="store_true", help="编辑后预览")
    edit_parser.add_argument("--check", action="store_true", help="编辑后验证")
    edit_parser.add_argument("--show-ids", action="store_true", help="显示坐标编号")
    edit_parser.add_argument("--no-color", action="store_true", help="禁用彩色输出")
    edit_parser.set_defaults(func=cmd_edit)

    batch_parser = subparsers.add_parser("batch-edit", help="批量修改多关卡元数据")
    batch_parser.add_argument("directory", help="关卡目录")
    batch_parser.add_argument("--apply", action="store_true", help="真正执行修改(默认试运行)")
    batch_parser.add_argument("--verbose", "-v", action="store_true", help="显示跳过原因")

    batch_filter = batch_parser.add_argument_group("筛选条件")
    batch_filter.add_argument("--chapter", help="按章节筛选，逗号分隔")
    batch_filter.add_argument("--difficulty-min", type=int, help="难度最小值")
    batch_filter.add_argument("--difficulty-max", type=int, help="难度最大值")
    batch_filter.add_argument("--missing-title", action="store_true", help="仅缺少标题的")
    batch_filter.add_argument("--has-errors", action="store_true", help="仅有验证错误的")
    batch_filter.add_argument("--no-step-limit", action="store_true", help="仅无步数限制的")
    batch_filter.add_argument("--level-names", help="按关卡名筛选，逗号分隔")

    batch_modify = batch_parser.add_argument_group("修改操作")
    batch_modify.add_argument("--set-chapter", help="统一设置章节")
    batch_modify.add_argument("--set-title", help="统一设置标题")
    batch_modify.add_argument("--set-author", help="统一设置作者")
    batch_modify.add_argument("--set-hint", help="统一设置提示")
    batch_modify.add_argument("--set-notes", help="统一设置备注")
    batch_modify.add_argument("--set-step-limit", type=int, help="统一设置步数限制")
    batch_modify.add_argument("--set-difficulty", type=int, help="统一设置难度")
    batch_modify.add_argument("--default-step-limit", type=int, help="给无步数限制的关卡设置默认值")
    batch_modify.add_argument("--auto-diff-min", type=int, help="自动设置难度的最小值")
    batch_modify.add_argument("--auto-diff-max", type=int, help="自动设置难度的最大值(取中间值)")
    batch_modify.add_argument("--prepend-title", help="在标题前追加内容")
    batch_modify.add_argument("--append-title", help="在标题后追加内容")
    batch_parser.set_defaults(func=cmd_batch_edit)

    check_parser = subparsers.add_parser("check", help="检查关卡问题")
    check_parser.add_argument("target", help="关卡文件或目录路径")
    check_parser.add_argument("--strict", action="store_true", help="发现错误时返回非零退出码")
    check_parser.set_defaults(func=cmd_check)

    preview_parser = subparsers.add_parser("preview", help="在终端预览关卡网格")
    preview_parser.add_argument("file", help="关卡 JSON 文件路径")
    preview_parser.add_argument("--show-ids", action="store_true", help="显示坐标编号")
    preview_parser.add_argument("--no-color", action="store_true", help="禁用彩色输出")
    preview_parser.add_argument("--text", "-t", action="store_true", help="同时输出文本地图格式")
    preview_parser.add_argument("--bindings", "-b", action="store_true", help="显示开关门绑定关系")
    preview_parser.add_argument("--hide-issues", action="store_true", help="隐藏叠放和越界问题")
    preview_parser.set_defaults(func=cmd_preview)

    pack_parser = subparsers.add_parser("pack", help="批量处理关卡（重命名、打包、发布）")
    pack_parser.add_argument("directory", help="关卡目录")
    pack_parser.add_argument("--rename", "-r", action="store_true", help="批量重命名关卡")
    pack_parser.add_argument("--pattern", help="命名模式 (默认: level_{index:03d})")
    pack_parser.add_argument("--start-index", type=int, help="起始序号 (默认: 1)")
    pack_parser.add_argument("--chapter", help="仅处理指定章节的关卡，逗号分隔")
    pack_parser.add_argument("--dry-run", action="store_true", help="试运行，不实际修改")
    pack_parser.add_argument("--force", "-f", action="store_true", help="强制覆盖冲突的文件")
    pack_parser.add_argument("--strict", action="store_true", help="发现冲突时返回非零退出码")
    pack_parser.add_argument("--pack", "-p", action="store_true", help="生成关卡包")
    pack_parser.add_argument("--pack-name", help="关卡包名称 (默认: levelpack)")
    pack_parser.add_argument("--flat", action="store_true", help="不按章节分组")
    pack_parser.add_argument("--skip-errors", action="store_true", help="只打包没有 error 的关卡")
    pack_parser.add_argument("--export-readme", action="store_true", help="同时导出说明文档")
    pack_parser.add_argument("--compare-with", metavar="LAST_PACK.json",
                             help="与上次发布的关卡包对比变更")
    pack_parser.add_argument("--config", metavar="CONFIG.json",
                             help="加载发布配置文件")
    pack_parser.add_argument("--save-config", metavar="CONFIG.json",
                             help="保存当前参数为发布配置文件")
    pack_parser.add_argument("--output", "-o", help="输出目录 (默认: ./output)")
    pack_parser.set_defaults(func=cmd_pack)

    stats_parser = subparsers.add_parser("stats", help="统计难度指标并导出说明文档")
    stats_parser.add_argument("target", help="关卡文件或目录路径")
    stats_parser.add_argument("--list-missing-titles", action="store_true", help="列出缺少标题的关卡")
    stats_parser.add_argument("--list-unpublishable", action="store_true", help="列出暂不可发布的关卡")
    stats_parser.add_argument("--export-readme", action="store_true", help="按章节导出说明文档")
    stats_parser.add_argument("--skip-errors", action="store_true", help="文档中仅展示可发布关卡")
    stats_parser.add_argument("--compare-with", metavar="LAST_PACK.json",
                              help="与上次发布的关卡包对比变更")
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
