"""
🎮 Strinova Teammate Finder — VK Bot

Бот для поиска тиммейтов в Strinova.
Запуск: python bot.py
"""
import json
import logging
import traceback

import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id
from vk_api.upload import VkUpload

from config import VK_TOKEN, VK_GROUP_ID, MODES, CHARACTERS, TIME_DAYS, TIME_PARTS, ADMIN_IDS
import database as db
from keyboards import (
    main_menu_kb, start_kb, back_kb, done_kb, yes_no_kb, empty_kb,
    modes_kb, characters_kb, play_days_kb, play_times_kb,
    browse_kb, cabinet_kb, edit_kb, menu_kb
)
from utils import format_profile

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("bot")

# ── VK init ──
vk_session = vk_api.VkApi(token=VK_TOKEN)
vk = vk_session.get_api()
upload = VkUpload(vk_session)


def send(user_id, message, keyboard=None, attachment=None):
    params = {
        "user_id": user_id,
        "message": message,
        "random_id": get_random_id(),
    }
    if keyboard:
        params["keyboard"] = keyboard
    if attachment:
        params["attachment"] = attachment
    try:
        vk.messages.send(**params)
    except Exception as e:
        log.error(f"Send error to {user_id}: {e}")


def get_photo_from_attachments(attachments):
    """Извлечь attachment-строку фото из вложений сообщения."""
    for att in (attachments or []):
        if att.get("type") == "photo":
            p = att["photo"]
            # Берём access_key если есть
            ak = f"_{p['access_key']}" if p.get("access_key") else ""
            return f"photo{p['owner_id']}_{p['id']}{ak}"
    return ""


def get_max_photo_url(attachments):
    """Получить URL самого большого фото из вложений."""
    for att in (attachments or []):
        if att.get("type") == "photo":
            sizes = att["photo"].get("sizes", [])
            if sizes:
                best = max(sizes, key=lambda s: s.get("width", 0) * s.get("height", 0))
                return best.get("url", "")
    return ""


# ═══════════════════════════════════════════
#  STATES
# ═══════════════════════════════════════════

# Registration
S_REG_NAME = "reg_name"
S_REG_NICK = "reg_nick"
S_REG_MODES = "reg_modes"
S_REG_MODES_CUSTOM = "reg_modes_custom"
S_REG_CHARS = "reg_chars"
S_REG_DAYS = "reg_days"
S_REG_TIMES = "reg_times"
S_REG_DESC = "reg_desc"
S_REG_PHOTO = "reg_photo"

# Browse
S_BROWSE = "browse"
S_BROWSE_REPORT = "browse_report"

# Cabinet
S_CABINET = "cabinet"

# Edit
S_EDIT = "edit"
S_EDIT_NAME = "edit_name"
S_EDIT_NICK = "edit_nick"
S_EDIT_MODES = "edit_modes"
S_EDIT_MODES_CUSTOM = "edit_modes_custom"
S_EDIT_CHARS = "edit_chars"
S_EDIT_DAYS = "edit_days"
S_EDIT_TIMES = "edit_times"
S_EDIT_DESC = "edit_desc"
S_EDIT_PHOTO = "edit_photo"
S_EDIT_DELETE = "edit_delete"

# Who liked me browse
S_LIKED_ME = "liked_me"


# ═══════════════════════════════════════════
#  MAIN HANDLER
# ═══════════════════════════════════════════

def handle_message(user_id, text, attachments=None):
    text = (text or "").strip()
    lower = text.lower()

    user = db.get_user(user_id)

    # ── Global ──
    if lower in ("начать", "start", "/start"):
        return cmd_start(user_id, user)
    if lower in ("🏠 меню", "меню", "menu", "/menu"):
        if user and user["is_active"]:
            db.set_state(user_id, "")
            return send(user_id, "🎮 Главное меню", main_menu_kb())
        return cmd_start(user_id, user)

    if not user:
        return cmd_start(user_id, None)

    if user["is_banned"]:
        return send(user_id, "⛔ Аккаунт заблокирован.")

    state, sdata = db.get_state(user_id)

    # ── Registration ──
    if state.startswith("reg_"):
        return handle_registration(user_id, state, sdata, text, attachments)

    # ── Browse ──
    if state == S_BROWSE:
        return handle_browse(user_id, sdata, text)
    if state == S_BROWSE_REPORT:
        return handle_report(user_id, sdata, text)

    # ── Cabinet / Edit ──
    if state == S_CABINET:
        return handle_cabinet(user_id, text)
    if state == S_EDIT or state.startswith("edit_"):
        return handle_edit(user_id, state, sdata, text, attachments)

    # ── Liked me ──
    if state == S_LIKED_ME:
        return handle_liked_me(user_id, sdata, text)

    # ── Menu buttons ──
    if "искать тиммейт" in lower or lower == "поиск":
        return cmd_search(user_id)
    if "личный кабинет" in lower or "кабинет" in lower:
        return cmd_cabinet(user_id)
    if "помощь" in lower or lower == "help":
        return cmd_help(user_id)
    if lower == "🎮 создать анкету":
        return start_registration(user_id)
    if lower == "ℹ️ как это работает?" or "как это работает" in lower:
        return cmd_help(user_id)

    send(user_id, "🎮 Жми кнопки или напиши /menu", main_menu_kb())


# ═══════════════════════════════════════════
#  COMMANDS
# ═══════════════════════════════════════════

def cmd_start(user_id, user):
    if user and user["is_active"]:
        db.set_state(user_id, "")
        send(user_id, f"👋 С возвращением, {user['name']}!\n🎮 Готов искать тиммейтов?", main_menu_kb())
    else:
        if not user:
            db.create_user(user_id)
        send(user_id,
             "👋 Привет! Я — Strinova Teammate Finder 🎮\n\n"
             "Помогу найти тиммейтов для катки в Strinova.\n"
             "Создай анкету и найди свою пати!\n\n"
             "⚡ Жми «Создать анкету»!",
             start_kb())


def cmd_search(user_id):
    user = db.get_user(user_id)
    if not user or not user["is_active"]:
        return send(user_id, "⚠️ Сначала создай анкету!", start_kb())

    candidates = db.find_candidates(user_id)
    if not candidates:
        return send(user_id, "😔 Пока нет подходящих анкет. Попробуй позже!", main_menu_kb())

    queue_ids = [c["vk_id"] for c in candidates]
    db.set_state(user_id, S_BROWSE, {"queue": queue_ids, "idx": 0})
    show_candidate(user_id)


def cmd_cabinet(user_id):
    user = db.get_user(user_id)
    if not user or not user["is_active"]:
        return send(user_id, "⚠️ Сначала создай анкету!", start_kb())
    db.set_state(user_id, S_CABINET)
    send(user_id, "👤 Личный кабинет", cabinet_kb())


def cmd_help(user_id):
    send(user_id,
         "ℹ️ ггвп ботик\n\n"
         "🔍 Искать тиммейтов — смотри анкеты\n"
         "🎮 Го играть — лайк! Если взаимно — матч!\n"
         "⏭ Некст — следующая анкета\n"
         "💘 Матч — бот пришлёт контакт обоим\n\n"
         "👤 Личный кабинет — анкета, редактирование\n"
         "💘 Кто лайкнул — посмотри кому ты зашёл\n\n"
         "🎮 GG, найди свою пати!",
         main_menu_kb())


# ═══════════════════════════════════════════
#  REGISTRATION
# ═══════════════════════════════════════════

def start_registration(user_id):
    user = db.get_user(user_id)
    if not user:
        db.create_user(user_id)
    db.set_state(user_id, S_REG_NAME, {})
    send(user_id, "🎮 Создаём анкету!\n\n📝 Как тебя зовут?", back_kb())


def handle_registration(user_id, state, sdata, text, attachments):
    lower = text.lower()

    if lower in ("🏠 меню", "меню"):
        db.set_state(user_id, "")
        return send(user_id, "🎮 Главное меню\n⚠️ Анкета не сохранена.", main_menu_kb())

    # ── Имя ──
    if state == S_REG_NAME:
        if len(text) < 1 or len(text) > 40:
            return send(user_id, "❌ Имя от 1 до 40 символов:")
        sdata["name"] = text
        db.set_state(user_id, S_REG_NICK, sdata)
        send(user_id, f"✅ Имя: {text}\n\n🎮 Твой ник в Strinova?", back_kb())

    # ── Ник в игре ──
    elif state == S_REG_NICK:
        if lower == "🔙 назад":
            db.set_state(user_id, S_REG_NAME, sdata)
            return send(user_id, "📝 Как тебя зовут?", back_kb())
        if len(text) < 1 or len(text) > 40:
            return send(user_id, "❌ Ник от 1 до 40 символов:")
        sdata["game_nick"] = text
        sdata["modes"] = []
        db.set_state(user_id, S_REG_MODES, sdata)
        send(user_id, "🕹 Выбери режимы (можно несколько):", modes_kb())

    # ── Режимы ──
    elif state == S_REG_MODES:
        if lower == "🔙 назад":
            db.set_state(user_id, S_REG_NICK, sdata)
            return send(user_id, "🎮 Ник в Strinova?", back_kb())
        if lower in ("✅ готово", "готово"):
            if not sdata.get("modes"):
                return send(user_id, "❌ Выбери хотя бы один режим!")
            sdata["characters"] = []
            sdata["char_page"] = 0
            db.set_state(user_id, S_REG_CHARS, sdata)
            return send(user_id, f"✅ Режимы: {', '.join(sdata['modes'])}\n\n👤 Выбери персонажей:", characters_kb([], 0))
        if "другой" in lower or "ввести" in lower:
            db.set_state(user_id, S_REG_MODES_CUSTOM, sdata)
            return send(user_id, "📝 Напиши название режима:", back_kb())
        # Toggle mode
        clean = text.replace("✅ ", "").strip()
        if clean in MODES:
            sel = sdata.get("modes", [])
            if clean in sel:
                sel.remove(clean)
            else:
                sel.append(clean)
            sdata["modes"] = sel
            db.set_state(user_id, S_REG_MODES, sdata)
            send(user_id, f"Выбрано: {', '.join(sel) if sel else 'ничего'}", modes_kb(sel))
        else:
            send(user_id, "Жми кнопки для выбора режимов:", modes_kb(sdata.get("modes", [])))

    # ── Кастомный режим ──
    elif state == S_REG_MODES_CUSTOM:
        if lower == "🔙 назад":
            db.set_state(user_id, S_REG_MODES, sdata)
            return send(user_id, "🕹 Выбери режимы:", modes_kb(sdata.get("modes", [])))
        if len(text) > 30:
            return send(user_id, "❌ Слишком длинное название (макс 30):")
        sel = sdata.get("modes", [])
        if text not in sel:
            sel.append(text)
        sdata["modes"] = sel
        db.set_state(user_id, S_REG_MODES, sdata)
        send(user_id, f"✅ Добавлено: {text}\nВыбрано: {', '.join(sel)}", modes_kb(sel))

    # ── Персонажи ──
    elif state == S_REG_CHARS:
        if lower == "🔙 назад":
            sdata["modes"] = sdata.get("modes", [])
            db.set_state(user_id, S_REG_MODES, sdata)
            return send(user_id, "🕹 Выбери режимы:", modes_kb(sdata.get("modes", [])))
        if lower in ("✅ готово", "готово"):
            if not sdata.get("characters"):
                return send(user_id, "❌ Выбери хотя бы одного персонажа!")
            sdata["play_days"] = []
            db.set_state(user_id, S_REG_DAYS, sdata)
            return send(user_id, f"✅ Персонажи: {', '.join(sdata['characters'])}\n\n🗓 Когда играешь? (дни):", play_days_kb())
        if lower in ("➡️ далее", "далее"):
            sdata["char_page"] = sdata.get("char_page", 0) + 1
            db.set_state(user_id, S_REG_CHARS, sdata)
            return send(user_id, "👤 Выбери персонажей:", characters_kb(sdata.get("characters", []), sdata["char_page"]))
        if lower in ("⬅️ назад",):
            sdata["char_page"] = max(0, sdata.get("char_page", 0) - 1)
            db.set_state(user_id, S_REG_CHARS, sdata)
            return send(user_id, "👤 Выбери персонажей:", characters_kb(sdata.get("characters", []), sdata["char_page"]))
        # Toggle character
        clean = text.replace("✅ ", "").strip()
        if clean in CHARACTERS:
            sel = sdata.get("characters", [])
            if clean in sel:
                sel.remove(clean)
            else:
                sel.append(clean)
            sdata["characters"] = sel
            db.set_state(user_id, S_REG_CHARS, sdata)
            send(user_id, f"Выбрано: {len(sel)} перс.", characters_kb(sel, sdata.get("char_page", 0)))
        else:
            send(user_id, "Жми кнопки:", characters_kb(sdata.get("characters", []), sdata.get("char_page", 0)))

    # ── Дни ──
    elif state == S_REG_DAYS:
        if lower == "🔙 назад":
            sdata["char_page"] = 0
            db.set_state(user_id, S_REG_CHARS, sdata)
            return send(user_id, "👤 Выбери персонажей:", characters_kb(sdata.get("characters", []), 0))
        if lower in ("✅ готово", "готово"):
            if not sdata.get("play_days"):
                return send(user_id, "❌ Выбери хотя бы один вариант!")
            sdata["play_times"] = []
            db.set_state(user_id, S_REG_TIMES, sdata)
            return send(user_id, "🕐 В какое время?:", play_times_kb())
        clean = text.replace("✅ ", "").strip()
        if clean in TIME_DAYS:
            sel = sdata.get("play_days", [])
            if clean in sel:
                sel.remove(clean)
            else:
                sel.append(clean)
            sdata["play_days"] = sel
            db.set_state(user_id, S_REG_DAYS, sdata)
            send(user_id, f"Выбрано: {', '.join(sel) if sel else 'ничего'}", play_days_kb(sel))
        else:
            send(user_id, "Жми кнопки:", play_days_kb(sdata.get("play_days", [])))

    # ── Время ──
    elif state == S_REG_TIMES:
        if lower == "🔙 назад":
            db.set_state(user_id, S_REG_DAYS, sdata)
            return send(user_id, "🗓 Когда играешь?:", play_days_kb(sdata.get("play_days", [])))
        if lower in ("✅ готово", "готово"):
            if not sdata.get("play_times"):
                return send(user_id, "❌ Выбери хотя бы одно время!")
            db.set_state(user_id, S_REG_DESC, sdata)
            return send(user_id, "📖 Пару слов о себе (до 200 символов):", back_kb())
        clean = text.replace("✅ ", "").strip()
        if clean in TIME_PARTS:
            sel = sdata.get("play_times", [])
            if clean in sel:
                sel.remove(clean)
            else:
                sel.append(clean)
            sdata["play_times"] = sel
            db.set_state(user_id, S_REG_TIMES, sdata)
            send(user_id, f"Выбрано: {', '.join(sel) if sel else 'ничего'}", play_times_kb(sel))
        else:
            send(user_id, "Жми кнопки:", play_times_kb(sdata.get("play_times", [])))

    # ── Описание ──
    elif state == S_REG_DESC:
        if lower == "🔙 назад":
            db.set_state(user_id, S_REG_TIMES, sdata)
            return send(user_id, "🕐 В какое время?:", play_times_kb(sdata.get("play_times", [])))
        sdata["description"] = text[:200]
        db.set_state(user_id, S_REG_PHOTO, sdata)
        send(user_id, "📷 Отправь фото для анкеты (обязательно):", back_kb())

    # ── Фото ──
    elif state == S_REG_PHOTO:
        if lower == "🔙 назад":
            db.set_state(user_id, S_REG_DESC, sdata)
            return send(user_id, "📖 О себе (до 200 символов):", back_kb())
        photo = get_photo_from_attachments(attachments)
        if not photo:
            return send(user_id, "❌ Нужно отправить фото! Прикрепи картинку:", back_kb())
        sdata["photo"] = photo

        # Сохраняем
        db.update_user(user_id,
                       name=sdata.get("name", ""),
                       game_nick=sdata.get("game_nick", ""),
                       modes=sdata.get("modes", []),
                       characters=sdata.get("characters", []),
                       play_days=sdata.get("play_days", []),
                       play_times=sdata.get("play_times", []),
                       description=sdata.get("description", ""),
                       photo=photo,
                       is_active=1)
        db.set_state(user_id, "")

        user = db.get_user(user_id)
        msg = f"🎉 Анкета создана! GG!\n\n{format_profile(user)}\n\n🔍 Жми «Искать тиммейтов»!"
        send(user_id, msg, main_menu_kb(), attachment=photo)


# ═══════════════════════════════════════════
#  BROWSE — поиск тиммейтов
# ═══════════════════════════════════════════

def show_candidate(user_id):
    state, sdata = db.get_state(user_id)
    queue = sdata.get("queue", [])
    idx = sdata.get("idx", 0)

    if idx >= len(queue):
        db.set_state(user_id, "")
        return send(user_id, "🏁 Анкеты закончились! Заходи позже.", main_menu_kb())

    target_id = queue[idx]
    target = db.get_user(target_id)

    if not target or target["is_banned"] or not target["is_active"]:
        sdata["idx"] = idx + 1
        db.set_state(user_id, S_BROWSE, sdata)
        return show_candidate(user_id)

    remaining = len(queue) - idx
    msg = f"📋 Анкета ({remaining} ост.)\n\n{format_profile(target)}"

    photo = target.get("photo", "")
    send(user_id, msg, browse_kb(), attachment=photo if photo else None)


def handle_browse(user_id, sdata, text):
    lower = text.lower()
    queue = sdata.get("queue", [])
    idx = sdata.get("idx", 0)

    if lower in ("🏠 меню", "меню"):
        db.set_state(user_id, "")
        return send(user_id, "🎮 Главное меню", main_menu_kb())

    if idx >= len(queue):
        db.set_state(user_id, "")
        return send(user_id, "🏁 Анкеты закончились!", main_menu_kb())

    target_id = queue[idx]

    if "го играть" in lower or lower == "лайк" or lower == "👍":
        is_match = db.add_like(user_id, target_id)
        if is_match:
            target = db.get_user(target_id)
            me = db.get_user(user_id)
            # Уведомление обоим
            send(user_id,
                 f"💘 МАТЧ! Ты и {target['name']} хотите играть вместе!\n\n"
                 f"{format_profile(target, show_link=True)}",
                 main_menu_kb(),
                 attachment=target.get("photo", "") or None)
            send(target_id,
                 f"💘 МАТЧ! {me['name']} тоже хочет играть с тобой!\n\n"
                 f"{format_profile(me, show_link=True)}",
                 main_menu_kb(),
                 attachment=me.get("photo", "") or None)
        else:
            send(user_id, "🎮 Лайк отправлен! Ждём взаимности...")
            # Уведомление тому кого лайкнули
            me = db.get_user(user_id)
            send(target_id, f"👀 Кто-то хочет с тобой играть!\nЗагляни в «Личный кабинет» → «Кто меня лайкнул» 💘", menu_kb())

    elif "некст" in lower or "пропустить" in lower or lower == "👎":
        pass  # просто пропускаем

    elif "пожаловаться" in lower or "жалоба" in lower:
        db.set_state(user_id, S_BROWSE_REPORT, {**sdata, "report_target": target_id})
        return send(user_id, "🚫 Причина жалобы?", back_kb())

    else:
        return send(user_id, "Жми кнопки:", browse_kb())

    # Следующая анкета
    sdata["idx"] = idx + 1
    db.set_state(user_id, S_BROWSE, sdata)
    show_candidate(user_id)


def handle_report(user_id, sdata, text):
    if text.lower() in ("🔙 назад", "назад"):
        db.set_state(user_id, S_BROWSE, sdata)
        return show_candidate(user_id)

    target_id = sdata.get("report_target")
    if target_id:
        db.report_user(user_id, target_id, text[:300])
        send(user_id, "✅ Жалоба отправлена.")

    sdata["idx"] = sdata.get("idx", 0) + 1
    db.set_state(user_id, S_BROWSE, sdata)
    show_candidate(user_id)


# ═══════════════════════════════════════════
#  CABINET — личный кабинет
# ═══════════════════════════════════════════

def handle_cabinet(user_id, text):
    lower = text.lower()

    if lower in ("🏠 меню", "меню"):
        db.set_state(user_id, "")
        return send(user_id, "🎮 Главное меню", main_menu_kb())

    if "моя анкета" in lower or "📋" in text:
        user = db.get_user(user_id)
        msg = f"👤 Твоя анкета:\n\n{format_profile(user)}"
        return send(user_id, msg, cabinet_kb(), attachment=user.get("photo", "") or None)

    if "редактировать" in lower or "✏️" in text:
        db.set_state(user_id, S_EDIT)
        return send(user_id, "✏️ Что изменить?", edit_kb())

    if "кто меня лайкнул" in lower or "💘" in text:
        return cmd_who_liked_me(user_id)

    if "удалить анкету" in lower or "🗑" in text:
        db.set_state(user_id, S_EDIT_DELETE)
        return send(user_id, "⚠️ Точно удалить анкету? Все матчи пропадут!", yes_no_kb())

    send(user_id, "Жми кнопки:", cabinet_kb())


def cmd_who_liked_me(user_id):
    likers = db.get_who_liked_me(user_id)
    if not likers:
        return send(user_id, "💔 Пока никто не лайкнул. Продолжай искать!", cabinet_kb())

    queue_ids = [u["vk_id"] for u in likers]
    db.set_state(user_id, S_LIKED_ME, {"queue": queue_ids, "idx": 0})
    show_liker(user_id)


def show_liker(user_id):
    state, sdata = db.get_state(user_id)
    queue = sdata.get("queue", [])
    idx = sdata.get("idx", 0)

    if idx >= len(queue):
        db.set_state(user_id, S_CABINET)
        return send(user_id, "🏁 Все лайки просмотрены!", cabinet_kb())

    liker = db.get_user(queue[idx])
    if not liker or liker["is_banned"]:
        sdata["idx"] = idx + 1
        db.set_state(user_id, S_LIKED_ME, sdata)
        return show_liker(user_id)

    remaining = len(queue) - idx
    msg = f"💘 Тебя лайкнул ({remaining} ост.):\n\n{format_profile(liker)}"
    send(user_id, msg, browse_kb(), attachment=liker.get("photo", "") or None)


def handle_liked_me(user_id, sdata, text):
    lower = text.lower()
    queue = sdata.get("queue", [])
    idx = sdata.get("idx", 0)

    if lower in ("🏠 меню", "меню"):
        db.set_state(user_id, "")
        return send(user_id, "🎮 Главное меню", main_menu_kb())

    if idx >= len(queue):
        db.set_state(user_id, S_CABINET)
        return send(user_id, "🏁 Все просмотрены!", cabinet_kb())

    target_id = queue[idx]

    if "го играть" in lower or "лайк" in lower:
        is_match = db.add_like(user_id, target_id)
        if is_match:
            target = db.get_user(target_id)
            me = db.get_user(user_id)
            send(user_id,
                 f"💘 МАТЧ! Ты и {target['name']} хотите играть вместе!\n\n"
                 f"{format_profile(target, show_link=True)}",
                 main_menu_kb(),
                 attachment=target.get("photo", "") or None)
            send(target_id,
                 f"💘 МАТЧ! {me['name']} тоже хочет играть с тобой!\n\n"
                 f"{format_profile(me, show_link=True)}",
                 main_menu_kb(),
                 attachment=me.get("photo", "") or None)
            sdata["idx"] = idx + 1
            db.set_state(user_id, S_LIKED_ME, sdata)
            return show_liker(user_id)
    elif "некст" in lower or "пропустить" in lower:
        pass
    else:
        return send(user_id, "Жми кнопки:", browse_kb())

    sdata["idx"] = idx + 1
    db.set_state(user_id, S_LIKED_ME, sdata)
    show_liker(user_id)


# ═══════════════════════════════════════════
#  EDIT — редактирование анкеты
# ═══════════════════════════════════════════

def handle_edit(user_id, state, sdata, text, attachments):
    lower = text.lower()

    if lower in ("🏠 меню", "меню"):
        db.set_state(user_id, "")
        return send(user_id, "🎮 Главное меню", main_menu_kb())
    if lower in ("🔙 назад", "назад") and state == S_EDIT:
        db.set_state(user_id, S_CABINET)
        return send(user_id, "👤 Личный кабинет", cabinet_kb())
    if lower in ("🔙 назад", "назад"):
        db.set_state(user_id, S_EDIT)
        return send(user_id, "✏️ Что изменить?", edit_kb())

    # ── Edit menu ──
    if state == S_EDIT:
        if "имя" in lower or "📝 имя" in lower:
            db.set_state(user_id, S_EDIT_NAME)
            return send(user_id, "📝 Новое имя:", back_kb())
        elif "ник" in lower:
            db.set_state(user_id, S_EDIT_NICK)
            return send(user_id, "🎮 Новый ник в игре:", back_kb())
        elif "режим" in lower:
            user = db.get_user(user_id)
            sdata["modes"] = user.get("modes", [])
            db.set_state(user_id, S_EDIT_MODES, sdata)
            return send(user_id, "🕹 Выбери режимы:", modes_kb(sdata["modes"]))
        elif "персонаж" in lower:
            user = db.get_user(user_id)
            sdata["characters"] = user.get("characters", [])
            sdata["char_page"] = 0
            db.set_state(user_id, S_EDIT_CHARS, sdata)
            return send(user_id, "👤 Выбери персонажей:", characters_kb(sdata["characters"], 0))
        elif "время" in lower:
            user = db.get_user(user_id)
            sdata["play_days"] = user.get("play_days", [])
            sdata["play_times"] = user.get("play_times", [])
            db.set_state(user_id, S_EDIT_DAYS, sdata)
            return send(user_id, "🗓 Дни:", play_days_kb(sdata["play_days"]))
        elif "о себе" in lower:
            db.set_state(user_id, S_EDIT_DESC)
            return send(user_id, "📖 Новое описание (до 200 символов):", back_kb())
        elif "фото" in lower:
            db.set_state(user_id, S_EDIT_PHOTO)
            return send(user_id, "📷 Отправь новое фото:", back_kb())
        return send(user_id, "Жми кнопки:", edit_kb())

    # ── Edit fields ──
    if state == S_EDIT_NAME:
        if len(text) < 1 or len(text) > 40:
            return send(user_id, "❌ Имя от 1 до 40 символов:")
        db.update_user(user_id, name=text)
        send(user_id, f"✅ Имя обновлено: {text}")
        db.set_state(user_id, S_EDIT)
        return send(user_id, "✏️ Что ещё изменить?", edit_kb())

    if state == S_EDIT_NICK:
        if len(text) < 1 or len(text) > 40:
            return send(user_id, "❌ Ник от 1 до 40 символов:")
        db.update_user(user_id, game_nick=text)
        send(user_id, f"✅ Ник обновлён: {text}")
        db.set_state(user_id, S_EDIT)
        return send(user_id, "✏️ Что ещё изменить?", edit_kb())

    if state == S_EDIT_MODES:
        if lower in ("✅ готово", "готово"):
            if not sdata.get("modes"):
                return send(user_id, "❌ Выбери хотя бы один!")
            db.update_user(user_id, modes=sdata["modes"])
            send(user_id, f"✅ Режимы обновлены: {', '.join(sdata['modes'])}")
            db.set_state(user_id, S_EDIT)
            return send(user_id, "✏️ Что ещё?", edit_kb())
        if "другой" in lower or "ввести" in lower:
            db.set_state(user_id, S_EDIT_MODES_CUSTOM, sdata)
            return send(user_id, "📝 Название режима:", back_kb())
        clean = text.replace("✅ ", "").strip()
        if clean in MODES:
            sel = sdata.get("modes", [])
            if clean in sel:
                sel.remove(clean)
            else:
                sel.append(clean)
            sdata["modes"] = sel
            db.set_state(user_id, S_EDIT_MODES, sdata)
            return send(user_id, f"Выбрано: {', '.join(sel) if sel else 'ничего'}", modes_kb(sel))
        return send(user_id, "Жми кнопки:", modes_kb(sdata.get("modes", [])))

    if state == S_EDIT_MODES_CUSTOM:
        if len(text) > 30:
            return send(user_id, "❌ Макс 30 символов:")
        sel = sdata.get("modes", [])
        if text not in sel:
            sel.append(text)
        sdata["modes"] = sel
        db.set_state(user_id, S_EDIT_MODES, sdata)
        return send(user_id, f"✅ Добавлено. Выбрано: {', '.join(sel)}", modes_kb(sel))

    if state == S_EDIT_CHARS:
        if lower in ("✅ готово", "готово"):
            if not sdata.get("characters"):
                return send(user_id, "❌ Выбери хотя бы одного!")
            db.update_user(user_id, characters=sdata["characters"])
            send(user_id, f"✅ Персонажи обновлены ({len(sdata['characters'])})")
            db.set_state(user_id, S_EDIT)
            return send(user_id, "✏️ Что ещё?", edit_kb())
        if lower in ("➡️ далее", "далее"):
            sdata["char_page"] = sdata.get("char_page", 0) + 1
            db.set_state(user_id, S_EDIT_CHARS, sdata)
            return send(user_id, "👤 Персонажи:", characters_kb(sdata.get("characters", []), sdata["char_page"]))
        if lower in ("⬅️ назад",):
            sdata["char_page"] = max(0, sdata.get("char_page", 0) - 1)
            db.set_state(user_id, S_EDIT_CHARS, sdata)
            return send(user_id, "👤 Персонажи:", characters_kb(sdata.get("characters", []), sdata["char_page"]))
        clean = text.replace("✅ ", "").strip()
        if clean in CHARACTERS:
            sel = sdata.get("characters", [])
            if clean in sel:
                sel.remove(clean)
            else:
                sel.append(clean)
            sdata["characters"] = sel
            db.set_state(user_id, S_EDIT_CHARS, sdata)
            return send(user_id, f"Выбрано: {len(sel)}", characters_kb(sel, sdata.get("char_page", 0)))
        return send(user_id, "Жми кнопки:", characters_kb(sdata.get("characters", []), sdata.get("char_page", 0)))

    if state == S_EDIT_DAYS:
        if lower in ("✅ готово", "готово"):
            if not sdata.get("play_days"):
                return send(user_id, "❌ Выбери хотя бы один!")
            db.set_state(user_id, S_EDIT_TIMES, sdata)
            return send(user_id, "🕐 Время:", play_times_kb(sdata.get("play_times", [])))
        clean = text.replace("✅ ", "").strip()
        if clean in TIME_DAYS:
            sel = sdata.get("play_days", [])
            if clean in sel:
                sel.remove(clean)
            else:
                sel.append(clean)
            sdata["play_days"] = sel
            db.set_state(user_id, S_EDIT_DAYS, sdata)
            return send(user_id, f"Выбрано: {', '.join(sel) if sel else 'ничего'}", play_days_kb(sel))
        return send(user_id, "Жми кнопки:", play_days_kb(sdata.get("play_days", [])))

    if state == S_EDIT_TIMES:
        if lower in ("✅ готово", "готово"):
            if not sdata.get("play_times"):
                return send(user_id, "❌ Выбери хотя бы одно!")
            db.update_user(user_id, play_days=sdata["play_days"], play_times=sdata["play_times"])
            send(user_id, "✅ Время обновлено!")
            db.set_state(user_id, S_EDIT)
            return send(user_id, "✏️ Что ещё?", edit_kb())
        clean = text.replace("✅ ", "").strip()
        if clean in TIME_PARTS:
            sel = sdata.get("play_times", [])
            if clean in sel:
                sel.remove(clean)
            else:
                sel.append(clean)
            sdata["play_times"] = sel
            db.set_state(user_id, S_EDIT_TIMES, sdata)
            return send(user_id, f"Выбрано: {', '.join(sel) if sel else 'ничего'}", play_times_kb(sel))
        return send(user_id, "Жми кнопки:", play_times_kb(sdata.get("play_times", [])))

    if state == S_EDIT_DESC:
        db.update_user(user_id, description=text[:200])
        send(user_id, "✅ Описание обновлено!")
        db.set_state(user_id, S_EDIT)
        return send(user_id, "✏️ Что ещё?", edit_kb())

    if state == S_EDIT_PHOTO:
        photo = get_photo_from_attachments(attachments)
        if not photo:
            return send(user_id, "❌ Прикрепи фото!", back_kb())
        db.update_user(user_id, photo=photo)
        send(user_id, "✅ Фото обновлено!", attachment=photo)
        db.set_state(user_id, S_EDIT)
        return send(user_id, "✏️ Что ещё?", edit_kb())

    if state == S_EDIT_DELETE:
        if "да" in lower or "✅" in text:
            db.delete_user(user_id)
            db.create_user(user_id)  # чтобы state работал
            db.set_state(user_id, "")
            return send(user_id, "🗑 Анкета удалена. Напиши /start чтобы создать новую.", start_kb())
        else:
            db.set_state(user_id, S_CABINET)
            return send(user_id, "✅ Отменено.", cabinet_kb())


# ═══════════════════════════════════════════
#  MAIN LOOP
# ═══════════════════════════════════════════

def main():
    db.init_db()
    log.info("🎮 Strinova Teammate Finder запущен!")
    log.info(f"   Group ID: {VK_GROUP_ID}")

    longpoll = VkBotLongPoll(vk_session, VK_GROUP_ID)

    for event in longpoll.listen():
        try:
            if event.type == VkBotEventType.MESSAGE_NEW:
                msg = event.object.message
                user_id = msg["from_id"]
                text = msg.get("text", "")
                attachments = msg.get("attachments", [])
                handle_message(user_id, text, attachments)
        except Exception as e:
            log.error(f"Error: {e}\n{traceback.format_exc()}")


if __name__ == "__main__":
    main()
