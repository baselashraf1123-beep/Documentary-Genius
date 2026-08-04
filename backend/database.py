#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
طبقة قاعدة البيانات — SQLite
نظام إنتاج الوثائقيات الذكي v4.1 (نسخة مجانية بالكامل بدون مفاتيح API)

التحديثات في v4.1:
- تجزئة كلمات المرور أصبحت PBKDF2-SHA256 مع "ملح" (salt) عبر werkzeug،
  بدل SHA-256 الخام غير المُملَّح. يوجد ترقية تلقائية شفافة لأي حساب قديم
  عند أول تسجيل دخول ناجح بالنظام القديم.
- جدول settings (key/value) لتخزين بيانات صفحة فيسبوك (Page ID + Access Token)
  بدل كتابتها داخل الكود مباشرة.
- أعمدة نشر فيسبوك على جدول الحلقات لتتبع حالة النشر.
"""
import json
import os
import secrets
import sqlite3
from pathlib import Path

from werkzeug.security import generate_password_hash, check_password_hash

# يمكن ضبط DB_PATH عبر متغيّر بيئة (مفيد عند تركيب Docker volume في مسار
# ثابت خارج مجلد الكود، حتى لا تُفقد البيانات عند إعادة بناء الحاوية).
DB_PATH = Path(os.environ.get("DB_PATH", str(Path(__file__).parent / "production.db")))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# هاش قديم (SHA-256 خام) = 64 حرف hex بدون أي فاصل "$".
# هاش werkzeug الحديث دائماً بصيغة "method$salt$hash" ويحوي "$".
_LEGACY_HASH_LEN = 64


def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def _ensure_column(c, table, column, coltype):
    """يضيف عموداً لجدول موجود إن لم يكن موجوداً بالفعل (ترقية آمنة لقواعد بيانات قديمة)."""
    c.execute(f"PRAGMA table_info({table})")
    existing = {row[1] for row in c.fetchall()}
    if column not in existing:
        c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS episodes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        topic TEXT NOT NULL,
        duration INTEGER DEFAULT 4,
        style TEXT DEFAULT 'غامض_ومشوق',
        voice TEXT DEFAULT 'أنتوني_رسمي',
        script_json TEXT,
        scenes_json TEXT,
        seo_json TEXT,
        audio_file TEXT,
        video_file TEXT,
        thumbnail_file TEXT,
        images_json TEXT,
        has_audio INTEGER DEFAULT 0,
        has_video INTEGER DEFAULT 0,
        elapsed_sec REAL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS ideas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT NOT NULL,
        hook_fact TEXT,
        mystery_level INTEGER DEFAULT 5,
        potential TEXT,
        estimated_audience TEXT,
        estimated_duration TEXT,
        keywords TEXT,
        used INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )""")

    # ترقية آمنة لقواعد بيانات منشأة بنسخة أقدم: أعمدة تتبّع النشر على فيسبوك
    _ensure_column(c, "episodes", "fb_post_id", "TEXT")
    _ensure_column(c, "episodes", "fb_published_at", "TEXT")
    _ensure_column(c, "episodes", "fb_publish_error", "TEXT")

    # مستخدم افتراضي بكلمة مرور عشوائية تُطبع في السجلّات مرة واحدة فقط.
    # لا تُستخدم كلمة مرور ثابتة معروفة كي لا يبقى أي تنصيب بكلمة سرّ متوقَّعة.
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        random_pass = secrets.token_urlsafe(9)
        c.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            ("basel", generate_password_hash(random_pass)),
        )
        print("=" * 64)
        print("تم إنشاء حساب أول مرة — احفظ هذه البيانات الآن:")
        print(f"  اسم المستخدم : basel")
        print(f"  كلمة المرور  : {random_pass}")
        print("(لن تُطبع هذه الرسالة مرة أخرى — غيّرها فوراً من الإعدادات)")
        print("=" * 64)

    conn.commit()
    conn.close()


def db_verify_user(username, password):
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    if not row:
        conn.close()
        return False

    stored = row["password_hash"]
    ok = False

    if len(stored) == _LEGACY_HASH_LEN and "$" not in stored:
        # هاش قديم (SHA-256 خام بدون ملح) — تحقق باستخدامه، ثم رقِّه فوراً.
        import hashlib
        ok = hashlib.sha256(password.encode()).hexdigest() == stored
        if ok:
            c.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (generate_password_hash(password), row["id"]),
            )
            conn.commit()
    else:
        ok = check_password_hash(stored, password)

    conn.close()
    return ok


def db_change_password(username, new_password):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "UPDATE users SET password_hash = ? WHERE username = ?",
        (generate_password_hash(new_password), username),
    )
    changed = c.rowcount > 0
    conn.commit()
    conn.close()
    return changed


# ══════════════════════════════════════════════════════════════
# الإعدادات (key/value) — تُستخدم لتخزين بيانات صفحة فيسبوك وغيرها
# بدل كتابتها داخل الكود المصدري.
# ══════════════════════════════════════════════════════════════
def db_get_setting(key, default=None):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else default


def db_set_setting(key, value):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()
    conn.close()


def db_get_settings_dict(keys):
    conn = get_conn()
    c = conn.cursor()
    q_marks = ",".join("?" * len(keys))
    c.execute(f"SELECT key, value FROM settings WHERE key IN ({q_marks})", keys)
    result = {k: None for k in keys}
    for k, v in c.fetchall():
        result[k] = v
    conn.close()
    return result


def db_insert_episode(data):
    conn = get_conn()
    c = conn.cursor()
    sc = data.get("script", {}) or {}
    c.execute("""INSERT INTO episodes
        (title, topic, duration, style, voice, script_json, scenes_json, seo_json,
         audio_file, video_file, thumbnail_file, images_json, has_audio, has_video, elapsed_sec)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (sc.get("title"), data.get("topic"), data.get("duration_min"),
         data.get("style"), data.get("voice"),
         json.dumps(data.get("script"), ensure_ascii=False),
         json.dumps(data.get("scenes"), ensure_ascii=False),
         json.dumps(data.get("seo"), ensure_ascii=False),
         data.get("audio_file"), data.get("video_file"), data.get("thumbnail_file"),
         json.dumps(data.get("images", []), ensure_ascii=False),
         1 if data.get("audio_file") else 0,
         1 if data.get("video_file") else 0,
         data.get("elapsed_sec")))
    ep_id = c.lastrowid
    conn.commit()
    conn.close()
    return ep_id


def db_get_episodes(limit=50):
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM episodes ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def db_get_episode(ep_id):
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM episodes WHERE id = ?", (ep_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def db_delete_episode(ep_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM episodes WHERE id = ?", (ep_id,))
    conn.commit()
    conn.close()


def db_set_episode_published(ep_id, fb_post_id=None, error=None):
    """يسجّل نتيجة محاولة النشر على فيسبوك (نجاح بمعرّف المنشور، أو فشل برسالة الخطأ)."""
    from datetime import datetime
    conn = get_conn()
    c = conn.cursor()
    if fb_post_id:
        c.execute(
            "UPDATE episodes SET fb_post_id = ?, fb_published_at = ?, fb_publish_error = NULL WHERE id = ?",
            (fb_post_id, datetime.now().isoformat(timespec="seconds"), ep_id),
        )
    else:
        c.execute(
            "UPDATE episodes SET fb_publish_error = ? WHERE id = ?",
            (error, ep_id),
        )
    conn.commit()
    conn.close()


def db_insert_ideas(ideas):
    conn = get_conn()
    c = conn.cursor()
    for idea in ideas:
        c.execute("""INSERT INTO ideas
            (topic, hook_fact, mystery_level, potential, estimated_audience, estimated_duration, keywords)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (idea.get("topic"), idea.get("hook_fact"), idea.get("mystery_level", 5),
             idea.get("potential"), idea.get("estimated_audience"), idea.get("estimated_duration"),
             json.dumps(idea.get("keywords", []), ensure_ascii=False)))
    conn.commit()
    conn.close()


def db_get_ideas(limit=50, unused_only=False):
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if unused_only:
        c.execute("SELECT * FROM ideas WHERE used = 0 ORDER BY created_at DESC LIMIT ?", (limit,))
    else:
        c.execute("SELECT * FROM ideas ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    for r in rows:
        try:
            r["keywords"] = json.loads(r.get("keywords") or "[]")
        except Exception:
            r["keywords"] = []
    return rows


def db_mark_idea_used(idea_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE ideas SET used = 1 WHERE id = ?", (idea_id,))
    conn.commit()
    conn.close()


def db_stats():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM episodes")
    episodes_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM episodes WHERE has_audio = 1")
    audio_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM episodes WHERE has_video = 1")
    video_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM ideas")
    ideas_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM ideas WHERE used = 0")
    unused_ideas = c.fetchone()[0]
    conn.close()
    return {
        "episodes": episodes_count,
        "with_audio": audio_count,
        "with_video": video_count,
        "ideas": ideas_count,
        "unused_ideas": unused_ideas,
    }
