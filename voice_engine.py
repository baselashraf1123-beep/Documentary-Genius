#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
محرك الصوت العربي المجاني بالكامل — Microsoft Edge TTS
لا يتطلب أي مفتاح API. يوفر أصواتاً عربية عصبية (Neural) طبيعية جداً
بجودة تنافس الخدمات المدفوعة مثل ElevenLabs.
"""
import asyncio
import logging
import re
import time
from datetime import datetime
from pathlib import Path

import edge_tts

log = logging.getLogger("🎙️")

# أصوات عربية مجانية عالية الجودة (Microsoft Neural Voices)
ARABIC_VOICES = {
    "أنتوني_رسمي": {"voice": "ar-SA-HamedNeural", "rate": "-3%", "desc": "صوت رجالي سعودي رسمي ووثائقي"},
    "آدم_قوي": {"voice": "ar-EG-ShakirNeural", "rate": "+0%", "desc": "صوت رجالي مصري قوي ومؤثر"},
    "جوش_درامي": {"voice": "ar-SY-LaithNeural", "rate": "-5%", "desc": "صوت رجالي سوري درامي مثير"},
    "أرنولد_تقارير": {"voice": "ar-JO-TaimNeural", "rate": "+2%", "desc": "صوت رجالي أردني بأسلوب تقارير إخبارية"},
    "ريتشل_نسائي": {"voice": "ar-EG-SalmaNeural", "rate": "+0%", "desc": "صوت نسائي مصري احترافي وواضح"},
}
DEFAULT_VOICE_KEY = "أنتوني_رسمي"
MAX_CHARS = 3000  # حجم كل جزء قبل التجزيء


def _split_text(text: str, max_chars: int = MAX_CHARS):
    if len(text) <= max_chars:
        return [text]
    # تجزيء عند علامات الترقيم للحفاظ على سلاسة النطق
    parts = re.split(r"(?<=[\.\!\؟\?])\s+", text)
    chunks, cur = [], ""
    for p in parts:
        if len(cur) + len(p) + 1 <= max_chars:
            cur = (cur + " " + p).strip()
        else:
            if cur:
                chunks.append(cur)
            cur = p
    if cur:
        chunks.append(cur)
    return chunks if chunks else [text]


async def _synthesize_async(text: str, voice: str, rate: str, out_path: Path):
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(str(out_path))


def generate_voiceover(text: str, voice_key: str, output_dir: Path, label: str = "full"):
    """
    يولد ملف صوت MP3 كامل من النص العربي باستخدام Edge TTS المجاني.
    يعيد اسم الملف النهائي (بدون المسار) أو None عند الفشل.
    """
    if not text or not text.strip():
        log.warning("⏭️ لا يوجد نص لتوليد الصوت")
        return None

    voice_info = ARABIC_VOICES.get(voice_key, ARABIC_VOICES[DEFAULT_VOICE_KEY])
    voice_id = voice_info["voice"]
    rate = voice_info["rate"]

    chunks = _split_text(text)
    log.info(f"   النص: {len(text)} حرف → {len(chunks)} جزء بصوت {voice_id}")

    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    parts = []

    for i, chunk in enumerate(chunks, 1):
        part_path = output_dir / f"_part_{i}_{ts}.mp3"
        # ⚠️ إصلاح فعلي (اكتُشف بمراجعة الكود): كانت أي عثرة شبكية عابرة واحدة في
        # جزء صوتي واحد (خدمة Edge-TTS خارجية) تُسقط توليد الصوت كاملاً فوراً —
        # وبما أن run() يشترط وجود mp3 صالح قبل توليد الصور/الفيديو، فهذا كان
        # يُسقط الحلقة بصرياً كاملة أيضاً بسبب عثرة شبكية عابرة في جزء واحد فقط.
        # نضيف هنا 3 محاولات بتأخير قصير لكل جزء قبل اعتبار الجزء فاشلاً فعلياً.
        ok = False
        for attempt in range(1, 4):
            try:
                log.info(f"   🔊 الجزء {i}/{len(chunks)} ({len(chunk)} حرف) — محاولة {attempt}...")
                asyncio.run(_synthesize_async(chunk, voice_id, rate, part_path))
                if part_path.exists() and part_path.stat().st_size > 0:
                    parts.append(part_path)
                    log.info(f"   ✅ الجزء {i} ({part_path.stat().st_size // 1024} KB)")
                    ok = True
                    break
                log.warning(f"   ⚠️ الجزء {i} (محاولة {attempt}): ملف فارغ")
            except Exception as e:
                log.warning(f"   ⚠️ الجزء {i} (محاولة {attempt}) فشل: {e}")
            if attempt < 3:
                time.sleep(3)
        if not ok:
            log.error(f"   ❌ الجزء {i} فشل بعد 3 محاولات — سيتم إيقاف توليد الصوت")
            return None

    final_path = output_dir / f"{label}_{ts}.mp3"
    if len(parts) == 1:
        parts[0].rename(final_path)
    else:
        try:
            import subprocess
            lst_path = output_dir / f"_concat_{ts}.txt"
            lst_path.write_text("\n".join(f"file '{p.absolute()}'" for p in parts), encoding="utf-8")
            subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst_path),
                 "-c", "copy", str(final_path)],
                check=True, capture_output=True
            )
            lst_path.unlink(missing_ok=True)
            for p in parts:
                p.unlink(missing_ok=True)
        except Exception as e:
            log.warning(f"⚠️ فشل دمج الأجزاء بـ ffmpeg: {e} — استخدام الجزء الأول فقط")
            final_path = parts[0]
            for p in parts[1:]:
                p.unlink(missing_ok=True)

    return final_path.name


def get_available_voices():
    return {k: v["desc"] for k, v in ARABIC_VOICES.items()}
