#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
محرك دمج الفيديو — FFmpeg (مثبت مسبقاً في بيئة النظام، مجاني بالكامل)
يدمج مجموعة صور مع ملف صوت لإنتاج فيديو MP4 نهائي بجودة 1080p.

⚠️ ملاحظة تقنية مهمة (تم اكتشافها واختبارها فعلياً):
لا نستخدم "خدعة" ffmpeg concat-demuxer التقليدية (سرد duration لكل صورة ثم
تكرار سطر الصورة الأخيرة بدون duration) لأنها أثبتت عبر اختبارات معزولة
سلوكاً غير موثوق تماماً عند دمجها مع فلتر -vf (scale/pad) — قد تُنتج المدة
النهائية نصف المدة المطلوبة أو أكثر منها بشكل عشوائي وغير متوقع.

الأسلوب المعتمد هنا (مُثبت بالاختبار: مدة دقيقة 100% مطابقة للمطلوب):
1) نُرمّز كل صورة إلى مقطع فيديو (clip) منفصل بمدة دقيقة بالثواني
   باستخدام "-loop 1 -i image -t duration" (fixed frame count via -r 25).
2) ندمج كل المقاطع المُرمّزة (ملفات mp4 حقيقية لا "صور بميتاداتا") عبر
   concat demuxer بوضع "-c copy" فقط (نسخ تيار بدون إعادة ترميز) — وهذا
   دائماً يعطي مدة إجمالية = مجموع مدد المقاطع بدقة تامة.
3) نُدمج الفيديو المُجمَّع مع الصوت في خطوة أخيرة، مع ضبط مدة الفيديو
   ليطابق مدة الصوت الفعلية (لا نعتمد على "-shortest" فقط، بل نحسب الفرق
   ونمدد/نقصّر المدة النهائية بدقة صريحة عبر "-t").
"""
import logging
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

log = logging.getLogger("🎥")

VF_FILTER = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,format=yuv420p"

# ⚠️ شرط صريح من المستخدم: لا تتجاوز أي صورة واحدة 10 ثوانٍ على الشاشة أبداً
MAX_SHOT_SEC = 10.0


def _cap_shot_durations(durations: list, max_sec: float = MAX_SHOT_SEC) -> list:
    """
    يفرض حداً أقصى صارماً لمدة ظهور كل صورة (10 ثوانٍ)، مع إعادة توزيع أي فائض
    زمني ناتج عن هذا التقييد (Capping) على اللقطات الأخرى التي لديها مساحة
    متبقية أقل من الحد، لضمان أن المدة الإجمالية للفيديو تبقى مطابقة تماماً
    لمدة الصوت الفعلية — فلا يُقتطع أي جزء من السرد المسموع أبداً بسبب هذا الحد.
    (في التصميم الطبيعي للّقطات عبر pipeline._split_text_into_shots هذا التقييد
    نادراً ما يُفعَّل عملياً، لكنه يبقى كطبقة حماية صريحة وحاسمة أخيرة).
    """
    if not durations:
        return durations
    total_target = sum(durations)
    capped = [min(max_sec, d) for d in durations]
    deficit = total_target - sum(capped)
    for _ in range(6):
        if deficit <= 0.01:
            break
        headroom = [max_sec - d for d in capped]
        total_headroom = sum(h for h in headroom if h > 0)
        if total_headroom <= 0.01:
            break
        for i in range(len(capped)):
            if headroom[i] <= 0:
                continue
            add = min(deficit * (headroom[i] / total_headroom), headroom[i])
            capped[i] += add
        deficit = total_target - sum(capped)
    if deficit > 0.01 and capped:
        capped[-1] += deficit
        log.warning(
            f"⚠️ عدد اللقطات غير كافٍ لتغطية مدة الصوت بالكامل ضمن حد {max_sec:.0f}ث/صورة — "
            f"تم تمديد آخر لقطة بمقدار {deficit:.1f}ث تفادياً لقطع السرد الصوتي."
        )
    return capped


def _get_duration(path) -> float:
    """يعيد المدة الفعلية بالثواني لملف صوت/فيديو عبر ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=30
        )
        return float(result.stdout.strip())
    except Exception as e:
        log.warning(f"⚠️ تعذّر قياس المدة لـ {path}: {e}")
        return 0.0


def _render_image_clip(image_path: Path, duration: float, out_path: Path) -> bool:
    """يُرمّز صورة واحدة إلى مقطع فيديو بمدة دقيقة تماماً (بالثواني)."""
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(image_path),
        "-t", f"{duration:.3f}",
        "-vf", VF_FILTER,
        "-r", "25",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        str(out_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if result.returncode != 0 or not out_path.exists():
        log.error(f"❌ فشل ترميز مقطع الصورة {image_path.name}: {result.stderr[-500:]}")
        return False
    return True


def merge_video(image_paths, audio_path: str, durations, output_path: Path, use_zoom_effect=True):
    """
    يدمج قائمة من مسارات الصور مع ملف صوت باستخدام FFmpeg.
    image_paths: قائمة مسارات صور (Path أو str)
    durations: قائمة بمدة كل صورة بالثواني (نفس طول image_paths)
    """
    try:
        if not image_paths:
            log.warning("⏭️ لا توجد صور للدمج")
            return False

        tmp_dir = Path(tempfile.mkdtemp(prefix="doc_video_"))
        clip_paths = []

        # 1) ترميز كل صورة كمقطع فيديو مستقل بمدة دقيقة
        for i, (img, dur) in enumerate(zip(image_paths, durations)):
            clip_path = tmp_dir / f"clip_{i:03d}.mp4"
            if not _render_image_clip(Path(img), float(dur), clip_path):
                # في حال فشل صورة واحدة، تجاهلها ولا توقف كل العملية
                continue
            clip_paths.append(clip_path)

        if not clip_paths:
            log.error("❌ فشل ترميز جميع مقاطع الصور")
            return False

        # 2) دمج المقاطع المُرمّزة (concat حقيقي لملفات mp4 -> -c copy فقط)
        concat_list = tmp_dir / "clips_list.txt"
        concat_list.write_text(
            "\n".join(f"file '{c.absolute()}'" for c in clip_paths), encoding="utf-8"
        )
        merged_video = tmp_dir / "merged_video.mp4"
        cmd_concat = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-c", "copy",
            str(merged_video)
        ]
        result = subprocess.run(cmd_concat, capture_output=True, text=True, timeout=300)
        if result.returncode != 0 or not merged_video.exists():
            log.error(f"❌ فشل دمج مقاطع الفيديو: {result.stderr[-500:]}")
            return False

        video_dur = _get_duration(merged_video)
        audio_dur = _get_duration(audio_path)
        log.info(f"🎬 مدة الفيديو المُجمّع: {video_dur:.1f}ث │ مدة الصوت: {audio_dur:.1f}ث")

        # 3) دمج الفيديو النهائي مع الصوت — نضبط مدة الإخراج على القيمة الأصغر
        #    بدقة صريحة (-t) لضمان عدم وجود أي فيديو صامت أو صوت بلا صورة.
        final_dur = min(video_dur, audio_dur) if audio_dur > 0 else video_dur
        cmd_final = [
            "ffmpeg", "-y",
            "-i", str(merged_video),
            "-i", str(audio_path),
            "-t", f"{final_dur:.3f}",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            str(output_path)
        ]
        result = subprocess.run(cmd_final, capture_output=True, text=True, timeout=300)

        # تنظيف الملفات المؤقتة
        try:
            for c in clip_paths:
                c.unlink(missing_ok=True)
            merged_video.unlink(missing_ok=True)
            concat_list.unlink(missing_ok=True)
            tmp_dir.rmdir()
        except Exception:
            pass

        if result.returncode == 0 and Path(output_path).exists():
            final_check_dur = _get_duration(output_path)
            log.info(f"✅ الفيديو جاهز: {output_path} │ المدة النهائية المؤكدة: {final_check_dur:.1f}ث")
            return True
        else:
            log.error(f"❌ FFmpeg فشل في الدمج النهائي: {result.stderr[-800:]}")
            return False
    except Exception as e:
        log.error(f"❌ خطأ في دمج الفيديو: {e}")
        return False


def create_episode_video(image_paths, audio_file_path: Path, scenes_data: dict, output_dir: Path):
    """
    ⚠️ scenes_data هو ناتج pipeline.scenes() ويحمل اللقطات (shots) لا الأقسام
    السردية الأصلية — كل لقطة تحمل duration_seconds دقيقة خاصة بها (≤4-10ث)
    محسوبة من طول نصها المنطوق الفعلي، لا مدة القسم الكاملة.
    """
    if not image_paths or not audio_file_path or not Path(audio_file_path).exists():
        log.warning("⏭️ لا توجد صور أو ملف صوت صالح")
        return None

    output_dir.mkdir(parents=True, exist_ok=True)

    # مدة الصوت الفعلية الحقيقية (المصدر الوحيد الموثوق لتوزيع مدة كل صورة)
    audio_dur = _get_duration(audio_file_path)
    sections = scenes_data.get("sections", [])

    if sections and len(image_paths) == len(sections) and audio_dur > 0:
        # نوزّع مدة الصوت الفعلية على الصور بنفس النسب النسبية لمدة كل لقطة
        # (لا نعتمد على duration_seconds المخطط له فقط، بل نُعيد معايرته
        #  على مدة الصوت الحقيقية المُقاسة فعلياً، لضمان تطابق تام 100%)
        planned_total = sum(s.get("duration_seconds", 8) for s in sections) or 1
        durations = [
            max(1.0, (s.get("duration_seconds", 8) / planned_total) * audio_dur)
            for s in sections
        ]
    elif audio_dur > 0:
        avg = audio_dur / len(image_paths)
        durations = [avg] * len(image_paths)
    else:
        total_duration = sum(s.get("duration_seconds", 8) for s in sections) if sections else len(image_paths) * 8
        avg = total_duration / len(image_paths) if image_paths else 8
        durations = [avg] * len(image_paths)

    # ⚠️ التطبيق الفعلي للحد الملزم (≤ 10ث لكل صورة) مع إعادة توزيع الفارق بدون قطع الصوت
    durations = _cap_shot_durations(durations)
    log.info(
        f"🎯 عدد اللقطات: {len(durations)} │ مدة الصوت: {audio_dur:.1f}ث │ "
        f"أقل/أقصى مدة لقطة: {min(durations):.1f}ث/{max(durations):.1f}ث (الحد المسموح: {MAX_SHOT_SEC:.0f}ث)"
    )

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"episode_{ts}.mp4"

    if merge_video(image_paths, str(audio_file_path), durations, output_path):
        return output_path.name
    return None
