"""
🎮 Strinova Teammate Finder — База данных
"""
import sqlite3
import json
import time
from contextlib import contextmanager
from config import DB_PATH


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            vk_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL DEFAULT '',
            game_nick TEXT NOT NULL DEFAULT '',
            modes TEXT DEFAULT '[]',
            characters TEXT DEFAULT '[]',
            play_days TEXT DEFAULT '[]',
            play_times TEXT DEFAULT '[]',
            description TEXT DEFAULT '',
            photo TEXT DEFAULT '',
            is_active INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            created_at INTEGER DEFAULT (strftime('%s','now')),
            updated_at INTEGER DEFAULT (strftime('%s','now')),
            state TEXT DEFAULT '',
            state_data TEXT DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user INTEGER NOT NULL,
            to_user INTEGER NOT NULL,
            created_at INTEGER DEFAULT (strftime('%s','now')),
            UNIQUE(from_user, to_user),
            FOREIGN KEY(from_user) REFERENCES users(vk_id),
            FOREIGN KEY(to_user) REFERENCES users(vk_id)
        );

        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user1 INTEGER NOT NULL,
            user2 INTEGER NOT NULL,
            created_at INTEGER DEFAULT (strftime('%s','now')),
            UNIQUE(user1, user2),
            FOREIGN KEY(user1) REFERENCES users(vk_id),
            FOREIGN KEY(user2) REFERENCES users(vk_id)
        );

        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user INTEGER NOT NULL,
            to_user INTEGER NOT NULL,
            reason TEXT DEFAULT '',
            created_at INTEGER DEFAULT (strftime('%s','now')),
            resolved INTEGER DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_likes_from ON likes(from_user);
        CREATE INDEX IF NOT EXISTS idx_likes_to ON likes(to_user);
        """)


# ── User CRUD ──

def _parse_user(row):
    if not row:
        return None
    d = dict(row)
    for field in ("modes", "characters", "play_days", "play_times", "state_data"):
        try:
            d[field] = json.loads(d[field])
        except:
            d[field] = [] if field != "state_data" else {}
    return d


def get_user(vk_id):
    with get_db() as db:
        row = db.execute("SELECT * FROM users WHERE vk_id=?", (vk_id,)).fetchone()
        return _parse_user(row)


def create_user(vk_id):
    with get_db() as db:
        db.execute("INSERT OR IGNORE INTO users (vk_id) VALUES (?)", (vk_id,))
    return get_user(vk_id)


def update_user(vk_id, **fields):
    with get_db() as db:
        sets = []
        vals = []
        for k, v in fields.items():
            if isinstance(v, (dict, list)):
                v = json.dumps(v, ensure_ascii=False)
            sets.append(f"{k}=?")
            vals.append(v)
        sets.append("updated_at=?")
        vals.append(int(time.time()))
        vals.append(vk_id)
        db.execute(f"UPDATE users SET {','.join(sets)} WHERE vk_id=?", vals)


def delete_user(vk_id):
    with get_db() as db:
        db.execute("DELETE FROM users WHERE vk_id=?", (vk_id,))
        db.execute("DELETE FROM likes WHERE from_user=? OR to_user=?", (vk_id, vk_id))
        db.execute("DELETE FROM matches WHERE user1=? OR user2=?", (vk_id, vk_id))


def set_state(vk_id, state, state_data=None):
    update_user(vk_id, state=state, state_data=state_data or {})


def get_state(vk_id):
    user = get_user(vk_id)
    if user:
        return user["state"], user["state_data"]
    return "", {}


# ── Likes / Matches ──

def add_like(from_id, to_id):
    """Ставим лайк. Возвращаем True если матч."""
    with get_db() as db:
        db.execute(
            "INSERT OR IGNORE INTO likes (from_user, to_user) VALUES (?,?)",
            (from_id, to_id)
        )
    return check_match(from_id, to_id)


def check_match(user1, user2):
    with get_db() as db:
        row = db.execute(
            "SELECT 1 FROM likes WHERE from_user=? AND to_user=?",
            (user2, user1)
        ).fetchone()
        if row:
            u1, u2 = min(user1, user2), max(user1, user2)
            db.execute(
                "INSERT OR IGNORE INTO matches (user1, user2) VALUES (?,?)",
                (u1, u2)
            )
            return True
    return False


def get_matches(vk_id):
    with get_db() as db:
        rows = db.execute("""
            SELECT * FROM matches WHERE user1=? OR user2=?
            ORDER BY created_at DESC
        """, (vk_id, vk_id)).fetchall()
        result = []
        for r in rows:
            other = r["user2"] if r["user1"] == vk_id else r["user1"]
            u = get_user(other)
            if u and not u["is_banned"]:
                result.append(u)
        return result


def get_who_liked_me(vk_id):
    """Те кто лайкнул меня, но я их ещё не лайкнул (без взаимности)."""
    with get_db() as db:
        rows = db.execute("""
            SELECT l.from_user FROM likes l
            WHERE l.to_user = ?
            AND l.from_user NOT IN (
                SELECT to_user FROM likes WHERE from_user = ?
            )
            AND l.from_user NOT IN (
                SELECT user1 FROM matches WHERE user2 = ?
                UNION
                SELECT user2 FROM matches WHERE user1 = ?
            )
        """, (vk_id, vk_id, vk_id, vk_id)).fetchall()
        result = []
        for r in rows:
            u = get_user(r["from_user"])
            if u and not u["is_banned"] and u["is_active"]:
                result.append(u)
        return result


# ── Search ──

def find_candidates(vk_id, limit=30):
    """Найти анкеты для показа."""
    with get_db() as db:
        # Уже видели (лайкнули или скипнули — в likes лежат только лайки, скипы не храним,
        # но seen мы храним в state_data)
        seen = db.execute(
            "SELECT to_user FROM likes WHERE from_user=?", (vk_id,)
        ).fetchall()
        seen_ids = {r["to_user"] for r in seen}
        seen_ids.add(vk_id)

        rows = db.execute(
            "SELECT * FROM users WHERE is_active=1 AND is_banned=0 ORDER BY RANDOM() LIMIT ?",
            (limit + len(seen_ids),)
        ).fetchall()

        results = []
        for r in rows:
            if r["vk_id"] in seen_ids:
                continue
            results.append(_parse_user(r))
            if len(results) >= limit:
                break
        return results


# ── Reports ──

def report_user(from_id, to_id, reason=""):
    with get_db() as db:
        db.execute("INSERT INTO reports (from_user, to_user, reason) VALUES (?,?,?)", (from_id, to_id, reason))


# ── Admin ──

def get_stats():
    with get_db() as db:
        users = db.execute("SELECT COUNT(*) as c FROM users WHERE is_active=1").fetchone()["c"]
        matches = db.execute("SELECT COUNT(*) as c FROM matches").fetchone()["c"]
        reports = db.execute("SELECT COUNT(*) as c FROM reports WHERE resolved=0").fetchone()["c"]
        return {"users": users, "matches": matches, "reports": reports}


def ban_user(vk_id):
    update_user(vk_id, is_banned=1)


def unban_user(vk_id):
    update_user(vk_id, is_banned=0)
