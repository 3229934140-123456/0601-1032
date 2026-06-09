"""关卡编辑器模块"""

from typing import List, Optional, Tuple
from .models import Level, Position, Box, Target, Switch, Door


class LevelEditor:
    """关卡编辑器"""

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
    ) -> Tuple[Level, Box]:
        """添加箱子"""
        pos = Position(x, y)
        if level.get_box_at(pos):
            raise ValueError(f"位置 ({x},{y}) 已有箱子")

        level = LevelEditor.ensure_floor(level, pos)

        if box_id is None:
            box_id = LevelEditor._get_next_id(level.boxes)
        elif any(b.id == box_id for b in level.boxes):
            raise ValueError(f"箱子 ID {box_id} 已存在")

        box = Box(id=box_id, position=pos, color=color)
        level.boxes.append(box)
        return level, box

    @staticmethod
    def remove_box(level: Level, x: int, y: int) -> Tuple[Level, bool]:
        """移除指定位置的箱子"""
        pos = Position(x, y)
        for i, box in enumerate(level.boxes):
            if box.position == pos:
                level.boxes.pop(i)
                return level, True
        return level, False

    @staticmethod
    def remove_box_by_id(level: Level, box_id: int) -> Tuple[Level, bool]:
        """按 ID 移除箱子"""
        for i, box in enumerate(level.boxes):
            if box.id == box_id:
                level.boxes.pop(i)
                return level, True
        return level, False

    @staticmethod
    def add_target(
        level: Level,
        x: int,
        y: int,
        target_id: Optional[int] = None,
        required_color: Optional[str] = None
    ) -> Tuple[Level, Target]:
        """添加目标点"""
        pos = Position(x, y)
        if level.get_target_at(pos):
            raise ValueError(f"位置 ({x},{y}) 已有目标点")

        level = LevelEditor.ensure_floor(level, pos)

        if target_id is None:
            target_id = LevelEditor._get_next_id(level.targets)
        elif any(t.id == target_id for t in level.targets):
            raise ValueError(f"目标点 ID {target_id} 已存在")

        target = Target(id=target_id, position=pos, required_color=required_color)
        level.targets.append(target)
        return level, target

    @staticmethod
    def remove_target(level: Level, x: int, y: int) -> Tuple[Level, bool]:
        """移除指定位置的目标点"""
        pos = Position(x, y)
        for i, target in enumerate(level.targets):
            if target.position == pos:
                level.targets.pop(i)
                return level, True
        return level, False

    @staticmethod
    def remove_target_by_id(level: Level, target_id: int) -> Tuple[Level, bool]:
        """按 ID 移除目标点"""
        for i, target in enumerate(level.targets):
            if target.id == target_id:
                level.targets.pop(i)
                return level, True
        return level, False

    @staticmethod
    def add_wall(level: Level, x: int, y: int) -> Level:
        """添加墙"""
        pos = Position(x, y)
        if not level.is_valid_position(pos):
            if pos.x >= level.width:
                level.width = pos.x + 1
            if pos.y >= level.height:
                level.height = pos.y + 1

        if pos in level.floors:
            level.floors.remove(pos)

        if not level.is_wall(pos):
            level.walls.append(pos)

        level.boxes = [b for b in level.boxes if b.position != pos]
        level.targets = [t for t in level.targets if t.position != pos]
        level.switches = [s for s in level.switches if s.position != pos]
        level.doors = [d for d in level.doors if d.position != pos]
        if level.player == pos:
            level.player = Position(0, 0)

        return level

    @staticmethod
    def remove_wall(level: Level, x: int, y: int) -> Tuple[Level, bool]:
        """移除墙"""
        pos = Position(x, y)
        for i, wall in enumerate(level.walls):
            if wall == pos:
                level.walls.pop(i)
                level = LevelEditor.ensure_floor(level, pos)
                return level, True
        return level, False

    @staticmethod
    def set_player(level: Level, x: int, y: int) -> Level:
        """设置玩家位置"""
        pos = Position(x, y)
        level = LevelEditor.ensure_floor(level, pos)
        level.player = pos
        return level

    @staticmethod
    def add_switch(
        level: Level,
        x: int,
        y: int,
        switch_id: Optional[int] = None,
        door_ids: Optional[List[int]] = None
    ) -> Tuple[Level, Switch]:
        """添加开关"""
        pos = Position(x, y)
        if level.get_switch_at(pos):
            raise ValueError(f"位置 ({x},{y}) 已有开关")

        level = LevelEditor.ensure_floor(level, pos)

        if switch_id is None:
            switch_id = LevelEditor._get_next_id(level.switches)
        elif any(s.id == switch_id for s in level.switches):
            raise ValueError(f"开关 ID {switch_id} 已存在")

        switch = Switch(id=switch_id, position=pos, door_ids=door_ids or [])
        level.switches.append(switch)
        return level, switch

    @staticmethod
    def remove_switch(level: Level, x: int, y: int) -> Tuple[Level, bool]:
        """移除指定位置的开关"""
        pos = Position(x, y)
        for i, switch in enumerate(level.switches):
            if switch.position == pos:
                level.switches.pop(i)
                return level, True
        return level, False

    @staticmethod
    def remove_switch_by_id(level: Level, switch_id: int) -> Tuple[Level, bool]:
        """按 ID 移除开关"""
        for i, switch in enumerate(level.switches):
            if switch.id == switch_id:
                level.switches.pop(i)
                return level, True
        return level, False

    @staticmethod
    def bind_switch_to_doors(level: Level, switch_id: int, door_ids: List[int]) -> Tuple[Level, bool]:
        """将开关绑定到一个或多个门"""
        for switch in level.switches:
            if switch.id == switch_id:
                switch.door_ids = list(set(door_ids))
                return level, True
        return level, False

    @staticmethod
    def unbind_switch_doors(level: Level, switch_id: int) -> Tuple[Level, bool]:
        """解绑开关的所有门"""
        for switch in level.switches:
            if switch.id == switch_id:
                switch.door_ids = []
                return level, True
        return level, False

    @staticmethod
    def add_door(
        level: Level,
        x: int,
        y: int,
        door_id: Optional[int] = None,
        is_open: bool = False
    ) -> Tuple[Level, Door]:
        """添加门"""
        pos = Position(x, y)
        if level.get_door_at(pos):
            raise ValueError(f"位置 ({x},{y}) 已有门")

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
            raise ValueError(f"门 ID {door_id} 已存在")

        door = Door(id=door_id, position=pos, is_open=is_open)
        level.doors.append(door)
        return level, door

    @staticmethod
    def remove_door(level: Level, x: int, y: int) -> Tuple[Level, bool]:
        """移除指定位置的门"""
        pos = Position(x, y)
        for i, door in enumerate(level.doors):
            if door.position == pos:
                level.doors.pop(i)
                level = LevelEditor.ensure_floor(level, pos)
                return level, True
        return level, False

    @staticmethod
    def remove_door_by_id(level: Level, door_id: int) -> Tuple[Level, bool]:
        """按 ID 移除门"""
        for i, door in enumerate(level.doors):
            if door.id == door_id:
                pos = door.position
                level.doors.pop(i)
                level = LevelEditor.ensure_floor(level, pos)
                return level, True
        return level, False

    @staticmethod
    def toggle_door(level: Level, door_id: int) -> Tuple[Level, bool]:
        """切换门的开关状态"""
        for door in level.doors:
            if door.id == door_id:
                door.is_open = not door.is_open
                return level, True
        return level, False
