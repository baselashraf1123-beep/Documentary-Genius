#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   نظام إنتاج الوثائقيات الذكي — الإصدار 4.0 (مجاني بالكامل)      ║
║   Arabic Documentary Production System v4.0 — 100% Free           ║
║   قناة: أسرار ما وراء الأفق                                       ║
║   لا يتطلب أي مفتاح API — كل الخدمات مجانية ومدمجة                ║
╚══════════════════════════════════════════════════════════════════╝
"""
import json
import logging
import os
import secrets
import threading
import uuid
from functools import wraps
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS

from database import (
    init_db, db_verify_user, db_get_episodes, db_get_episode, db_delete_episode,
    db_insert_ideas, db_get_ideas, db_mark_idea_used, db_stats, db_change_password,
    db_get_setting, db_set_setting, db_get_settings_dict, db_set_episode_published
)
from pipeline import DocumentaryPipeline, STYLES, CHANNEL
import voice_engine
import image_engine
import ai_engine
import facebook_publisher

logging.basicConfig(level=logging.INFO, format="%(asctime)s │ %(levelname)s │ %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("🎬")

BASE_DIR = Path(__file__).parent
OUT = BASE_DIR / "output"

app = Flask(__name__, static_folder="static", static_url_path="")

_secret_key = os.environ.get("SECRET_KEY")
if not _secret_key:
    # لا يوجد مفتاح ثابت مكتوب بالكود: نولّد مفتاحاً عشوائياً عند كل إقلاع.
    # الأثر الوحيد: تسجيلات الدخول تُلغى عند إعادة تشغيل الخادم (وهذا أصلاً
    # سلوك النظام الحالي بسبب TOKENS في الذاكرة) — لكن لا يوجد مفتاح متوقَّع
    # يمكن لأي شخص استغلاله لتزوير الجلسات. للإنتاج: عرّف SECRET_KEY في البيئة
    # كي تبقى الجلسات صالحة عبر عمليات إعادة التشغيل.
    _secret_key = secrets.token_hex(32)
    log.warning("⚠️  SECRET_KEY غير مضبوط في البيئة — تم توليد مفتاح عشوائي مؤقت لهذا التشغيل.")
app.secret_key = _secret_key
app.config["SESSION_COOKIE_SAMESITE"] = "None"
app.config["SESSION_COOKIE_SECURE"] = True
CORS(app, supports_credentials=True)
app.config["MAX_CONTENT_LENGTH"] = 300 * 1024 * 1024

init_db()

# ══════════════════════════════════════════════════════════════
# مصادقة بالرمز (Bearer Token) — لعملاء تطبيق Flutter (ويب/أندرويد)
# تعمل جنباً إلى جنب مع مصادقة الجلسة (Cookie) الخاصة بواجهة الويب القديمة،
# لتجنّب أي مشاكل كوكيز عبر النطاقات (CORS/cross-origin) على منصّة الويب
# ولأن عميل http على أندرويد لا يخزّن الكوكيز تلقائياً بين الطلبات.
# ══════════════════════════════════════════════════════════════
TOKENS = {}  # token -> username
TOKENS_LOCK = threading.Lock()


def _extract_bearer_token():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    return None


# ══════════════════════════════════════════════════════════════
# إدارة المهام غير المتزامنة (Background Jobs) لتتبع التقدم الحقيقي
# ══════════════════════════════════════════════════════════════
JOBS = {}
JOBS_LOCK = threading.Lock()


def _set_job(job_id, **kwargs):
    with JOBS_LOCK:
        JOBS[job_id].update(kwargs)


def _run_production_job(job_id, topic, duration, style, voice, audio, generate_video):
    def progress_cb(pct, msg):
        _set_job(job_id, progress=pct, message=msg)

    try:
        pipe = DocumentaryPipeline(voice_key=voice, output_dir=OUT)
        result = pipe.run(topic, duration, style, audio, generate_video, progress_cb=progress_cb)
        _set_job(job_id, status="done", progress=100, message="اكتمل الإنتاج بنجاح!", result=result)
    except Exception as e:
        log.error(f"❌ خطأ في مهمة الإنتاج {job_id}: {e}")
        _set_job(job_id, status="error", error=str(e))


# ══════════════════════════════════════════════════════════════
# Middleware — تسجيل الدخول
# ══════════════════════════════════════════════════════════════
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("logged_in"):
            return f(*args, **kwargs)
        token = _extract_bearer_token()
        if token:
            with TOKENS_LOCK:
                if token in TOKENS:
                    return f(*args, **kwargs)
        return jsonify({"error": "يجب تسجيل الدخول"}), 401
    return decorated


# ══════════════════════════════════════════════════════════════
# الصفحة الرئيسية
# ══════════════════════════════════════════════════════════════
@app.route("/")
def index():
    return send_from_directory("static", "index.html")


# ══════════════════════════════════════════════════════════════
# حالة النظام — كل الخدمات مجانية دائماً بدون مفاتيح
# ══════════════════════════════════════════════════════════════
@app.route("/api/status")
def api_status():
    stats = db_stats()
    return jsonify({
        "status": "ok",
        "mode": "free",
        "ai_engine": "g4f (مجاني بالكامل)",
        "voice_engine": "Edge-TTS (مجاني بالكامل)",
        "image_engine": "Pollinations.ai (مجاني بالكامل)",
        "video_engine": "FFmpeg (محلي)",
        "requires_api_key": False,
        "channel": CHANNEL,
        "styles": STYLES,
        "voices": voice_engine.get_available_voices(),
        "logged_in": session.get("logged_in", False),
        "stats": stats,
    })


# ══════════════════════════════════════════════════════════════
# تسجيل الدخول / الخروج
# ══════════════════════════════════════════════════════════════
@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    if db_verify_user(username, password):
        session["logged_in"] = True
        session["username"] = username
        token = secrets.token_urlsafe(32)
        with TOKENS_LOCK:
            TOKENS[token] = username
        return jsonify({"success": True, "message": "تم تسجيل الدخول بنجاح", "token": token})
    return jsonify({"success": False, "error": "اسم المستخدم أو كلمة المرور غير صحيحة"}), 401


@app.route("/api/logout", methods=["POST"])
def api_logout():
    token = _extract_bearer_token()
    if token:
        with TOKENS_LOCK:
            TOKENS.pop(token, None)
    session.clear()
    return jsonify({"success": True, "message": "تم تسجيل الخروج"})


@app.route("/api/change-password", methods=["POST"])
@login_required
def api_change_password():
    data = request.get_json(silent=True) or {}
    username = session.get("username") or data.get("username", "").strip()
    current = data.get("current_password", "")
    new = data.get("new_password", "")
    if not username:
        return jsonify({"success": False, "error": "تعذّر تحديد المستخدم الحالي"}), 400
    if len(new) < 8:
        return jsonify({"success": False, "error": "كلمة المرور الجديدة يجب أن تكون 8 أحرف على الأقل"}), 400
    if not db_verify_user(username, current):
        return jsonify({"success": False, "error": "كلمة المرور الحالية غير صحيحة"}), 401
    db_change_password(username, new)
    return jsonify({"success": True, "message": "تم تغيير كلمة المرور بنجاح"})


# ══════════════════════════════════════════════════════════════
# إعدادات صفحة فيسبوك (Page ID + Access Token) — تُخزَّن في قاعدة
# البيانات فقط، وليست مكتوبة داخل الكود المصدري بأي شكل.
# ══════════════════════════════════════════════════════════════
@app.route("/api/settings/facebook", methods=["GET"])
@login_required
def api_get_facebook_settings():
    vals = db_get_settings_dict(["fb_page_id", "fb_page_token"])
    token = vals.get("fb_page_token") or ""
    return jsonify({
        "page_id": vals.get("fb_page_id") or "",
        # لا نُعيد الرمز كاملاً لواجهة العميل بعد حفظه، فقط نهايته للتأكيد المرئي
        "token_configured": bool(token),
        "token_preview": ("•" * 10 + token[-4:]) if token else "",
    })


@app.route("/api/settings/facebook", methods=["POST"])
@login_required
def api_set_facebook_settings():
    data = request.get_json(silent=True) or {}
    page_id = (data.get("page_id") or "").strip()
    token = (data.get("access_token") or "").strip()
    if page_id:
        db_set_setting("fb_page_id", page_id)
    if token:
        db_set_setting("fb_page_token", token)
    return jsonify({"success": True, "message": "تم حفظ إعدادات فيسبوك"})


@app.route("/api/settings/facebook/test", methods=["POST"])
@login_required
def api_test_facebook_settings():
    vals = db_get_settings_dict(["fb_page_id", "fb_page_token"])
    try:
        info = facebook_publisher.verify_page_token(vals.get("fb_page_id"), vals.get("fb_page_token"))
        return jsonify({"success": True, "page_name": info.get("name"), "fan_count": info.get("fan_count")})
    except facebook_publisher.FacebookPublishError as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ══════════════════════════════════════════════════════════════
# الإنتاج — بدء مهمة غير متزامنة + تتبع التقدم
# ══════════════════════════════════════════════════════════════
@app.route("/api/produce", methods=["POST"])
@login_required
def api_produce():
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "").strip()
    duration = int(data.get("duration", 4))
    style = data.get("style", "غامض_ومشوق")
    voice = data.get("voice", "أنتوني_رسمي")
    audio = bool(data.get("audio", True))
    generate_video = bool(data.get("generate_video", False))

    if not topic:
        return jsonify({"error": "الموضوع مطلوب"}), 400

    job_id = str(uuid.uuid4())
    with JOBS_LOCK:
        JOBS[job_id] = {"status": "running", "progress": 0, "message": "بدء الإنتاج...", "result": None, "error": None}

    thread = threading.Thread(
        target=_run_production_job,
        args=(job_id, topic, duration, style, voice, audio, generate_video),
        daemon=True
    )
    thread.start()

    return jsonify({"success": True, "job_id": job_id})


@app.route("/api/produce/status/<job_id>")
@login_required
def api_produce_status(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "مهمة غير موجودة"}), 404
    resp = {
        "status": job["status"],
        "progress": job["progress"],
        "message": job["message"],
    }
    if job["status"] == "done":
        resp["data"] = job["result"]
    elif job["status"] == "error":
        resp["error"] = job["error"]
    return jsonify(resp)


# ══════════════════════════════════════════════════════════════
# مولّد الأفكار
# ══════════════════════════════════════════════════════════════
@app.route("/api/ideas", methods=["POST"])
@login_required
def api_ideas():
    data = request.get_json(silent=True) or {}
    count = int(data.get("count", 9))
    topic_hint = data.get("topic_hint", "")
    try:
        ideas = DocumentaryPipeline.idea_generator(count, topic_hint)
        if ideas:
            db_insert_ideas(ideas)
        return jsonify({"success": True, "ideas": ideas})
    except Exception as e:
        log.error(f"❌ خطأ في توليد الأفكار: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/ideas/stored", methods=["GET"])
@login_required
def api_stored_ideas():
    unused = request.args.get("unused", "false").lower() == "true"
    ideas = db_get_ideas(limit=60, unused_only=unused)
    return jsonify({"success": True, "ideas": ideas})


@app.route("/api/ideas/use/<int:idea_id>", methods=["POST"])
@login_required
def api_use_idea(idea_id):
    db_mark_idea_used(idea_id)
    return jsonify({"success": True, "message": "تم تحديد الفكرة كمستخدمة"})


# ══════════════════════════════════════════════════════════════
# البيانات الوصفية (أصوات / أنماط)
# ══════════════════════════════════════════════════════════════
@app.route("/api/voices")
@login_required
def api_voices():
    return jsonify({"voices": voice_engine.get_available_voices()})


@app.route("/api/styles")
@login_required
def api_styles():
    return jsonify({"styles": STYLES})


# ══════════════════════════════════════════════════════════════
# التحميل
# ══════════════════════════════════════════════════════════════
@app.route("/api/download/<path:filename>")
@login_required
def api_download(filename):
    parts = filename.split("/")
    if len(parts) == 2:
        subdir, fname = parts
        allowed = {"scripts", "audio", "scenes", "seo", "packages", "videos", "thumbnails", "images"}
        if subdir not in allowed:
            return jsonify({"error": "مسار غير مسموح"}), 400
        full_dir = OUT / subdir
        if not (full_dir / fname).exists():
            return jsonify({"error": "الملف غير موجود"}), 404
        return send_from_directory(full_dir, fname, as_attachment=True)
    return jsonify({"error": "مسار غير صالح"}), 400


# نسخة بدون تسجيل دخول لتشغيل الصوت/الفيديو مباشرة داخل عناصر <audio>/<video>
# (بعض المتصفحات لا ترسل كوكيز الجلسة مع طلبات media تلقائياً في جميع الحالات)
@app.route("/api/media/<path:filename>")
def api_media(filename):
    parts = filename.split("/")
    if len(parts) == 2:
        subdir, fname = parts
        allowed = {"audio", "videos", "images", "thumbnails"}
        if subdir not in allowed:
            return jsonify({"error": "مسار غير مسموح"}), 400
        full_dir = OUT / subdir
        if not (full_dir / fname).exists():
            return jsonify({"error": "الملف غير موجود"}), 404
        return send_from_directory(full_dir, fname)
    return jsonify({"error": "مسار غير صالح"}), 400


# ══════════════════════════════════════════════════════════════
# الأرشيف
# ══════════════════════════════════════════════════════════════
@app.route("/api/packages")
@login_required
def api_packages():
    episodes = db_get_episodes(limit=100)
    packages = []
    for ep in episodes:
        try:
            script = json.loads(ep.get("script_json") or "{}")
        except Exception:
            script = {}
        packages.append({
            "id": ep["id"],
            "topic": ep.get("topic", "غير معروف"),
            "title": script.get("title", ""),
            "date": ep.get("created_at", ""),
            "duration": ep.get("duration", 0),
            "style": ep.get("style", ""),
            "has_audio": bool(ep.get("has_audio")),
            "has_video": bool(ep.get("has_video")),
            "fb_post_id": ep.get("fb_post_id"),
            "fb_published_at": ep.get("fb_published_at"),
        })
    return jsonify({"packages": packages})


@app.route("/api/packages/<int:ep_id>")
@login_required
def api_package_detail(ep_id):
    ep = db_get_episode(ep_id)
    if not ep:
        return jsonify({"error": "الحلقة غير موجودة"}), 404
    try:
        pkg = {
            "id": ep["id"],
            "channel": CHANNEL,
            "topic": ep["topic"],
            "duration_min": ep["duration"],
            "style": ep["style"],
            "voice": ep["voice"],
            "generated_at": ep["created_at"],
            "elapsed_sec": ep["elapsed_sec"],
            "script": json.loads(ep["script_json"]) if ep["script_json"] else {},
            "scenes": json.loads(ep["scenes_json"]) if ep["scenes_json"] else {},
            "seo": json.loads(ep["seo_json"]) if ep["seo_json"] else {},
            "audio_file": ep["audio_file"],
            "video_file": ep["video_file"],
            "thumbnail_file": ep["thumbnail_file"],
            "images": json.loads(ep["images_json"]) if ep.get("images_json") else [],
            "images_count": len(json.loads(ep["images_json"])) if ep.get("images_json") else 0,
            "fb_post_id": ep.get("fb_post_id"),
            "fb_published_at": ep.get("fb_published_at"),
            "fb_publish_error": ep.get("fb_publish_error"),
        }
        return jsonify({"success": True, "data": pkg})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/packages/<int:ep_id>", methods=["DELETE"])
@login_required
def api_package_delete(ep_id):
    db_delete_episode(ep_id)
    return jsonify({"success": True, "message": "تم حذف الحلقة"})


@app.route("/api/packages/<int:ep_id>/publish", methods=["POST"])
@login_required
def api_publish_to_facebook(ep_id):
    ep = db_get_episode(ep_id)
    if not ep:
        return jsonify({"success": False, "error": "الحلقة غير موجودة"}), 404
    if not ep.get("video_file"):
        return jsonify({"success": False, "error": "لا يوجد فيديو مُنتَج لهذه الحلقة بعد"}), 400

    vals = db_get_settings_dict(["fb_page_id", "fb_page_token"])
    page_id, token = vals.get("fb_page_id"), vals.get("fb_page_token")

    video_path = OUT / "videos" / ep["video_file"]
    if not video_path.exists():
        return jsonify({"success": False, "error": "ملف الفيديو غير موجود على الخادم"}), 404

    try:
        seo = json.loads(ep["seo_json"]) if ep.get("seo_json") else {}
    except Exception:
        seo = {}
    try:
        script = json.loads(ep["script_json"]) if ep.get("script_json") else {}
    except Exception:
        script = {}

    title = script.get("title") or ep.get("topic") or ""
    description = seo.get("description") or ""
    hashtags = seo.get("hashtags") or []
    if hashtags:
        description = f"{description}\n\n" + " ".join(hashtags)

    try:
        post_id = facebook_publisher.publish_video_to_page(
            video_path, page_id, token, title=title, description=description
        )
        db_set_episode_published(ep_id, fb_post_id=post_id)
        return jsonify({"success": True, "post_id": post_id})
    except facebook_publisher.FacebookPublishError as e:
        db_set_episode_published(ep_id, error=str(e))
        return jsonify({"success": False, "error": str(e)}), 400


# ══════════════════════════════════════════════════════════════
# توليد صورة مفردة (أداة مساعدة عامة)
# ══════════════════════════════════════════════════════════════
@app.route("/api/generate-image", methods=["POST"])
@login_required
def api_generate_image():
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "")
    width = int(data.get("width", 1024))
    height = int(data.get("height", 576))
    if not prompt:
        return jsonify({"error": "الوصف مطلوب"}), 400
    img_data = image_engine.generate_image(prompt, width, height)
    if img_data:
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        img_path = OUT / "images" / f"generated_{ts}.jpg"
        img_path.write_bytes(img_data)
        return jsonify({"success": True, "filename": f"images/{img_path.name}", "size": len(img_data)})
    return jsonify({"error": "فشل توليد الصورة، حاول مرة أخرى"}), 500


# ══════════════════════════════════════════════════════════════
# تشغيل التطبيق
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    log.info(f"🚀 تشغيل النظام المجاني بالكامل على http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug, threaded=True)
