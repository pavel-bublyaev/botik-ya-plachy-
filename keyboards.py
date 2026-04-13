"""
🎮 Strinova Teammate Finder — Клавиатуры VK
"""
import json
from config import MODES, CHARACTERS, TIME_DAYS, TIME_PARTS


def kb(buttons, one_time=False, inline=False):
    keyboard = {
        "one_time": one_time,
        "inline": inline,
        "buttons": []
    }
    for row in buttons:
        kb_row = []
        for btn in row:
            if isinstance(btn, str):
                kb_row.append(text_btn(btn))
            elif isinstance(btn, tuple):
                kb_row.append(text_btn(btn[0], btn[1]))
            elif isinstance(btn, dict):
                kb_row.append(btn)
        keyboard["buttons"].append(kb_row)
    return json.dumps(keyboard, ensure_ascii=False)


def text_btn(label, color="secondary"):
    return {
        "action": {"type": "text", "label": label[:40]},
        "color": color,
    }


def empty_kb():
    return json.dumps({"buttons": [], "one_time": True}, ensure_ascii=False)


# ── Main menu ──

def main_menu_kb():
    return kb([
        [("🔍 Искать тиммейтов", "positive")],
        [("👤 Личный кабинет", "primary")],
        [("ℹ️ Помощь", "secondary")],
    ])


# ── Start ──

def start_kb():
    return kb([
        [("🎮 Создать анкету", "positive")],
        [("ℹ️ Как это работает?", "secondary")],
    ])


# ── Registration / Edit helpers ──

def back_kb():
    return kb([[("🔙 Назад", "secondary")]])


def skip_kb():
    return kb([[("⏭ Пропустить", "secondary")]])


def done_kb():
    return kb([[("✅ Готово", "positive")]])


def yes_no_kb():
    return kb([
        [("✅ Да", "positive"), ("❌ Нет", "negative")],
    ])


def modes_kb(selected=None):
    """Кнопки для выбора режимов."""
    selected = selected or []
    rows = []
    for mode in MODES:
        mark = "✅ " if mode in selected else ""
        color = "positive" if mode in selected else "secondary"
        rows.append([(f"{mark}{mode}", color)])
    rows.append([("📝 Другой (ввести)", "secondary")])
    rows.append([("✅ Готово", "positive")])
    return kb(rows)


def characters_kb(selected=None, page=0):
    """Кнопки для выбора персонажей (постранично, по 8)."""
    selected = selected or []
    per_page = 8
    start = page * per_page
    end = start + per_page
    chars_page = CHARACTERS[start:end]

    rows = []
    for i in range(0, len(chars_page), 2):
        row = []
        for j in range(i, min(i + 2, len(chars_page))):
            c = chars_page[j]
            mark = "✅ " if c in selected else ""
            color = "positive" if c in selected else "secondary"
            row.append((f"{mark}{c}", color))
        rows.append(row)

    # Navigation
    nav = []
    if page > 0:
        nav.append(("⬅️ Назад", "secondary"))
    total_pages = (len(CHARACTERS) + per_page - 1) // per_page
    if page < total_pages - 1:
        nav.append(("➡️ Далее", "secondary"))
    if nav:
        rows.append(nav)

    rows.append([("✅ Готово", "positive")])
    return kb(rows)


def play_days_kb(selected=None):
    selected = selected or []
    rows = []
    for d in TIME_DAYS:
        mark = "✅ " if d in selected else ""
        color = "positive" if d in selected else "secondary"
        rows.append([(f"{mark}{d}", color)])
    rows.append([("✅ Готово", "positive")])
    return kb(rows)


def play_times_kb(selected=None):
    selected = selected or []
    rows = []
    for t in TIME_PARTS:
        mark = "✅ " if t in selected else ""
        color = "positive" if t in selected else "secondary"
        rows.append([(f"{mark}{t}", color)])
    rows.append([("✅ Готово", "positive")])
    return kb(rows)


# ── Browse ──

def browse_kb():
    return kb([
        [("🎮 Го играть", "positive"), ("⏭ Некст", "negative")],
        [("🚫 Пожаловаться", "secondary")],
        [("🏠 Меню", "secondary")],
    ])


# ── Personal cabinet ──

def cabinet_kb():
    return kb([
        [("📋 Моя анкета", "primary")],
        [("✏️ Редактировать", "secondary"), ("💘 Кто меня лайкнул", "secondary")],
        [("🗑 Удалить анкету", "negative")],
        [("🏠 Меню", "secondary")],
    ])


def edit_kb():
    return kb([
        [("📝 Имя", "primary"), ("🎮 Ник в игре", "primary")],
        [("🕹 Режимы", "secondary"), ("👤 Персонажи", "secondary")],
        [("🕐 Время игры", "secondary"), ("📖 О себе", "secondary")],
        [("📷 Фото", "secondary")],
        [("🔙 Назад", "secondary")],
    ])


def menu_kb():
    return kb([[("🏠 Меню", "secondary")]])
