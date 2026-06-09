"""关卡验证器"""

from typing import List, Set, Tuple, Dict
from collections import deque
from dataclasses import dataclass, field
from .models import Level, Position


@dataclass
class ValidationIssue:
    """验证问题"""
    level: str
    type: str
    severity: str
    message: str
    positions: List[Position] = field(default_factory=list)

    def __str__(self):
        pos_str = ""
        if self.positions:
            pos_str = " 位置: " + ", ".join(f"({p.x},{p.y})" for p in self.positions)
        return f"[{self.severity.upper()}] {self.type}: {self.message}{pos_str}"


class LevelValidator:
    """关卡验证器"""

    DIRECTIONS = [Position(0, -1), Position(0, 1), Position(-1, 0), Position(1, 0)]

    @staticmethod
    def validate(level: Level) -> List[ValidationIssue]:
        """运行所有验证检查"""
        issues: List[ValidationIssue] = []
        issues.extend(LevelValidator.check_duplicate_ids(level))
        issues.extend(LevelValidator.check_box_target_count(level))
        issues.extend(LevelValidator.check_player_position(level))
        issues.extend(LevelValidator.check_unreachable_areas(level))
        issues.extend(LevelValidator.check_dead_spots(level))
        issues.extend(LevelValidator.check_switch_door_links(level))
        issues.extend(LevelValidator.check_overlaps_and_oob(level))
        return issues

    @staticmethod
    def check_overlaps_and_oob(level: Level) -> List[ValidationIssue]:
        """检查格子叠放和越界问题"""
        from .editor import LevelEditor

        issues: List[ValidationIssue] = []
        found = LevelEditor.get_level_issues(level)

        for pos, problems in found:
            for problem in problems:
                severity = "error" if ("叠放" in problem or "越界" in problem) else "warning"
                issues.append(ValidationIssue(
                    level=level.name,
                    type="格子冲突",
                    severity=severity,
                    message=f"位置 ({pos.x},{pos.y}): {problem}",
                    positions=[pos]
                ))

        return issues

    @staticmethod
    def check_duplicate_ids(level: Level) -> List[ValidationIssue]:
        """检查重复编号"""
        issues: List[ValidationIssue] = []

        for name, items in [
            ("箱子", level.boxes),
            ("目标点", level.targets),
            ("开关", level.switches),
            ("门", level.doors),
        ]:
            id_counts: Dict[int, int] = {}
            for item in items:
                id_counts[item.id] = id_counts.get(item.id, 0) + 1

            duplicates = [id_ for id_, count in id_counts.items() if count > 1]
            if duplicates:
                issues.append(ValidationIssue(
                    level=level.name,
                    type="重复编号",
                    severity="error",
                    message=f"{name}存在重复编号: {duplicates}"
                ))

        return issues

    @staticmethod
    def check_box_target_count(level: Level) -> List[ValidationIssue]:
        """检查箱子和目标点数量是否匹配"""
        issues: List[ValidationIssue] = []
        box_count = len(level.boxes)
        target_count = len(level.targets)

        if box_count == 0:
            issues.append(ValidationIssue(
                level=level.name,
                type="配置错误",
                severity="error",
                message="关卡中没有箱子"
            ))
        elif target_count == 0:
            issues.append(ValidationIssue(
                level=level.name,
                type="配置错误",
                severity="error",
                message="关卡中没有目标点"
            ))
        elif box_count != target_count:
            issues.append(ValidationIssue(
                level=level.name,
                type="数量不匹配",
                severity="error",
                message=f"箱子数量({box_count})与目标点数量({target_count})不匹配"
            ))

        return issues

    @staticmethod
    def check_player_position(level: Level) -> List[ValidationIssue]:
        """检查玩家位置是否合法"""
        issues: List[ValidationIssue] = []

        if not level.is_valid_position(level.player):
            issues.append(ValidationIssue(
                level=level.name,
                type="玩家位置错误",
                severity="error",
                message="玩家位置超出关卡边界"
            ))
        elif level.is_wall(level.player):
            issues.append(ValidationIssue(
                level=level.name,
                type="玩家位置错误",
                severity="error",
                message="玩家位置在墙上",
                positions=[level.player]
            ))
        elif not level.is_floor(level.player) and level.get_target_at(level.player) is None:
            issues.append(ValidationIssue(
                level=level.name,
                type="玩家位置错误",
                severity="warning",
                message="玩家不在有效地板上",
                positions=[level.player]
            ))

        return issues

    @staticmethod
    def _get_walkable_positions(level: Level, ignore_doors: bool = False) -> Set[Position]:
        """获取玩家可达的所有位置（BFS）"""
        walkable: Set[Position] = set()

        is_walkable = lambda pos: (
            level.is_valid_position(pos)
            and not level.is_wall(pos)
            and (ignore_doors or not level.is_door(pos) or level.get_door_at(pos).is_open)
            and level.get_box_at(pos) is None
        )

        if not is_walkable(level.player):
            return walkable

        queue = deque([level.player])
        walkable.add(level.player)

        while queue:
            current = queue.popleft()
            for direction in LevelValidator.DIRECTIONS:
                next_pos = current + direction
                if next_pos not in walkable and is_walkable(next_pos):
                    walkable.add(next_pos)
                    queue.append(next_pos)

        return walkable

    @staticmethod
    def check_unreachable_areas(level: Level) -> List[ValidationIssue]:
        """检查不可达区域"""
        issues: List[ValidationIssue] = []
        walkable = LevelValidator._get_walkable_positions(level)

        unreachable_targets: List[Position] = []
        for target in level.targets:
            if target.position not in walkable:
                unreachable_targets.append(target.position)

        if unreachable_targets:
            issues.append(ValidationIssue(
                level=level.name,
                type="不可达区域",
                severity="error",
                message=f"有 {len(unreachable_targets)} 个目标点玩家无法到达",
                positions=unreachable_targets
            ))

        unreachable_boxes: List[Position] = []
        for box in level.boxes:
            can_reach = False
            for direction in LevelValidator.DIRECTIONS:
                approach_pos = box.position - direction
                if approach_pos in walkable:
                    can_reach = True
                    break
            if not can_reach:
                unreachable_boxes.append(box.position)

        if unreachable_boxes:
            issues.append(ValidationIssue(
                level=level.name,
                type="不可达区域",
                severity="warning",
                message=f"有 {len(unreachable_boxes)} 个箱子玩家无法推动",
                positions=unreachable_boxes
            ))

        return issues

    @staticmethod
    def _is_corner(level: Level, pos: Position) -> bool:
        """检查位置是否是墙角（两个相邻方向都是墙）"""
        up = pos + Position(0, -1)
        down = pos + Position(0, 1)
        left = pos + Position(-1, 0)
        right = pos + Position(1, 0)

        wall_up = level.is_wall(up) or not level.is_valid_position(up)
        wall_down = level.is_wall(down) or not level.is_valid_position(down)
        wall_left = level.is_wall(left) or not level.is_valid_position(left)
        wall_right = level.is_wall(right) or not level.is_valid_position(right)

        return (
            (wall_up and wall_left)
            or (wall_up and wall_right)
            or (wall_down and wall_left)
            or (wall_down and wall_right)
        )

    @staticmethod
    def check_dead_spots(level: Level) -> List[ValidationIssue]:
        """检查无解死角（箱子推到墙角但不是目标点）"""
        issues: List[ValidationIssue] = []
        dead_spots: List[Position] = []

        for box in level.boxes:
            if level.get_target_at(box.position):
                continue

            if LevelValidator._is_corner(level, box.position):
                dead_spots.append(box.position)

        for pos in level.floors:
            if level.get_target_at(pos):
                continue
            if level.get_box_at(pos):
                continue

            if LevelValidator._is_corner(level, pos):
                can_box_reach = False
                for direction in LevelValidator.DIRECTIONS:
                    approach_pos = pos - direction
                    push_pos = pos + direction
                    if (
                        level.is_valid_position(approach_pos)
                        and not level.is_wall(approach_pos)
                        and level.is_valid_position(push_pos)
                        and not level.is_wall(push_pos)
                    ):
                        can_box_reach = True
                        break
                if not can_box_reach:
                    dead_spots.append(pos)

        if dead_spots:
            issues.append(ValidationIssue(
                level=level.name,
                type="无解死角",
                severity="warning",
                message=f"发现 {len(dead_spots)} 个无解死角位置",
                positions=dead_spots
            ))

        return issues

    @staticmethod
    def check_switch_door_links(level: Level) -> List[ValidationIssue]:
        """检查开关与门的链接是否有效"""
        issues: List[ValidationIssue] = []

        door_ids = {door.id for door in level.doors}
        all_bound_door_ids: set = set()

        for switch in level.switches:
            invalid_doors = [did for did in switch.door_ids if did not in door_ids]
            if invalid_doors:
                issues.append(ValidationIssue(
                    level=level.name,
                    type="开关门链接错误",
                    severity="warning",
                    message=f"开关 {switch.id} 引用了不存在的门: {invalid_doors}",
                    positions=[switch.position]
                ))

            if not switch.door_ids:
                issues.append(ValidationIssue(
                    level=level.name,
                    type="开关未绑定",
                    severity="warning",
                    message=f"开关 {switch.id} 没有绑定任何门",
                    positions=[switch.position]
                ))
            else:
                all_bound_door_ids.update(switch.door_ids)

        unbound_doors = [door.id for door in level.doors if door.id not in all_bound_door_ids]
        if unbound_doors:
            door_positions = [d.position for d in level.doors if d.id in unbound_doors]
            issues.append(ValidationIssue(
                level=level.name,
                type="门无开关联动",
                severity="warning",
                message=f"以下门没有任何开关联动: {unbound_doors}",
                positions=door_positions
            ))

        if level.switches and not level.doors:
            issues.append(ValidationIssue(
                level=level.name,
                type="配置警告",
                severity="info",
                message="有开关但没有门"
            ))
        elif level.doors and not level.switches:
            issues.append(ValidationIssue(
                level=level.name,
                type="配置警告",
                severity="warning",
                message="有门但没有开关，门无法打开"
            ))

        return issues
