#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
محرك توليد الصور المجاني بالكامل — Pollinations.ai (Flux)
لا يتطلب أي مفتاح API — طلبات مجهولة (anonymous) مجانية بالكامل.
"""
import logging
import time
from datetime import datetime
from pathlib import Path

import requests

log = logging.getLogger("🖼️")

IMG_BASE = "https://image.pollinations.ai/prompt"


def generate_image(prompt: str, width: int = 1024, height: int = 576, seed: int = None, retries: int = 3):
    """يولد صورة واحدة عبر Pollinations.ai ويعيد bytes الصورة أو None."""
    if seed is None:
        seed = int(time.time() * 1000) % 2_000_000_000
    encoded = requests.utils.quote(prompt[:800])
    url = f"{IMG_BASE}/{encoded}?width={width}&height={height}&seed={seed}&nologo=true&enhance=true"
    for attempt in range(retries):
        try:
            resp = requests.get(url, timeout=90)
            if resp.status_code == 200 and len(resp.content) > 1000:
                return resp.content
            log.warning(f"⚠️ Pollinations status={resp.status_code} (محاولة {attempt+1})")
        except Exception as e:
            log.warning(f"⚠️ خطأ Pollinations (محاولة {attempt+1}): {e}")
        time.sleep(1.5)
    return None


def generate_images_for_scenes(scenes_data: dict, output_dir: Path, width=1920, height=1080):
    """
    يولد صورة لكل مشهد (لقطة) بناءً على midjourney_prompt أو veo3_prompt، ويحفظها على القرص.
    ⚠️ إن فشل توليد صورة لقطة معيّنة، يتم استبعاد تلك اللقطة من scenes_data["sections"]
    (تحديث فعلي بالمرجع In-place) لضمان بقاء عدد الصور == عدد اللقطات دائماً 100%،
    وهو أمر ضروري لحساب مدة عرض كل صورة بدقة في video_engine لاحقاً.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    sections = scenes_data.get("sections", [])
    log.info(f"🖼️ توليد {len(sections)} صورة (لقطة واحدة ≤10ث لكل صورة)...")
    saved = []
    matched_sections = []
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    for i, sec in enumerate(sections):
        prompt = sec.get("midjourney_prompt") or sec.get("veo3_prompt") or "cinematic documentary scene, 4k"
        # ⚠️ إصلاح فعلي (مؤكَّد بالفحص البصري لكل الصور): مشهدان من 6 خرجا غير واقعيين —
        # واحد بإطار "قصاصة جريدة" مزيّف بنص عشوائي غير مقروء، وآخر أشبه برسم/بوستر دعائي
        # (سببه كلمة "propaganda" في البرومبت التي تدفع النموذج لأسلوب الملصق لا الصورة).
        # الحل: استبدال الكلمات المحفِّزة على أسلوب الرسم/الملصق، وإضافة لاحقة تفرض
        # فوتوغرافيا واقعية صريحة وتمنع أي إطار/نص/عناوين مزيّفة داخل الصورة.
        prompt = prompt.replace("propaganda", "historical newsreel footage").replace("Propaganda", "Historical newsreel footage")
        prompt = (
            f"{prompt}, ultra-realistic documentary photography, real photo, shot on DSLR, "
            f"35mm film grain, natural lighting, photojournalism style, no illustration, "
            f"no painting, no drawing, no poster art, no text, no caption, no frame, no border, no watermark"
        )
        log.info(f"   🖼️ صورة {i+1}/{len(sections)}...")
        img = generate_image(prompt, width=width, height=height, seed=int(time.time()) + i)
        if img:
            img_path = output_dir / f"scene_{i+1:02d}_{ts}.jpg"
            img_path.write_bytes(img)
            saved.append(img_path)
            matched_sections.append(sec)
            log.info(f"   ✅ صورة {i+1} ({len(img)//1024} KB) — مدة اللقطة: {sec.get('duration_seconds', '?')}ث")
        else:
            log.warning(f"   ⚠️ فشل توليد صورة {i+1} — سيُسقط هذا المشهد من الفيديو النهائي")
        time.sleep(0.6)

    # ⚠️ تحديث scenes_data['sections'] ليطابق بالضبط اللقطات الناجحة فقط — يضمن
    # أن video_engine لاحقاً يحسب مدة كل صورة بدقة (len(sections)==len(images) دائماً)
    scenes_data["sections"] = matched_sections
    if len(saved) < len(sections):
        log.warning(
            f"⚠️ نجح {len(saved)}/{len(sections)} لقطة فقط — اللقطات الفاشلة استُبعدت من المونتاتاج النهائي"
        )
    return saved


def generate_thumbnail(prompt: str, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    img = generate_image(prompt, width=1280, height=720)
    if not img:
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"thumb_{ts}.jpg"
    path.write_bytes(img)
    return path.name
