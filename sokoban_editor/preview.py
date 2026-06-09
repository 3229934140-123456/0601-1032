"""终端预览模块"""

from typing import List, Tuple
from .models import Level, Position, TileType


class TerminalPreview:
    """终端预览渲染器"""

    COLORS = {
        "reset": "\033[0m",
        "wall": "\033[90m",
        "floor": "\033[37m",
        "target": "\033[91m",
        "box": "\033[93m",
        "box_on_target": "\033[92m",
        "player": "\033[96m",
        "player_on_target": "\033[96m",
        "door": "\033[95m",
        "door_open": "\033[35m",
        "switch": "\033[94m",
        "empty": "\033[30m",
        "border": "\033[90m",
        "error": "\033[41m\033[97m",
        "warning": "\033[43m\033[30m",
    }

    TILE_DISPLAY = {
        TileType.WALL: ("█", "wall"),
        TileType.FLOOR: ("·", "floor"),
        TileType.TARGET: ("×", "target"),
        TileType.BOX: ("□", "box"),
        TileType.BOX_ON_TARGET: ("■", "box_on_target"),
        TileType.PLAYER: ("☺", "player"),
        TileType.PLAYER_ON_TARGET: ("☻", "player_on_target"),
        TileType.DOOR: ("▤", "door"),
        TileType.DOOR_OPEN: ("▥", "door_open"),
        TileType.SWITCH: ("◆", "switch"),
        TileType.SWITCH_ACTIVE: ("◇", "switch"),
        TileType.EMPTY: (" ", "empty"),
    }

    @staticmethod
    def render(
        level: Level,
        use_color: bool = True,
        show_ids: bool = False,
        show_issues: bool = True,
        show_bindings: bool = False
    ) -> str:
        """渲染关卡到终端字符串"""
        lines: List[str] = []

        header = TerminalPreview._render_header(level, use_color)
        if header:
            lines.append(header)

        grid_lines = TerminalPreview._render_grid(level, use_color, show_ids)
        lines.extend(grid_lines)

        if show_issues:
            issues_section = TerminalPreview._render_issues(level, use_color)
            if issues_section:
                lines.append("")
                lines.append(issues_section)

        if show_bindings or level.switches or level.doors:
            bindings_section = TerminalPreview._render_bindings_detailed(level, use_color)
            if bindings_section:
                lines.append("")
                lines.append(bindings_section)

        legend = TerminalPreview._render_legend(use_color)
        if legend:
            lines.append("")
            lines.append(legend)

        info = TerminalPreview._render_info(level, use_color)
        if info:
            lines.append("")
            lines.append(info)

        return "\n".join(lines)

    @staticmethod
    def _render_issues(level: Level, use_color: bool) -> str:
        """渲染叠放和越界问题"""
        from .editor import LevelEditor

        issues = LevelEditor.get_level_issues(level)
        if not issues:
            return ""

        lines = ["⚠️  格子问题:"]
        for pos, problems in issues:
            problem_str = "、".join(problems)
            if use_color:
                lines.append(
                    f"  {TerminalPreview.COLORS['error']}({pos.x},{pos.y}){TerminalPreview.COLORS['reset']} {problem_str}"
                )
            else:
                lines.append(f"  ({pos.x},{pos.y}) {problem_str}")
        return "\n".join(lines)

    @staticmethod
    def _render_bindings_detailed(level: Level, use_color: bool) -> str:
        """详细渲染开关-门绑定关系，带位置和连线提示"""
        if not level.switches and not level.doors:
            return ""

        lines = []

        if level.switches:
            lines.append("🔌 开关-门绑定关系:")
            for switch in sorted(level.switches, key=lambda s: s.id):
                switch_color = TerminalPreview.COLORS.get("switch", "")
                reset = TerminalPreview.COLORS.get("reset", "") if use_color else ""

                if switch.door_ids:
                    door_infos = []
                    for door_id in sorted(switch.door_ids):
                        door = next((d for d in level.doors if d.id == door_id), None)
                        if door:
                            status = "开" if door.is_open else "关"
                            if use_color:
                                door_color = TerminalPreview.COLORS.get("door_open" if door.is_open else "door", "")
                                door_infos.append(
                                    f"门#{door_id}({door.position.x},{door.position.y})[{door_color}{status}{reset}]"
                                )
                            else:
                                door_infos.append(f"门#{door_id}({door.position.x},{door.position.y})[{status}]")
                        else:
                            if use_color:
                                door_infos.append(
                                    f"{TerminalPreview.COLORS['error']}门#{door_id}(不存在!){reset}"
                                )
                            else:
                                door_infos.append(f"门#{door_id}(不存在!)")

                    if use_color:
                        lines.append(
                            f"  {switch_color}◆ 开关#{switch.id}{reset} "
                            f"({switch.position.x},{switch.position.y}) "
                            f"→ {' → '.join(door_infos)}"
                        )
                    else:
                        lines.append(
                            f"  开关#{switch.id}({switch.position.x},{switch.position.y}) "
                            f"→ {' → '.join(door_infos)}"
                        )
                else:
                    warn = TerminalPreview.COLORS.get("warning", "") if use_color else ""
                    if use_color:
                        lines.append(
                            f"  {switch_color}◆ 开关#{switch.id}{reset} "
                            f"({switch.position.x},{switch.position.y}) "
                            f"→ {warn}[未绑定任何门]{reset}"
                        )
                    else:
                        lines.append(
                            f"  开关#{switch.id}({switch.position.x},{switch.position.y}) → [未绑定任何门]"
                        )

        unbound_doors = []
        all_bound = set()
        for s in level.switches:
            all_bound.update(s.door_ids)
        for door in level.doors:
            if door.id not in all_bound:
                unbound_doors.append(door)

        if unbound_doors:
            lines.append("")
            lines.append("🚪 未被任何开关控制的门:")
            for door in sorted(unbound_doors, key=lambda d: d.id):
                status = "开" if door.is_open else "关"
                if use_color:
                    warn = TerminalPreview.COLORS.get("warning", "")
                    reset = TerminalPreview.COLORS.get("reset", "")
                    lines.append(
                        f"  {warn}门#{door.id}({door.position.x},{door.position.y})[{status}] - 无法打开!{reset}"
                    )
                else:
                    lines.append(f"  门#{door.id}({door.position.x},{door.position.y})[{status}] - 无法打开!")

        return "\n".join(lines)

    @staticmethod
    def _render_header(level: Level, use_color: bool) -> str:
        """渲染标题行"""
        parts = []
        if level.title:
            parts.append(f"关卡: {level.title}")
        else:
            parts.append(f"关卡: {level.name}")

        if level.chapter:
            parts.append(f"章节: {level.chapter}")

        if use_color:
            return f"{TerminalPreview.COLORS['reset']}{' | '.join(parts)}"
        return " | ".join(parts)

    @staticmethod
    def _render_grid(level: Level, use_color: bool, show_ids: bool) -> List[str]:
        """渲染网格"""
        lines: List[str] = []

        grid = [[" " for _ in range(level.width)] for _ in range(level.height)]
        color_grid = [["empty" for _ in range(level.width)] for _ in range(level.height)]

        for pos in level.walls:
            if 0 <= pos.y < level.height and 0 <= pos.x < level.width:
                grid[pos.y][pos.x], color_grid[pos.y][pos.x] = TerminalPreview.TILE_DISPLAY[TileType.WALL]

        for pos in level.floors:
            if 0 <= pos.y < level.height and 0 <= pos.x < level.width:
                grid[pos.y][pos.x], color_grid[pos.y][pos.x] = TerminalPreview.TILE_DISPLAY[TileType.FLOOR]

        for target in level.targets:
            pos = target.position
            if 0 <= pos.y < level.height and 0 <= pos.x < level.width:
                grid[pos.y][pos.x], color_grid[pos.y][pos.x] = TerminalPreview.TILE_DISPLAY[TileType.TARGET]

        for door in level.doors:
            pos = door.position
            if 0 <= pos.y < level.height and 0 <= pos.x < level.width:
                tile = TileType.DOOR_OPEN if door.is_open else TileType.DOOR
                grid[pos.y][pos.x], color_grid[pos.y][pos.x] = TerminalPreview.TILE_DISPLAY[tile]

        for switch in level.switches:
            pos = switch.position
            if 0 <= pos.y < level.height and 0 <= pos.x < level.width:
                grid[pos.y][pos.x], color_grid[pos.y][pos.x] = TerminalPreview.TILE_DISPLAY[TileType.SWITCH]

        for box in level.boxes:
            pos = box.position
            if 0 <= pos.y < level.height and 0 <= pos.x < level.width:
                if level.get_target_at(pos):
                    grid[pos.y][pos.x], color_grid[pos.y][pos.x] = TerminalPreview.TILE_DISPLAY[TileType.BOX_ON_TARGET]
                else:
                    grid[pos.y][pos.x], color_grid[pos.y][pos.x] = TerminalPreview.TILE_DISPLAY[TileType.BOX]

        player_pos = level.player
        if 0 <= player_pos.y < level.height and 0 <= player_pos.x < level.width:
            if level.get_target_at(player_pos):
                grid[player_pos.y][player_pos.x], color_grid[player_pos.y][player_pos.x] = TerminalPreview.TILE_DISPLAY[TileType.PLAYER_ON_TARGET]
            else:
                grid[player_pos.y][player_pos.x], color_grid[player_pos.y][player_pos.x] = TerminalPreview.TILE_DISPLAY[TileType.PLAYER]

        col_num_width = max(2, len(str(level.width - 1)))
        row_num_width = max(2, len(str(level.height - 1)))

        if show_ids:
            col_header = " " * (row_num_width + 1)
            for x in range(level.width):
                col_header += f"{x:^{col_num_width}}"
            lines.append(col_header)

        for y in range(level.height):
            line_parts = []

            if show_ids:
                line_parts.append(f"{y:>{row_num_width}} ")

            for x in range(level.width):
                char = grid[y][x]
                color_name = color_grid[y][x]

                if use_color and color_name in TerminalPreview.COLORS:
                    line_parts.append(
                        f"{TerminalPreview.COLORS[color_name]}{char}{TerminalPreview.COLORS['reset']}"
                    )
                else:
                    line_parts.append(char)

            lines.append("".join(line_parts))

        return lines

    @staticmethod
    def _render_legend(use_color: bool) -> str:
        """渲染图例"""
        items = [
            ("☺", "玩家"),
            ("□", "箱子"),
            ("■", "箱子在目标点"),
            ("×", "目标点"),
            ("▤", "门"),
            ("◆", "开关"),
            ("█", "墙"),
            ("·", "地板"),
        ]

        if use_color:
            parts = []
            for symbol, name in items:
                color_key = {
                    "☺": "player", "□": "box", "■": "box_on_target",
                    "×": "target", "▤": "door", "◆": "switch",
                    "█": "wall", "·": "floor"
                }[symbol]
                parts.append(
                    f"{TerminalPreview.COLORS[color_key]}{symbol}{TerminalPreview.COLORS['reset']}={name}"
                )
            return "  ".join(parts)
        else:
            return "  ".join(f"{s}={n}" for s, n in items)

    @staticmethod
    def _render_info(level: Level, use_color: bool) -> str:
        """渲染关卡信息"""
        infos = []
        infos.append(f"大小: {level.width}x{level.height}")
        infos.append(f"箱子: {len(level.boxes)}")
        infos.append(f"目标点: {len(level.targets)}")
        if level.switches:
            infos.append(f"开关: {len(level.switches)}")
        if level.doors:
            infos.append(f"门: {len(level.doors)}")
        if level.step_limit:
            infos.append(f"步数限制: {level.step_limit}")
        if level.difficulty is not None:
            infos.append(f"难度: {level.difficulty}")
        return " | ".join(infos)
