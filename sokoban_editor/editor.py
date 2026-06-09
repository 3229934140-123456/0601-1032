"""关卡编辑器模块"""

from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass, field
from .models import Level, Position, Box, Target, Switch, Door


@dataclass
class EditResult:
    """编辑操作结果"""
    level: Level
    success: bool
    message: str = ""
    position: Optional[Position] = None
    warnings: List[str] = field(default_factory=list)


class LevelEditor:
    """关卡编辑器"""

    MAX_COORD = 1000

    @staticmethod
    def _validate_coordinate(x: int, y: int, max_extent: int = MAX_COORD) -> Optional[str]:
        """验证坐标是否合法"""
        if x < 0 or y < 0:
            return f"坐标为负数: ({x},{y})"
        if x > max_extent or y > max_extent:
            return f"坐标超出合理范围 ({max_extent}): ({x},{y})"
        return None

    @staticmethod
    def _check_overlap(level: Level, pos: Position, exclude: str = None) -> List[str]:
        """检查位置是否有叠放冲突"""
        conflicts = []

        if exclude != "wall" and level.is_wall(pos):
            conflicts.append("墙")

        if exclude != "box" and level.get_box_at(pos):
            conflicts.append("箱子")

        if exclude != "target" and level.get_target_at(pos):
            conflicts.append("目标点")

        if exclude != "switch" and level.get_switch_at(pos):
            conflicts.append("开关")

        if exclude != "door" and level.get_door_at(pos):
            conflicts.append("门")

        if exclude != "player" and level.player == pos:
            conflicts.append("玩家")

        return conflicts

    @staticmethod
    def _find_invalid_positions(level: Level) -> List[Tuple[Position, List[str]]]:
        """找出关卡中所有越界或叠放的位置"""
        issues: List[Tuple[Position, List[str]]] = []

        all_positions: Dict[Position, List[str]] = {}

        def add(pos: Position, name: str):
            if pos not in all_positions:
                all_positions[pos] = []
            all_positions[pos].append(name)

        for pos in level.walls:
            if pos.x < 0 or pos.y < 0 or pos.x >= level.width or pos.y >= level.height:
                issues.append((pos, [f"墙越界({level.width}x{level.height})"]))
            add(pos, "墙")

        for pos in level.floors:
            add(pos, "地板")

        for box in level.boxes:
            pos = box.position
            if pos.x < 0 or pos.y < 0 or pos.x >= level.width or pos.y >= level.height:
                issues.append((pos, [f"箱子越界({level.width}x{level.height})"]))
            add(pos, f"箱子#{box.id}")

        for target in level.targets:
            pos = target.position
            if pos.x < 0 or pos.y < 0 or pos.x >= level.width or pos.y >= level.height:
                issues.append((pos, [f"目标点越界({level.width}x{level.height})"]))
            add(pos, f"目标点#{target.id}")

        for switch in level.switches:
            pos = switch.position
            if pos.x < 0 or pos.y < 0 or pos.x >= level.width or pos.y >= level.height:
                issues.append((pos, [f"开关越界({level.width}x{level.height})"]))
            add(pos, f"开关#{switch.id}")

        for door in level.doors:
            pos = door.position
            if pos.x < 0 or pos.y < 0 or pos.x >= level.width or pos.y >= level.height:
                issues.append((pos, [f"门越界({level.width}x{level.height})"]))
            add(pos, f"门#{door.id}")

        pos = level.player
        if pos.x < 0 or pos.y < 0 or pos.x >= level.width or pos.y >= level.height:
            issues.append((pos, [f"玩家越界({level.width}x{level.height})"]))
        add(pos, "玩家")

        for pos, items in all_positions.items():
            wall_count = sum(1 for i in items if i == "墙")
            box_count = sum(1 for i in items if i.startswith("箱子"))
            target_count = sum(1 for i in items if i.startswith("目标点"))
            switch_count = sum(1 for i in items if i.startswith("开关"))
            door_count = sum(1 for i in items if i.startswith("门"))
            player_count = sum(1 for i in items if i == "玩家")

            overlaps = []
            if wall_count > 0 and (box_count > 0 or switch_count > 0 or door_count > 0 or player_count > 0):
                overlaps.append("墙与其他元素叠放")
            if door_count > 0 and box_count > 0:
                overlaps.append("门和箱子叠放")
            if switch_count > 0 and player_count > 0:
                overlaps.append("玩家和开关重叠")
            if box_count > 1:
                overlaps.append(f"多个箱子叠放({box_count}个)")
            if switch_count > 1:
                overlaps.append(f"多个开关叠放({switch_count}个)")
            if door_count > 1:
                overlaps.append(f"多个门叠放({door_count}个)")

            if overlaps:
                existing = next((i for p, i in issues if p == pos), None)
                if existing:
                    existing.extend(overlaps)
                else:
                    issues.append((pos, overlaps))

        return issues

    @staticmethod
    def get_level_issues(level: Level) -> List[Tuple[Position, List[str]]]:
        """获取关卡所有叠放和越界问题"""
        return LevelEditor._find_invalid_positions(level)

    @staticmethod
    def set_metadata(
        level: Level,
        title: Optional[str] = None,
        chapter: Optional[str] = None,
        hint: Optional[str] = None,
        difficulty: Optional[int] = None,
        step_limit: Optional[int] = None,
        notes: Optional[str] = None,
        author: Optional[str] = None
    ) -> Level:
        """设置关卡元数据"""
        if title is not None:
            level.title = title if title != "" else None
        if chapter is not None:
            level.chapter = chapter if chapter != "" else None
        if hint is not None:
            level.hint = hint if hint != "" else None
        if difficulty is not None:
            level.difficulty = difficulty
        if step_limit is not None:
            level.step_limit = step_limit if step_limit > 0 else None
        if notes is not None:
            level.notes = notes if notes != "" else None
        if author is not None:
            level.author = author if author != "" else None
        return level

    @staticmethod
    def _get_next_id(items: List, start: int = 1) -> int:
        """获取下一个可用 ID"""
        existing_ids = {item.id for item in items}
        next_id = start
        while next_id in existing_ids:
            next_id += 1
        return next_id

    @staticmethod
    def ensure_floor(level: Level, pos: Position) -> Level:
        """确保位置是地板（如果不是墙的话）"""
        if not level.is_valid_position(pos):
            if pos.x >= level.width:
                level.width = pos.x + 1
            if pos.y >= level.height:
                level.height = pos.y + 1

        if not level.is_wall(pos) and pos not in level.floors:
            level.floors.append(pos)
        return level

    @staticmethod
    def add_box(
        level: Level,
        x: int,
        y: int,
        box_id: Optional[int] = None,
        color: Optional[str] = None
    ) -> EditResult:
        """安全地添加箱子"""
        pos = Position(x, y)

        coord_err = LevelEditor._validate_coordinate(x, y)
        if coord_err:
            return EditResult(level=level, success=False, message=coord_err, position=pos)

        if level.is_wall(pos):
            return EditResult(
                level=level, success=False,
                message=f"位置 ({x},{y}) 是墙，不能放置箱子",
                position=pos
            )

        if level.is_door(pos):
            return EditResult(
                level=level, success=False,
                message=f"位置 ({x},{y}) 有门，不能放置箱子",
                position=pos
            )

        overlaps = LevelEditor._check_overlap(level, pos, exclude="box")
        if overlaps:
            return EditResult(
                level=level, success=False,
                message=f"位置 ({x},{y}) 已有元素: {', '.join(overlaps)}，不能叠放箱子",
                position=pos
            )

        level = LevelEditor.ensure_floor(level, pos)

        if box_id is None:
            box_id = LevelEditor._get_next_id(level.boxes)
        elif any(b.id == box_id for b in level.boxes):
            return EditResult(
                level=level, success=False,
                message=f"箱子 ID {box_id} 已存在",
                position=pos
            )

        box = Box(id=box_id, position=pos, color=color)
        level.boxes.append(box)
        return EditResult(
            level=level, success=True,
            message=f"已添加箱子 #{box_id} 于 ({x},{y})",
            position=pos
        )

    @staticmethod
    def remove_box(level: Level, x: int, y: int) -> EditResult:
        """移除指定位置的箱子"""
        pos = Position(x, y)
        for i, box in enumerate(level.boxes):
            if box.position == pos:
                level.boxes.pop(i)
                return EditResult(
                    level=level, success=True,
                    message=f"已移除箱子 #{box.id} 于 ({x},{y})",
                    position=pos
                )
        return EditResult(
            level=level, success=False,
            message=f"位置 ({x},{y}) 没有箱子",
            position=pos
        )

    @staticmethod
    def remove_box_by_id(level: Level, box_id: int) -> EditResult:
        """按 ID 移除箱子"""
        for i, box in enumerate(level.boxes):
            if box.id == box_id:
                pos = box.position
                level.boxes.pop(i)
                return EditResult(
                    level=level, success=True,
                    message=f"已移除箱子 #{box_id}",
                    position=pos
                )
        return EditResult(
            level=level, success=False,
            message=f"未找到箱子 ID {box_id}"
        )

    @staticmethod
    def add_target(
        level: Level,
        x: int,
        y: int,
        target_id: Optional[int] = None,
        required_color: Optional[str] = None
    ) -> EditResult:
        """安全地添加目标点"""
        pos = Position(x, y)

        coord_err = LevelEditor._validate_coordinate(x, y)
        if coord_err:
            return EditResult(level=level, success=False, message=coord_err, position=pos)

        if level.is_wall(pos):
            return EditResult(
                level=level, success=False,
                message=f"位置 ({x},{y}) 是墙，不能放置目标点",
                position=pos
            )

        overlaps = LevelEditor._check_overlap(level, pos, exclude="target")
        if "目标点" in overlaps:
            return EditResult(
                level=level, success=False,
                message=f"位置 ({x},{y}) 已有目标点",
                position=pos
            )

        level = LevelEditor.ensure_floor(level, pos)

        if target_id is None:
            target_id = LevelEditor._get_next_id(level.targets)
        elif any(t.id == target_id for t in level.targets):
            return EditResult(
                level=level, success=False,
                message=f"目标点 ID {target_id} 已存在",
                position=pos
            )

        target = Target(id=target_id, position=pos, required_color=required_color)
        level.targets.append(target)
        return EditResult(
            level=level, success=True,
            message=f"已添加目标点 #{target_id} 于 ({x},{y})",
            position=pos
        )

    @staticmethod
    def remove_target(level: Level, x: int, y: int) -> EditResult:
        """移除指定位置的目标点"""
        pos = Position(x, y)
        for i, target in enumerate(level.targets):
            if target.position == pos:
                level.targets.pop(i)
                return EditResult(
                    level=level, success=True,
                    message=f"已移除目标点 #{target.id} 于 ({x},{y})",
                    position=pos
                )
        return EditResult(
            level=level, success=False,
            message=f"位置 ({x},{y}) 没有目标点",
            position=pos
        )

    @staticmethod
    def remove_target_by_id(level: Level, target_id: int) -> EditResult:
        """按 ID 移除目标点"""
        for i, target in enumerate(level.targets):
            if target.id == target_id:
                pos = target.position
                level.targets.pop(i)
                return EditResult(
                    level=level, success=True,
                    message=f"已移除目标点 #{target_id}",
                    position=pos
                )
        return EditResult(
            level=level, success=False,
            message=f"未找到目标点 ID {target_id}"
        )

    @staticmethod
    def add_wall(level: Level, x: int, y: int) -> EditResult:
        """安全地添加墙"""
        pos = Position(x, y)

        coord_err = LevelEditor._validate_coordinate(x, y)
        if coord_err:
            return EditResult(level=level, success=False, message=coord_err, position=pos)

        if level.is_wall(pos):
            return EditResult(
                level=level, success=False,
                message=f"位置 ({x},{y}) 已有墙",
                position=pos
            )

        if not level.is_valid_position(pos):
            if pos.x >= level.width:
                level.width = pos.x + 1
            if pos.y >= level.height:
                level.height = pos.y + 1

        if pos in level.floors:
            level.floors.remove(pos)

        level.walls.append(pos)

        removed = []
        for i in range(len(level.boxes) - 1, -1, -1):
            if level.boxes[i].position == pos:
                removed.append(f"箱子#{level.boxes[i].id}")
                level.boxes.pop(i)
        for i in range(len(level.targets) - 1, -1, -1):
            if level.targets[i].position == pos:
                removed.append(f"目标点#{level.targets[i].id}")
                level.targets.pop(i)
        for i in range(len(level.switches) - 1, -1, -1):
            if level.switches[i].position == pos:
                removed.append(f"开关#{level.switches[i].id}")
                level.switches.pop(i)
        for i in range(len(level.doors) - 1, -1, -1):
            if level.doors[i].position == pos:
                removed.append(f"门#{level.doors[i].id}")
                level.doors.pop(i)

        msg = f"已添加墙于 ({x},{y})"
        result = EditResult(level=level, success=True, message=msg, position=pos)
        if removed:
            result.warnings.append(f"警告: 墙覆盖了以下元素: {', '.join(removed)}")
        if level.player == pos:
            level.player = Position(0, 0)
            result.warnings.append("警告: 玩家位置被墙覆盖，已重置到 (0,0)")
        return result

    @staticmethod
    def remove_wall(level: Level, x: int, y: int) -> EditResult:
        """移除墙"""
        pos = Position(x, y)
        for i, wall in enumerate(level.walls):
            if wall == pos:
                level.walls.pop(i)
                level = LevelEditor.ensure_floor(level, pos)
                return EditResult(
                    level=level, success=True,
                    message=f"已移除墙于 ({x},{y})",
                    position=pos
                )
        return EditResult(
            level=level, success=False,
            message=f"位置 ({x},{y}) 没有墙",
            position=pos
        )

    @staticmethod
    def set_player(level: Level, x: int, y: int) -> EditResult:
        """安全地设置玩家位置"""
        pos = Position(x, y)

        coord_err = LevelEditor._validate_coordinate(x, y)
        if coord_err:
            return EditResult(level=level, success=False, message=coord_err, position=pos)

        if level.is_wall(pos):
            return EditResult(
                level=level, success=False,
                message=f"位置 ({x},{y}) 是墙，玩家不能放在墙上",
                position=pos
            )

        if level.is_door(pos):
            door = level.get_door_at(pos)
            if door and not door.is_open:
                return EditResult(
                    level=level, success=False,
                    message=f"位置 ({x},{y}) 有关闭的门，玩家不能放在门上",
                    position=pos
                )

        overlaps = LevelEditor._check_overlap(level, pos, exclude="player")
        if "箱子" in overlaps:
            return EditResult(
                level=level, success=False,
                message=f"位置 ({x},{y}) 有箱子，玩家不能和箱子叠放",
                position=pos
            )
        if "开关" in overlaps:
            return EditResult(
                level=level, success=False,
                message=f"位置 ({x},{y}) 有开关，玩家不能和开关重叠",
                position=pos
            )

        level = LevelEditor.ensure_floor(level, pos)
        level.player = pos
        return EditResult(
            level=level, success=True,
            message=f"玩家位置已设置为 ({x},{y})",
            position=pos
        )

    @staticmethod
    def add_switch(
        level: Level,
        x: int,
        y: int,
        switch_id: Optional[int] = None,
        door_ids: Optional[List[int]] = None
    ) -> EditResult:
        """安全地添加开关"""
        pos = Position(x, y)

        coord_err = LevelEditor._validate_coordinate(x, y)
        if coord_err:
            return EditResult(level=level, success=False, message=coord_err, position=pos)

        if level.is_wall(pos):
            return EditResult(
                level=level, success=False,
                message=f"位置 ({x},{y}) 是墙，不能放置开关",
                position=pos
            )

        if level.is_door(pos):
            return EditResult(
                level=level, success=False,
                message=f"位置 ({x},{y}) 有门，不能放置开关",
                position=pos
            )

        overlaps = LevelEditor._check_overlap(level, pos, exclude="switch")
        if overlaps:
            return EditResult(
                level=level, success=False,
                message=f"位置 ({x},{y}) 已有元素: {', '.join(overlaps)}，不能叠放开关",
                position=pos
            )

        level = LevelEditor.ensure_floor(level, pos)

        if switch_id is None:
            switch_id = LevelEditor._get_next_id(level.switches)
        elif any(s.id == switch_id for s in level.switches):
            return EditResult(
                level=level, success=False,
                message=f"开关 ID {switch_id} 已存在",
                position=pos
            )

        switch = Switch(id=switch_id, position=pos, door_ids=door_ids or [])
        level.switches.append(switch)

        bind_info = f"，绑定门: {door_ids}" if door_ids else ""
        return EditResult(
            level=level, success=True,
            message=f"已添加开关 #{switch_id} 于 ({x},{y}){bind_info}",
            position=pos
        )

    @staticmethod
    def remove_switch(level: Level, x: int, y: int) -> EditResult:
        """移除指定位置的开关"""
        pos = Position(x, y)
        for i, switch in enumerate(level.switches):
            if switch.position == pos:
                level.switches.pop(i)
                return EditResult(
                    level=level, success=True,
                    message=f"已移除开关 #{switch.id} 于 ({x},{y})",
                    position=pos
                )
        return EditResult(
            level=level, success=False,
            message=f"位置 ({x},{y}) 没有开关",
            position=pos
        )

    @staticmethod
    def remove_switch_by_id(level: Level, switch_id: int) -> EditResult:
        """按 ID 移除开关"""
        for i, switch in enumerate(level.switches):
            if switch.id == switch_id:
                pos = switch.position
                level.switches.pop(i)
                return EditResult(
                    level=level, success=True,
                    message=f"已移除开关 #{switch_id}",
                    position=pos
                )
        return EditResult(
            level=level, success=False,
            message=f"未找到开关 ID {switch_id}"
        )

    @staticmethod
    def bind_switch_to_doors(level: Level, switch_id: int, door_ids: List[int]) -> EditResult:
        """将开关绑定到一个或多个门（替换模式）"""
        for switch in level.switches:
            if switch.id == switch_id:
                invalid = [d for d in door_ids if not any(door.id == d for door in level.doors)]
                warnings = []
                if invalid:
                    warnings.append(f"警告: 以下门 ID 不存在: {invalid}")
                switch.door_ids = list(set(d for d in door_ids if d not in invalid))
                return EditResult(
                    level=level, success=True,
                    message=f"开关 {switch_id} 已绑定到门: {switch.door_ids}",
                    warnings=warnings
                )
        return EditResult(
            level=level, success=False,
            message=f"未找到开关 ID {switch_id}"
        )

    @staticmethod
    def add_door_binding(level: Level, switch_id: int, door_id: int) -> EditResult:
        """追加单个门到开关绑定"""
        for switch in level.switches:
            if switch.id == switch_id:
                if not any(door.id == door_id for door in level.doors):
                    return EditResult(
                        level=level, success=False,
                        message=f"门 ID {door_id} 不存在"
                    )
                if door_id in switch.door_ids:
                    return EditResult(
                        level=level, success=False,
                        message=f"开关 {switch_id} 已经绑定门 {door_id}"
                    )
                switch.door_ids.append(door_id)
                return EditResult(
                    level=level, success=True,
                    message=f"已追加门 {door_id} 到开关 {switch_id} 的绑定，当前绑定: {switch.door_ids}"
                )
        return EditResult(
            level=level, success=False,
            message=f"未找到开关 ID {switch_id}"
        )

    @staticmethod
    def remove_door_binding(level: Level, switch_id: int, door_id: int) -> EditResult:
        """从开关绑定中移除单个门"""
        for switch in level.switches:
            if switch.id == switch_id:
                if door_id not in switch.door_ids:
                    return EditResult(
                        level=level, success=False,
                        message=f"开关 {switch_id} 未绑定门 {door_id}"
                    )
                switch.door_ids.remove(door_id)
                return EditResult(
                    level=level, success=True,
                    message=f"已从开关 {switch_id} 移除门 {door_id}，当前绑定: {switch.door_ids}"
                )
        return EditResult(
            level=level, success=False,
            message=f"未找到开关 ID {switch_id}"
        )

    @staticmethod
    def unbind_switch_doors(level: Level, switch_id: int) -> EditResult:
        """解绑开关的所有门"""
        for switch in level.switches:
            if switch.id == switch_id:
                switch.door_ids = []
                return EditResult(
                    level=level, success=True,
                    message=f"已解绑开关 {switch_id} 的所有门"
                )
        return EditResult(
            level=level, success=False,
            message=f"未找到开关 ID {switch_id}"
        )

    @staticmethod
    def add_door(
        level: Level,
        x: int,
        y: int,
        door_id: Optional[int] = None,
        is_open: bool = False
    ) -> EditResult:
        """安全地添加门"""
        pos = Position(x, y)

        coord_err = LevelEditor._validate_coordinate(x, y)
        if coord_err:
            return EditResult(level=level, success=False, message=coord_err, position=pos)

        if level.is_wall(pos):
            return EditResult(
                level=level, success=False,
                message=f"位置 ({x},{y}) 是墙，不能放置门",
                position=pos
            )

        overlaps = LevelEditor._check_overlap(level, pos, exclude="door")
        if overlaps:
            return EditResult(
                level=level, success=False,
                message=f"位置 ({x},{y}) 已有元素: {', '.join(overlaps)}，不能叠放门",
                position=pos
            )

        if not level.is_valid_position(pos):
            if pos.x >= level.width:
                level.width = pos.x + 1
            if pos.y >= level.height:
                level.height = pos.y + 1

        if pos in level.floors:
            level.floors.remove(pos)

        if door_id is None:
            door_id = LevelEditor._get_next_id(level.doors)
        elif any(d.id == door_id for d in level.doors):
            return EditResult(
                level=level, success=False,
                message=f"门 ID {door_id} 已存在",
                position=pos
            )

        door = Door(id=door_id, position=pos, is_open=is_open)
        level.doors.append(door)
        return EditResult(
            level=level, success=True,
            message=f"已添加门 #{door_id} 于 ({x},{y})",
            position=pos
        )

    @staticmethod
    def remove_door(level: Level, x: int, y: int) -> EditResult:
        """移除指定位置的门，并提示相关开关绑定"""
        pos = Position(x, y)
        for i, door in enumerate(level.doors):
            if door.position == pos:
                removed_id = door.id
                level.doors.pop(i)
                level = LevelEditor.ensure_floor(level, pos)

                affected_switches = []
                for switch in level.switches:
                    if removed_id in switch.door_ids:
                        switch.door_ids.remove(removed_id)
                        affected_switches.append(switch.id)

                result = EditResult(
                    level=level, success=True,
                    message=f"已移除门 #{removed_id} 于 ({x},{y})",
                    position=pos
                )
                if affected_switches:
                    result.warnings.append(
                        f"提示: 已自动清理开关 {affected_switches} 对门 #{removed_id} 的绑定引用"
                    )
                return result
        return EditResult(
            level=level, success=False,
            message=f"位置 ({x},{y}) 没有门",
            position=pos
        )

    @staticmethod
    def remove_door_by_id(level: Level, door_id: int) -> EditResult:
        """按 ID 移除门，并清理相关开关绑定"""
        for i, door in enumerate(level.doors):
            if door.id == door_id:
                pos = door.position
                level.doors.pop(i)
                level = LevelEditor.ensure_floor(level, pos)

                affected_switches = []
                for switch in level.switches:
                    if door_id in switch.door_ids:
                        switch.door_ids.remove(door_id)
                        affected_switches.append(switch.id)

                result = EditResult(
                    level=level, success=True,
                    message=f"已移除门 #{door_id}",
                    position=pos
                )
                if affected_switches:
                    result.warnings.append(
                        f"提示: 已自动清理开关 {affected_switches} 对门 #{door_id} 的绑定引用"
                    )
                return result
        return EditResult(
            level=level, success=False,
            message=f"未找到门 ID {door_id}"
        )

    @staticmethod
    def toggle_door(level: Level, door_id: int) -> EditResult:
        """切换门的开关状态"""
        for door in level.doors:
            if door.id == door_id:
                door.is_open = not door.is_open
                status = "打开" if door.is_open else "关闭"
                return EditResult(
                    level=level, success=True,
                    message=f"门 {door_id} 状态: {status}"
                )
        return EditResult(
            level=level, success=False,
            message=f"未找到门 ID {door_id}"
        )
