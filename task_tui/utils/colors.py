def get_project_color(project_name: str) -> str:
    """Return a consistent color for a project name based on hash."""
    if not project_name:
        return "white"
    
    colors = [
        "green",
        "yellow",
        "blue",
        "magenta",
        "cyan",
        "white",
        "bright_black",
        "bright_red",
        "bright_green",
        "bright_yellow",
        "bright_blue",
        "bright_magenta",
        "bright_cyan",
        "bright_white",
        "orange1",
        "orange_red1",
        "orchid",
        "pale_green1",
        "pale_turquoise1",
        "hot_pink",
        "indian_red",
        "khaki1",
        "light_coral",
        "light_pink1",
        "light_salmon1",
        "light_sea_green",
        "light_skyblue1",
        "light_slate_blue",
        "light_steel_blue1",
        "medium_orchid1",
        "medium_purple1",
        "medium_spring_green",
    ]
    
    idx = sum(ord(c) for c in project_name) % len(colors)
    return colors[idx]


def get_priority_color(priority: str) -> str:
    """Return color for task priority."""
    return {"H": "red", "M": "yellow", "L": "green"}.get(priority, "white")


def format_urgency(urgency_val: float) -> str:
    """Format urgency value with bold red if > 20."""
    urgency_str = f"{urgency_val:.1f}"
    if urgency_val > 20:
        return f"[b][red]{urgency_str}[/][/]"
    return urgency_str
