#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
طبقة قاعدة البيانات — SQLite
نظام إنتاج الوثائقيات الذكي v4.0 (نسخة مجانية بالكامل بدون مفاتيح API)
"""
import json
import sqlite3
import hashlib
from pathlib import Path

DB_PATH = Path(__file__).parent / "production.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


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
    # مستخدم افتراضي (يمكن تغييره من قاعدة البيانات لاحقاً)
    default_pass = hashlib.sha256("horizon2024".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users (username, password_hash) VALUES (?, ?)",
              ("basel", default_pass))
    conn.commit()
    conn.close()


def db_verify_user(username, password):
    conn = get_conn()
    c = conn.cursor()
    pass_hash = hashlib.sha256(password.encode()).hexdigest()
    c.execute("SELECT 1 FROM users WHERE username = ? AND password_hash = ?", (username, pass_hash))
    result = c.fetchone() is not None
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
