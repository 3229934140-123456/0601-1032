"""批量关卡编辑模块"""

import os
import json
from typing import List, Dict, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from .models import Level
from .editor import LevelEditor
from .validator import LevelValidator
from .packer import LevelPacker


@dataclass
class BatchFilter:
    """批量筛选条件"""
    chapters: Optional[List[str]] = None
    difficulty_min: Optional[int] = None
    difficulty_max: Optional[int] = None
    missing_title_only: bool = False
    has_errors_only: bool = False
    no_step_limit_only: bool = False
    level_names: Optional[List[str]] = None

    def matches(self, level: Level) -> bool:
        """判断关卡是否符合筛选条件"""
        if self.level_names and level.name not in self.level_names:
            return False

        if self.chapters and level.chapter not in self.chapters:
            return False

        if self.difficulty_min is not None:
            if level.difficulty is None or level.difficulty < self.difficulty_min:
                return False

        if self.difficulty_max is not None:
            if level.difficulty is None or level.difficulty > self.difficulty_max:
                return False

        if self.missing_title_only and level.title and level.title.strip():
            return False

        if self.no_step_limit_only and level.step_limit is not None:
            return False

        if self.has_errors_only:
            issues = LevelValidator.validate(level)
            if not any(i.severity == "error" for i in issues):
                return False

        return True


@dataclass
class BatchChange:
    """单关卡变更记录"""
    level_name: str
    changes: List[str] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str = ""


@dataclass
class BatchResult:
    """批量编辑结果"""
    total: int = 0
    matched: int = 0
    modified: int = 0
    skipped: int = 0
    changes: List[BatchChange] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class PublishConfig:
    """发布配置"""
    name: str
    chapters: Optional[List[str]] = None
    skip_with_errors: bool = True
    include_warnings_in_readme: bool = True
    default_step_limit: Optional[int] = None
    min_difficulty: Optional[int] = None
    max_difficulty: Optional[int] = None

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "chapters": self.chapters,
            "skip_with_errors": self.skip_with_errors,
            "include_warnings_in_readme": self.include_warnings_in_readme,
            "default_step_limit": self.default_step_limit,
            "min_difficulty": self.min_difficulty,
            "max_difficulty": self.max_difficulty,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "PublishConfig":
        return cls(
            name=data["name"],
            chapters=data.get("chapters"),
            skip_with_errors=data.get("skip_with_errors", True),
            include_warnings_in_readme=data.get("include_warnings_in_readme", True),
            default_step_limit=data.get("default_step_limit"),
            min_difficulty=data.get("min_difficulty"),
            max_difficulty=data.get("max_difficulty"),
        )


@dataclass
class ReleaseDiff:
    """版本差异"""
    added: List[str] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)
    renamed: List[Tuple[str, str]] = field(default_factory=list)
    modified: List[str] = field(default_factory=list)
    unchanged: List[str] = field(default_factory=list)


class BatchEditor:
    """批量编辑器"""

    @staticmethod
    def load_config(config_path: str) -> Optional[PublishConfig]:
        """加载发布配置"""
        if not os.path.exists(config_path):
            return None
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "publish_config" in data:
            return PublishConfig.from_dict(data["publish_config"])
        return PublishConfig.from_dict(data)

    @staticmethod
    def save_config(config_path: str, config: PublishConfig):
        """保存发布配置"""
        data = {
            "publish_config": config.to_dict(),
            "saved_at": datetime.now().isoformat()
        }
        os.makedirs(os.path.dirname(config_path) or ".", exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def filter_levels(levels: List[Level], f: BatchFilter) -> List[Level]:
        """按条件筛选关卡"""
        return [lvl for lvl in levels if f.matches(lvl)]

    @staticmethod
    def batch_edit_metadata(
        directory: str,
        batch_filter: BatchFilter,
        *,
        set_chapter: Optional[str] = None,
        set_title: Optional[str] = None,
        set_author: Optional[str] = None,
        set_hint: Optional[str] = None,
        set_notes: Optional[str] = None,
        set_step_limit: Optional[int] = None,
        set_difficulty: Optional[int] = None,
        difficulty_min: Optional[int] = None,
        difficulty_max: Optional[int] = None,
        default_step_limit: Optional[int] = None,
        prepend_title: Optional[str] = None,
        append_title: Optional[str] = None,
        dry_run: bool = True
    ) -> BatchResult:
        """
        批量编辑关卡元数据

        Args:
            directory: 关卡目录
            batch_filter: 筛选条件
            set_*: 直接设置对应字段
            difficulty_min/max: 为难度在此区间但未设置难度的关卡设置难度
            default_step_limit: 为没有步数限制的关卡设置默认值
            prepend_title/append_title: 在现有标题前后追加内容
            dry_run: 是否为试运行

        Returns:
            BatchResult 批量编辑结果
        """
        result = BatchResult()

        all_levels = LevelPacker.load_all_levels(directory)
        result.total = len(all_levels)

        matched = BatchEditor.filter_levels(all_levels, batch_filter)
        result.matched = len(matched)

        for level in matched:
            change = BatchChange(level_name=level.name)
            original_dict = level.to_dict()

            if set_chapter is not None:
                old = level.chapter
                level.chapter = set_chapter if set_chapter != "" else None
                if old != level.chapter:
                    change.changes.append(f"章节: {old!r} → {level.chapter!r}")

            if set_title is not None:
                old = level.title
                level.title = set_title if set_title != "" else None
                if old != level.title:
                    change.changes.append(f"标题: {old!r} → {level.title!r}")

            if prepend_title and level.title:
                level.title = prepend_title + level.title
                change.changes.append(f"标题前追加: {prepend_title!r}")

            if append_title and level.title:
                level.title = level.title + append_title
                change.changes.append(f"标题后追加: {append_title!r}")

            if set_author is not None:
                old = level.author
                level.author = set_author if set_author != "" else None
                if old != level.author:
                    change.changes.append(f"作者: {old!r} → {level.author!r}")

            if set_hint is not None:
                old = level.hint
                level.hint = set_hint if set_hint != "" else None
                if old != level.hint:
                    change.changes.append(f"提示: {old!r} → {level.hint!r}")

            if set_notes is not None:
                old = level.notes
                level.notes = set_notes if set_notes != "" else None
                if old != level.notes:
                    change.changes.append(f"备注: {old!r} → {level.notes!r}")

            if set_step_limit is not None:
                old = level.step_limit
                level.step_limit = set_step_limit if set_step_limit > 0 else None
                if old != level.step_limit:
                    change.changes.append(f"步数限制: {old} → {level.step_limit}")

            if default_step_limit is not None and level.step_limit is None:
                level.step_limit = default_step_limit
                change.changes.append(f"默认步数限制: None → {default_step_limit}")

            if set_difficulty is not None:
                old = level.difficulty
                level.difficulty = set_difficulty
                if old != level.difficulty:
                    change.changes.append(f"难度: {old} → {level.difficulty}")

            if (difficulty_min is not None and difficulty_max is not None
                    and level.difficulty is None):
                level.difficulty = (difficulty_min + difficulty_max) // 2
                change.changes.append(f"难度(自动): None → {level.difficulty}")

            if change.changes:
                if not dry_run:
                    level.save(directory)
                result.modified += 1
            else:
                change.skipped = True
                change.skip_reason = "无需要修改的字段"
                result.skipped += 1

            result.changes.append(change)

        return result

    @staticmethod
    def load_previous_release(pack_path: str) -> Optional[Dict]:
        """加载上一次发布的关卡包"""
        if not os.path.exists(pack_path):
            return None
        with open(pack_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _extract_level_names_and_hashes(pack_data: Dict) -> Dict[str, str]:
        """从关卡包提取名称和内容哈希"""
        import hashlib

        result: Dict[str, str] = {}

        def process_level(lvl_data: Dict):
            name = lvl_data.get("name", "")
            content = json.dumps(lvl_data, sort_keys=True, ensure_ascii=False)
            h = hashlib.md5(content.encode("utf-8")).hexdigest()[:12]
            result[name] = h

        if "chapters" in pack_data:
            for ch in pack_data["chapters"]:
                for lvl in ch.get("levels", []):
                    process_level(lvl)
        elif "levels" in pack_data:
            for lvl in pack_data["levels"]:
                process_level(lvl)

        return result

    @staticmethod
    def compare_releases(
        previous_pack_path: str,
        current_directory: str,
        config: Optional[PublishConfig] = None
    ) -> ReleaseDiff:
        """
        对比当前关卡与上次发布的差异

        Returns:
            ReleaseDiff 变更明细
        """
        diff = ReleaseDiff()

        prev_pack = BatchEditor.load_previous_release(previous_pack_path)
        if prev_pack is None:
            all_levels = LevelPacker.load_all_levels(current_directory)
            if config:
                bf = BatchFilter(
                    chapters=config.chapters,
                    difficulty_min=config.min_difficulty,
                    difficulty_max=config.max_difficulty
                )
                if config.skip_with_errors:
                    all_levels = [
                        l for l in all_levels
                        if not any(i.severity == "error" for i in LevelValidator.validate(l))
                    ]
                all_levels = BatchEditor.filter_levels(all_levels, bf)
            diff.added = [l.name for l in all_levels]
            return diff

        prev_levels = BatchEditor._extract_level_names_and_hashes(prev_pack)

        current_levels = LevelPacker.load_all_levels(current_directory)
        if config:
            bf = BatchFilter(
                chapters=config.chapters,
                difficulty_min=config.min_difficulty,
                difficulty_max=config.max_difficulty
            )
            if config.skip_with_errors:
                current_levels = [
                    l for l in current_levels
                    if not any(i.severity == "error" for i in LevelValidator.validate(l))
                ]
            current_levels = BatchEditor.filter_levels(current_levels, bf)

        current_hashes: Dict[str, str] = {}
        for lvl in current_levels:
            content = json.dumps(lvl.to_dict(), sort_keys=True, ensure_ascii=False)
            import hashlib
            h = hashlib.md5(content.encode("utf-8")).hexdigest()[:12]
            current_hashes[lvl.name] = h

        prev_names = set(prev_levels.keys())
        curr_names = set(current_hashes.keys())

        only_in_curr = curr_names - prev_names
        only_in_prev = prev_names - curr_names
        in_both = curr_names & prev_names

        prev_removed = list(only_in_prev)
        curr_added = list(only_in_curr)

        possible_renames = []
        for old_name in list(prev_removed):
            old_hash = prev_levels[old_name]
            for new_name in list(curr_added):
                if current_hashes[new_name] == old_hash:
                    possible_renames.append((old_name, new_name))
                    prev_removed.remove(old_name)
                    curr_added.remove(new_name)
                    break

        diff.renamed = possible_renames
        diff.added = sorted(curr_added)
        diff.removed = sorted(prev_removed)

        for name in in_both:
            if prev_levels[name] != current_hashes.get(name):
                diff.modified.append(name)
            else:
                diff.unchanged.append(name)

        diff.modified.sort()
        diff.unchanged.sort()

        return diff

    @staticmethod
    def format_diff(diff: ReleaseDiff) -> str:
        """格式化差异为可读文本"""
        lines = []

        total = len(diff.added) + len(diff.removed) + len(diff.renamed) + len(diff.modified)
        if total == 0:
            return "与上次发布相比，无任何变更。"

        lines.append(f"与上次发布相比，共 {total} 处变更:")

        if diff.added:
            lines.append(f"\n✨ 新增关卡 ({len(diff.added)}):")
            for name in diff.added:
                lines.append(f"  + {name}")

        if diff.removed:
            lines.append(f"\n🗑️  移除关卡 ({len(diff.removed)}):")
            for name in diff.removed:
                lines.append(f"  - {name}")

        if diff.renamed:
            lines.append(f"\n✏️  重命名关卡 ({len(diff.renamed)}):")
            for old, new in diff.renamed:
                lines.append(f"  {old} → {new}")

        if diff.modified:
            lines.append(f"\n🔄 内容修改 ({len(diff.modified)}):")
            for name in diff.modified:
                lines.append(f"  ~ {name}")

        if diff.unchanged:
            lines.append(f"\n✅ 未变更 ({len(diff.unchanged)})")

        return "\n".join(lines)
