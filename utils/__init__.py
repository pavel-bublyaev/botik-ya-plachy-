"""
🎮 Strinova Teammate Finder — Утилиты
"""


def format_profile(user, show_link=False):
    """Форматирование анкеты для отправки."""
    lines = []
    lines.append(f"🎮 {user.get('name', '—')}")
    lines.append(f"🏷 Ник: {user.get('game_nick', '—')}")

    modes = user.get("modes", [])
    if modes:
        lines.append(f"🕹 Режимы: {', '.join(modes)}")

    chars = user.get("characters", [])
    if chars:
        lines.append(f"👤 Персонажи: {', '.join(chars)}")

    days = user.get("play_days", [])
    times = user.get("play_times", [])
    time_str = ""
    if days:
        time_str += ", ".join(days)
    if times:
        if time_str:
            time_str += " / "
        time_str += ", ".join(times)
    if time_str:
        lines.append(f"🕐 Время: {time_str}")

    if user.get("description"):
        lines.append(f"\n📖 {user['description']}")

    if show_link:
        lines.append(f"\n💬 vk.com/id{user['vk_id']}")

    return "\n".join(lines)
