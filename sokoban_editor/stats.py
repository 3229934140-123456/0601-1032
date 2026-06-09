"""难度统计与说明文件导出模块"""

import os
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass
from .models import Level
from .validator import LevelValidator, ValidationIssue


@dataclass
class LevelStats:
    """关卡统计数据"""
    name: str
    title: Optional[str]
    chapter: Optional[str]
    difficulty: Optional[int]
    width: int
    height: int
    box_count: int
    target_count: int
    switch_count: int
    door_count: int
    step_limit: Optional[int]
    area: int
    walkable_area: int
    has_title: bool
    issues: List[ValidationIssue]
    has_errors: bool = False
    publishable: bool = True


class StatsGenerator:
    """统计数据生成器"""

    @staticmethod
    def analyze_level(level: Level) -> LevelStats:
        """分析单个关卡"""
        walkable = LevelValidator._get_walkable_positions(level)
        issues = LevelValidator.validate(level)
        has_errors = any(i.severity == "error" for i in issues)

        return LevelStats(
            name=level.name,
            title=level.title,
            chapter=level.chapter,
            difficulty=level.difficulty,
            width=level.width,
            height=level.height,
            box_count=len(level.boxes),
            target_count=len(level.targets),
            switch_count=len(level.switches),
            door_count=len(level.doors),
            step_limit=level.step_limit,
            area=level.width * level.height,
            walkable_area=len(walkable),
            has_title=bool(level.title and level.title.strip()),
            issues=issues,
            has_errors=has_errors,
            publishable=not has_errors
        )

    @staticmethod
    def analyze_directory(directory: str) -> List[LevelStats]:
        """分析目录下所有关卡"""
        from .packer import LevelPacker

        levels = LevelPacker.load_all_levels(directory)
        return [StatsGenerator.analyze_level(level) for level in levels]

    @staticmethod
    def list_missing_titles(stats_list: List[LevelStats]) -> List[LevelStats]:
        """列出缺少标题的关卡"""
        return [s for s in stats_list if not s.has_title]

    @staticmethod
    def calculate_difficulty_metrics(stats_list: List[LevelStats]) -> Dict:
        """计算整体难度指标"""
        if not stats_list:
            return {}

        total_boxes = sum(s.box_count for s in stats_list)
        total_area = sum(s.area for s in stats_list)
        total_walkable = sum(s.walkable_area for s in stats_list)
        total_issues = sum(len(s.issues) for s in stats_list)

        difficulties = [s.difficulty for s in stats_list if s.difficulty is not None]
        avg_difficulty = sum(difficulties) / len(difficulties) if difficulties else None

        error_count = sum(
            1 for s in stats_list
            for i in s.issues if i.severity == "error"
        )
        warning_count = sum(
            1 for s in stats_list
            for i in s.issues if i.severity == "warning"
        )

        return {
            "total_levels": len(stats_list),
            "total_boxes": total_boxes,
            "total_area": total_area,
            "total_walkable_area": total_walkable,
            "avg_boxes_per_level": total_boxes / len(stats_list),
            "avg_walkable_area": total_walkable / len(stats_list),
            "avg_difficulty": avg_difficulty,
            "total_issues": total_issues,
            "error_count": error_count,
            "warning_count": warning_count,
            "levels_without_title": len(StatsGenerator.list_missing_titles(stats_list))
        }

    @staticmethod
    def group_by_chapter(stats_list: List[LevelStats]) -> Dict[str, List[LevelStats]]:
        """按章节分组"""
        chapters: Dict[str, List[LevelStats]] = defaultdict(list)
        for stats in stats_list:
            chapter = stats.chapter or "未分类"
            chapters[chapter].append(stats)
        return dict(chapters)

    @staticmethod
    def export_readme(
        stats_list: List[LevelStats],
        output_path: str,
        pack_name: str = "关卡包",
        skip_with_errors: bool = False
    ) -> str:
        """按章节导出游戏使用的说明文件"""
        chapters = StatsGenerator.group_by_chapter(stats_list)
        metrics = StatsGenerator.calculate_difficulty_metrics(stats_list)
        missing_titles = StatsGenerator.list_missing_titles(stats_list)

        lines: List[str] = []

        publishable_count = sum(1 for s in stats_list if s.publishable)
        unpublishable = [s for s in stats_list if not s.publishable]

        lines.append(f"# {pack_name} 说明文档")
        lines.append("")
        lines.append("## 概览")
        lines.append("")
        lines.append(f"- 关卡总数: {metrics.get('total_levels', 0)}")
        lines.append(f"- 可发布关卡: {publishable_count}")
        if skip_with_errors:
            lines.append(f"- 已跳过(有错误): {len(unpublishable)}")
        lines.append(f"- 章节数: {len(chapters)}")
        lines.append(f"- 箱子总数: {metrics.get('total_boxes', 0)}")
        lines.append(f"- 平均难度: {metrics.get('avg_difficulty', '未设置'):.1f}" if metrics.get('avg_difficulty') else "- 平均难度: 未设置")
        lines.append(f"- 错误数: {metrics.get('error_count', 0)}")
        lines.append(f"- 警告数: {metrics.get('warning_count', 0)}")
        lines.append(f"- 缺少标题的关卡: {metrics.get('levels_without_title', 0)}")
        lines.append("")

        if unpublishable:
            lines.append("## 🚫 暂不可发布的关卡")
            lines.append("")
            lines.append("以下关卡存在严重错误，发布时将被跳过：")
            lines.append("")
            lines.append("| 章节 | 关卡名 | 标题 | 错误原因 |")
            lines.append("|------|--------|------|----------|")
            for stats in unpublishable:
                chapter = stats.chapter or "未分类"
                title = stats.title or "⚠️ 未设置"
                errors = [i.message for i in stats.issues if i.severity == "error"]
                error_str = "; ".join(errors) if errors else "未知错误"
                lines.append(f"| {chapter} | {stats.name} | {title} | {error_str} |")
            lines.append("")

        if missing_titles:
            lines.append("## ⚠️ 缺少标题的关卡")
            lines.append("")
            for stats in missing_titles:
                chapter = stats.chapter or "未分类"
                status = " 🚫" if not stats.publishable else ""
                lines.append(f"- [{chapter}] {stats.name}{status}")
            lines.append("")

        lines.append("## 章节详情")
        lines.append("")

        for chapter_name in sorted(chapters.keys()):
            chapter_stats = chapters[chapter_name]

            if skip_with_errors:
                chapter_stats = [s for s in chapter_stats if s.publishable]
                if not chapter_stats:
                    continue

            lines.append(f"### {chapter_name}")
            lines.append("")
            lines.append(f"本章节共 {len(chapter_stats)} 个关卡")
            lines.append("")

            lines.append("| 序号 | 状态 | 关卡名 | 标题 | 难度 | 箱子数 | 步数限制 | 提示 |")
            lines.append("|------|------|--------|------|------|--------|----------|------|")

            for idx, stats in enumerate(chapter_stats, 1):
                title = stats.title or "⚠️ 未设置"
                difficulty = str(stats.difficulty) if stats.difficulty is not None else "-"
                step_limit = str(stats.step_limit) if stats.step_limit else "无"
                status = "✅" if stats.publishable else "🚫"

                lines.append(
                    f"| {idx} | {status} | {stats.name} | {title} | {difficulty} | {stats.box_count} | {step_limit} | |"
                )

            lines.append("")
            lines.append("### 关卡说明")
            lines.append("")

            for stats in chapter_stats:
                title = stats.title or stats.name
                status_badge = " 🚫" if not stats.publishable else ""
                lines.append(f"#### {title} (`{stats.name}`){status_badge}")
                lines.append("")

                if not stats.publishable:
                    lines.append("> ⚠️ **注意**: 此关卡存在验证错误，暂不可发布")
                    lines.append("")

                level_info = []
                level_info.append(f"- 尺寸: {stats.width}x{stats.height}")
                level_info.append(f"- 箱子数: {stats.box_count}")
                level_info.append(f"- 目标点数: {stats.target_count}")
                if stats.switch_count > 0:
                    level_info.append(f"- 开关数: {stats.switch_count}")
                if stats.door_count > 0:
                    level_info.append(f"- 门数: {stats.door_count}")
                if stats.step_limit:
                    level_info.append(f"- 步数限制: {stats.step_limit}")
                if stats.difficulty is not None:
                    level_info.append(f"- 难度等级: {stats.difficulty}")

                lines.extend(level_info)

                if stats.issues:
                    lines.append("")
                    lines.append("**验证问题:**")
                    for issue in stats.issues:
                        lines.append(f"- {issue}")

                lines.append("")

        output_file = os.path.join(output_path, f"{pack_name}_README.md")
        os.makedirs(output_path, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return output_file
