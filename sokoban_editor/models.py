"""数据模型定义"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Tuple
import json
import os


class TileType(Enum):
    """地图格子类型"""
    FLOOR = "."
    WALL = "#"
    TARGET = "x"
    BOX = "$"
    BOX_ON_TARGET = "*"
    PLAYER = "@"
    PLAYER_ON_TARGET = "+"
    DOOR = "D"
    DOOR_OPEN = "d"
    SWITCH = "S"
    SWITCH_ACTIVE = "s"
    EMPTY = " "


@dataclass
class Position:
    """位置坐标"""
    x: int
    y: int

    def __hash__(self):
        return hash((self.x, self.y))

    def __eq__(self, other):
        return isinstance(other, Position) and self.x == other.x and self.y == other.y

    def __add__(self, other):
        return Position(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Position(self.x - other.x, self.y - other.y)

    def to_tuple(self) -> Tuple[int, int]:
        return (self.x, self.y)


@dataclass
class Box:
    """箱子"""
    id: int
    position: Position
    color: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "position": {"x": self.position.x, "y": self.position.y},
            "color": self.color
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Box":
        return cls(
            id=data["id"],
            position=Position(data["position"]["x"], data["position"]["y"]),
            color=data.get("color")
        )


@dataclass
class Target:
    """目标点"""
    id: int
    position: Position
    required_color: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "position": {"x": self.position.x, "y": self.position.y},
            "required_color": self.required_color
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Target":
        return cls(
            id=data["id"],
            position=Position(data["position"]["x"], data["position"]["y"]),
            required_color=data.get("required_color")
        )


@dataclass
class Switch:
    """机关开关"""
    id: int
    position: Position
    door_ids: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "position": {"x": self.position.x, "y": self.position.y},
            "door_ids": self.door_ids
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Switch":
        return cls(
            id=data["id"],
            position=Position(data["position"]["x"], data["position"]["y"]),
            door_ids=data.get("door_ids", [])
        )


@dataclass
class Door:
    """机关门"""
    id: int
    position: Position
    is_open: bool = False

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "position": {"x": self.position.x, "y": self.position.y},
            "is_open": self.is_open
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Door":
        return cls(
            id=data["id"],
            position=Position(data["position"]["x"], data["position"]["y"]),
            is_open=data.get("is_open", False)
        )


@dataclass
class Level:
    """关卡"""
    name: str
    width: int
    height: int
    walls: List[Position] = field(default_factory=list)
    floors: List[Position] = field(default_factory=list)
    player: Position = Position(0, 0)
    boxes: List[Box] = field(default_factory=list)
    targets: List[Target] = field(default_factory=list)
    switches: List[Switch] = field(default_factory=list)
    doors: List[Door] = field(default_factory=list)
    step_limit: Optional[int] = None
    title: Optional[str] = None
    chapter: Optional[str] = None
    hint: Optional[str] = None
    difficulty: Optional[int] = None
    author: Optional[str] = None
    created_at: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "title": self.title,
            "chapter": self.chapter,
            "hint": self.hint,
            "difficulty": self.difficulty,
            "author": self.author,
            "created_at": self.created_at,
            "notes": self.notes,
            "step_limit": self.step_limit,
            "width": self.width,
            "height": self.height,
            "player": {"x": self.player.x, "y": self.player.y},
            "walls": [{"x": w.x, "y": w.y} for w in self.walls],
            "floors": [{"x": f.x, "y": f.y} for f in self.floors],
            "boxes": [b.to_dict() for b in self.boxes],
            "targets": [t.to_dict() for t in self.targets],
            "switches": [s.to_dict() for s in self.switches],
            "doors": [d.to_dict() for d in self.doors]
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Level":
        level = cls(
            name=data["name"],
            width=data["width"],
            height=data["height"],
            player=Position(data["player"]["x"], data["player"]["y"]),
            walls=[Position(w["x"], w["y"]) for w in data.get("walls", [])],
            floors=[Position(f["x"], f["y"]) for f in data.get("floors", [])],
            boxes=[Box.from_dict(b) for b in data.get("boxes", [])],
            targets=[Target.from_dict(t) for t in data.get("targets", [])],
            switches=[Switch.from_dict(s) for s in data.get("switches", [])],
            doors=[Door.from_dict(d) for d in data.get("doors", [])],
            step_limit=data.get("step_limit"),
            title=data.get("title"),
            chapter=data.get("chapter"),
            hint=data.get("hint"),
            difficulty=data.get("difficulty"),
            author=data.get("author"),
            created_at=data.get("created_at"),
            notes=data.get("notes")
        )
        return level

    def save(self, directory: str):
        """保存关卡到文件"""
        filepath = os.path.join(directory, f"{self.name}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, filepath: str) -> "Level":
        """从文件加载关卡"""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def is_valid_position(self, pos: Position) -> bool:
        """检查位置是否在关卡范围内"""
        return 0 <= pos.x < self.width and 0 <= pos.y < self.height

    def is_wall(self, pos: Position) -> bool:
        """检查位置是否是墙"""
        return pos in self.walls

    def is_floor(self, pos: Position) -> bool:
        """检查位置是否是地板"""
        return pos in self.floors

    def is_door(self, pos: Position) -> bool:
        """检查位置是否是门"""
        return any(d.position == pos for d in self.doors)

    def get_box_at(self, pos: Position) -> Optional[Box]:
        """获取指定位置的箱子"""
        for box in self.boxes:
            if box.position == pos:
                return box
        return None

    def get_target_at(self, pos: Position) -> Optional[Target]:
        """获取指定位置的目标点"""
        for target in self.targets:
            if target.position == pos:
                return target
        return None

    def get_switch_at(self, pos: Position) -> Optional[Switch]:
        """获取指定位置的开关"""
        for switch in self.switches:
            if switch.position == pos:
                return switch
        return None

    def get_door_at(self, pos: Position) -> Optional[Door]:
        """获取指定位置的门"""
        for door in self.doors:
            if door.position == pos:
                return door
        return None
