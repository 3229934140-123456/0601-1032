"""关卡打包与批量重命名模块"""

import os
import json
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from .models import Level


@dataclass
class PackResult:
    """打包结果"""
    total_levels: int
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
    def batch_rename(
        directory: str,
        pattern: str = "level_{index:03d}",
        start_index: int = 1,
        chapter_filter: Optional[str] = None,
        dry_run: bool = False
    ) -> List[Tuple[str, str]]:
        """
        批量重命名关卡

        Args:
            directory: 关卡目录
            pattern: 命名模式，支持 {index}, {chapter}, {name} 等占位符
            start_index: 起始序号
            chapter_filter: 仅重命名指定章节的关卡
            dry_run: 试运行，不实际重命名

        Returns:
            重命名对列表 (旧名称, 新名称)
        """
        levels = LevelPacker.load_all_levels(directory)

        if chapter_filter:
            levels = [l for l in levels if l.chapter == chapter_filter]

        levels.sort(key=lambda l: (l.chapter or "", l.name))

        renamed: List[Tuple[str, str]] = []
        current_index = start_index

        used_names = set()

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

            used_names.add(new_name)

            if new_name != old_name:
                renamed.append((old_name, new_name))

                if not dry_run:
                    old_path = os.path.join(directory, f"{old_name}.json")
                    new_path = os.path.join(directory, f"{new_name}.json")

                    if os.path.exists(old_path):
                        level.name = new_name
                        level.save(directory)
                        if old_path != new_path:
                            os.remove(old_path)

            current_index += 1

        return renamed

    @staticmethod
    def generate_levelpack(
        directory: str,
        output_path: str,
        pack_name: str = "levelpack",
        include_chapters: bool = True
    ) -> str:
        """
        生成关卡包文件

        Args:
            directory: 关卡目录
            output_path: 输出目录
            pack_name: 关卡包名称
            include_chapters: 是否按章节分组

        Returns:
            生成的关卡包文件路径
        """
        levels = LevelPacker.load_all_levels(directory)

        os.makedirs(output_path, exist_ok=True)

        if include_chapters:
            chapters: Dict[str, List[Dict]] = {}
            for level in levels:
                chapter = level.chapter or "未分类"
                if chapter not in chapters:
                    chapters[chapter] = []
                chapters[chapter].append(level.to_dict())

            levelpack = {
                "name": pack_name,
                "version": "1.0",
                "level_count": len(levels),
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
                "level_count": len(levels),
                "levels": [level.to_dict() for level in levels]
            }

        output_file = os.path.join(output_path, f"{pack_name}.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(levelpack, f, ensure_ascii=False, indent=2)

        return output_file
