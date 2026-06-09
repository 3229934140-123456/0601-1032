"""关卡打包与批量重命名模块"""

import os
import json
import re
import uuid
import shutil
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from .models import Level
from .validator import LevelValidator, ValidationIssue


@dataclass
class RenameConflict:
    """重命名冲突"""
    old_name: str
    proposed_name: str
    conflict_type: str
    existing_file: Optional[str] = None


@dataclass
class RenameResult:
    """重命名结果"""
    renamed: List[Tuple[str, str]] = field(default_factory=list)
    conflicts: List[RenameConflict] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)


@dataclass
class PackResult:
    """打包结果"""
    total_levels: int
    packed_levels: int
    skipped_levels: List[Tuple[str, List[str]]]
    renamed_levels: List[Tuple[str, str]]
    output_path: str
    levelpack_path: str


class LevelPacker:
    """关卡打包器"""

    @staticmethod
    def load_all_levels(directory: str) -> List[Level]:
        """加载目录下所有关卡"""
        levels: List[Level] = []

        if not os.path.exists(directory):
            return levels

        for filename in sorted(os.listdir(directory)):
            if filename.endswith(".json"):
                filepath = os.path.join(directory, filename)
                try:
                    level = Level.load(filepath)
                    levels.append(level)
                except Exception as e:
                    print(f"警告: 无法加载 {filename}: {e}")

        return levels

    @staticmethod
    def _plan_renames(
        levels: List[Level],
        directory: str,
        pattern: str,
        start_index: int,
        chapter_filter: Optional[str] = None
    ) -> Tuple[List[Tuple[Level, str]], List[RenameConflict]]:
        """
        规划重命名方案，并进行冲突预检

        Returns:
            (重命名计划列表[(Level, new_name)], 冲突列表)
        """
        if chapter_filter:
            levels = [l for l in levels if l.chapter == chapter_filter]

        levels.sort(key=lambda l: (l.chapter or "", l.name))

        all_existing_names = set()
        for fname in os.listdir(directory):
            if fname.endswith(".json"):
                name = fname[:-5]
                all_existing_names.add(name)

        to_rename_names = {l.name for l in levels}
        used_names: set = set()
        plan: List[Tuple[Level, str]] = []
        conflicts: List[RenameConflict] = []
        current_index = start_index

        for level in levels:
            old_name = level.name
            chapter = level.chapter or ""

            new_name = pattern.format(
                index=current_index,
                chapter=chapter,
                name=old_name,
                title=level.title or old_name
            )

            while new_name in used_names:
                current_index += 1
                new_name = pattern.format(
                    index=current_index,
                    chapter=chapter,
                    name=old_name,
                    title=level.title or old_name
                )

            if new_name != old_name:
                if new_name in all_existing_names and new_name not in to_rename_names:
                    conflicts.append(RenameConflict(
                        old_name=old_name,
                        proposed_name=new_name,
                        conflict_type="目标名称已被外部关卡占用",
                        existing_file=f"{new_name}.json"
                    ))
                elif new_name in used_names:
                    conflicts.append(RenameConflict(
                        old_name=old_name,
                        proposed_name=new_name,
                        conflict_type="命名模式产生重复名称"
                    ))
                else:
                    plan.append((level, new_name))

            used_names.add(new_name)
            current_index += 1

        return plan, conflicts

    @staticmethod
    def batch_rename(
        directory: str,
        pattern: str = "level_{index:03d}",
        start_index: int = 1,
        chapter_filter: Optional[str] = None,
        dry_run: bool = False,
        force: bool = False
    ) -> RenameResult:
        """
        批量重命名关卡（安全版）

        流程：
        1. 预检：检查新名称是否与目录中已有非重命名关卡冲突
        2. 若有冲突，列出清单并停止（除非 --force）
        3. 执行时用临时名过渡，确保 JSON 内部关卡名与文件名一致

        Args:
            directory: 关卡目录
            pattern: 命名模式，支持 {index}, {chapter}, {name} 等占位符
            start_index: 起始序号
            chapter_filter: 仅重命名指定章节的关卡
            dry_run: 试运行，不实际重命名
            force: 强制覆盖冲突的已有文件（不推荐）

        Returns:
            RenameResult 包含重命名对、冲突和跳过列表
        """
        result = RenameResult()

        all_levels = LevelPacker.load_all_levels(directory)
        plan, conflicts = LevelPacker._plan_renames(
            all_levels, directory, pattern, start_index, chapter_filter
        )
        result.conflicts = conflicts

        if conflicts and not force:
            for level, _ in plan:
                result.skipped.append(level.name)
            return result

        if dry_run:
            for level, new_name in plan:
                result.renamed.append((level.name, new_name))
            return result

        temp_suffix = f"__tmp_{uuid.uuid4().hex[:8]}__"
        temp_paths: Dict[str, str] = {}

        try:
            for level, new_name in plan:
                old_name = level.name
                old_path = os.path.join(directory, f"{old_name}.json")
                temp_path = os.path.join(directory, f"{old_name}{temp_suffix}.json")

                if not os.path.exists(old_path):
                    result.skipped.append(old_name)
                    continue

                shutil.copy2(old_path, temp_path)
                temp_paths[old_name] = temp_path

            for level, new_name in plan:
                old_name = level.name
                temp_path = temp_paths.get(old_name)
                new_path = os.path.join(directory, f"{new_name}.json")

                if not temp_path or not os.path.exists(temp_path):
                    result.skipped.append(old_name)
                    continue

                level_to_save = Level.load(temp_path)
                level_to_save.name = new_name
                level_to_save.save(directory)

                if os.path.exists(temp_path):
                    os.remove(temp_path)

                old_path = os.path.join(directory, f"{old_name}.json")
                if os.path.exists(old_path) and os.path.abspath(old_path) != os.path.abspath(new_path):
                    os.remove(old_path)

                result.renamed.append((old_name, new_name))

        finally:
            for temp_path in temp_paths.values():
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        return result

    @staticmethod
    def generate_levelpack(
        directory: str,
        output_path: str,
        pack_name: str = "levelpack",
        include_chapters: bool = True,
        skip_with_errors: bool = False
    ) -> PackResult:
        """
        生成关卡包文件（支持发布前检查）

        Args:
            directory: 关卡目录
            output_path: 输出目录
            pack_name: 关卡包名称
            include_chapters: 是否按章节分组
            skip_with_errors: 只打包没有 error 的关卡

        Returns:
            PackResult 打包结果
        """
        all_levels = LevelPacker.load_all_levels(directory)
        os.makedirs(output_path, exist_ok=True)

        packed_levels: List[Level] = []
        skipped: List[Tuple[str, List[str]]] = []

        for level in all_levels:
            if skip_with_errors:
                issues = LevelValidator.validate(level)
                errors = [i for i in issues if i.severity == "error"]
                if errors:
                    skipped.append((
                        level.name,
                        [e.message for e in errors]
                    ))
                    continue
            packed_levels.append(level)

        if include_chapters:
            chapters: Dict[str, List[Dict]] = {}
            for level in packed_levels:
                chapter = level.chapter or "未分类"
                if chapter not in chapters:
                    chapters[chapter] = []
                chapters[chapter].append(level.to_dict())

            levelpack = {
                "name": pack_name,
                "version": "1.0",
                "level_count": len(packed_levels),
                "total_levels": len(all_levels),
                "skipped_count": len(skipped),
                "chapters": [
                    {
                        "name": chapter_name,
                        "levels": chapter_levels
                    }
                    for chapter_name, chapter_levels in sorted(chapters.items())
                ]
            }
        else:
            levelpack = {
                "name": pack_name,
                "version": "1.0",
                "level_count": len(packed_levels),
                "total_levels": len(all_levels),
                "skipped_count": len(skipped),
                "levels": [level.to_dict() for level in packed_levels]
            }

        if skipped:
            skipped_by_chapter: Dict[str, List[Dict]] = {}
            for level_name, reasons in skipped:
                level = next((l for l in all_levels if l.name == level_name), None)
                chapter = level.chapter if level else "未分类"
                if chapter not in skipped_by_chapter:
                    skipped_by_chapter[chapter] = []
                skipped_by_chapter[chapter].append({
                    "name": level_name,
                    "reasons": reasons
                })
            levelpack["skipped_levels"] = [
                {
                    "chapter": ch,
                    "levels": lvls
                }
                for ch, lvls in sorted(skipped_by_chapter.items())
            ]

        output_file = os.path.join(output_path, f"{pack_name}.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(levelpack, f, ensure_ascii=False, indent=2)

        return PackResult(
            total_levels=len(all_levels),
            packed_levels=len(packed_levels),
            skipped_levels=skipped,
            renamed_levels=[],
            output_path=output_path,
            levelpack_path=output_file
        )
