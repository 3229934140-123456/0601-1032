"""文本地图解析器"""

from typing import List, Tuple
from .models import Level, Position, Box, Target, Switch, Door, TileType


class MapParser:
    """文本地图解析器"""

    @staticmethod
    def parse(text_map: str, level_name: str = "untitled") -> Level:
        """
        解析文本地图

        符号说明:
            #  墙
            .  地板
            x  目标点
            $  箱子
            *  箱子在目标点上
            @  玩家
            +  玩家在目标点上
            D  机关门（关闭）
            d  机关门（打开）
            S  机关开关
            s  激活的机关开关
            (空格)  虚空
        """
        lines = text_map.strip().split("\n")
        lines = [line.rstrip() for line in lines]

        height = len(lines)
        width = max(len(line) for line in lines) if lines else 0

        level = Level(name=level_name, width=width, height=height)

        walls: List[Position] = []
        floors: List[Position] = []
        boxes: List[Box] = []
        targets: List[Target] = []
        switches: List[Switch] = []
        doors: List[Door] = []
        player = Position(0, 0)

        box_id = 1
        target_id = 1
        switch_id = 1
        door_id = 1

        for y, line in enumerate(lines):
            for x in range(width):
                char = line[x] if x < len(line) else " "
                pos = Position(x, y)

                if char == TileType.WALL.value:
                    walls.append(pos)
                elif char == TileType.EMPTY.value:
                    pass
                else:
                    floors.append(pos)

                    if char == TileType.PLAYER.value:
                        player = pos
                    elif char == TileType.PLAYER_ON_TARGET.value:
                        player = pos
                        targets.append(Target(id=target_id, position=pos))
                        target_id += 1
                    elif char == TileType.TARGET.value:
                        targets.append(Target(id=target_id, position=pos))
                        target_id += 1
                    elif char == TileType.BOX.value:
                        boxes.append(Box(id=box_id, position=pos))
                        box_id += 1
                    elif char == TileType.BOX_ON_TARGET.value:
                        boxes.append(Box(id=box_id, position=pos))
                        box_id += 1
                        targets.append(Target(id=target_id, position=pos))
                        target_id += 1
                    elif char == TileType.DOOR.value:
                        doors.append(Door(id=door_id, position=pos, is_open=False))
                        door_id += 1
                    elif char == TileType.DOOR_OPEN.value:
                        doors.append(Door(id=door_id, position=pos, is_open=True))
                        door_id += 1
                    elif char == TileType.SWITCH.value:
                        switches.append(Switch(id=switch_id, position=pos))
                        switch_id += 1
                    elif char == TileType.SWITCH_ACTIVE.value:
                        switches.append(Switch(id=switch_id, position=pos))
                        switch_id += 1

        level.walls = walls
        level.floors = floors
        level.boxes = boxes
        level.targets = targets
        level.switches = switches
        level.doors = doors
        level.player = player

        return level

    @staticmethod
    def from_file(filepath: str, level_name: str = None) -> Level:
        """从文件加载文本地图"""
        if level_name is None:
            import os
            level_name = os.path.splitext(os.path.basename(filepath))[0]

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        return MapParser.parse(content, level_name)

    @staticmethod
    def to_text_map(level: Level) -> str:
        """将关卡转换为文本地图"""
        grid = [[" " for _ in range(level.width)] for _ in range(level.height)]

        for pos in level.walls:
            grid[pos.y][pos.x] = TileType.WALL.value

        for pos in level.floors:
            grid[pos.y][pos.x] = TileType.FLOOR.value

        for target in level.targets:
            grid[target.position.y][target.position.x] = TileType.TARGET.value

        for door in level.doors:
            grid[door.position.y][door.position.x] = (
                TileType.DOOR_OPEN.value if door.is_open else TileType.DOOR.value
            )

        for switch in level.switches:
            grid[switch.position.y][switch.position.x] = TileType.SWITCH.value

        for box in level.boxes:
            if level.get_target_at(box.position):
                grid[box.position.y][box.position.x] = TileType.BOX_ON_TARGET.value
            else:
                grid[box.position.y][box.position.x] = TileType.BOX.value

        if level.get_target_at(level.player):
            grid[level.player.y][level.player.x] = TileType.PLAYER_ON_TARGET.value
        else:
            grid[level.player.y][level.player.x] = TileType.PLAYER.value

        return "\n".join("".join(row) for row in grid)
