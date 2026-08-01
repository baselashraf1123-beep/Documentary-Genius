#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام إنتاج الوثائقيات الذكي — خط الأنابيب الرئيسي
Documentary Production Pipeline v4.0 — 100% مجاني بدون أي مفتاح API
قناة: أسرار ما وراء الأفق
"""
import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path

import ai_engine
import voice_engine
import image_engine
import video_engine
from database import db_insert_episode

log = logging.getLogger("🎬")

CHANNEL = "أسرار ما وراء الأفق"

STYLES = {
    "غامض_ومشوق": "غامض تصاعدي — يبني التشويق تدريجياً حتى الكشف الكبير",
    "علمي_موثق": "أكاديمي رصين — يعتمد على الحقائق والأبحاث والأرقام الدقيقة",
    "تاريخي_درامي": "سردي درامي — يروي الأحداث كقصة ملحمية بشخصيات وصراع",
    "صادم_مفاجئ": "صدمة فورية — يفتح بمفاجأة قوية ويحافظ على وتيرة سريعة",
    "فلسفي_تأملي": "عميق تأملي — يطرح تساؤلات وجودية ويدعو للتفكير العميق",
}

# ══════════════════════════════════════════════
# معايرة سرعة النطق العربي (Edge-TTS) — تم قياسها فعلياً بالتجربة
# المعدل الحقيقي المقاس: ~9.7-10.9 حرف/ثانية → نستخدم قيمة متحفظة
# لضمان أن النص المكتوب يغطي المدة المطلوبة فعلياً دون نقص.
# ══════════════════════════════════════════════
CHARS_PER_SEC = 9.5

# ⚠️ الحد الأقصى المسموح لتجاوز طول القسم عن الهدف المحسوب من duration_min.
# ثبت عملياً (عبر جوبين اختباريين فعليين) أن النموذج قد يكتب نصاً يتراوح
# طوله بين 88% و190% من الهدف المطلوب رغم التوجيه الصريح بعدم الاختصار —
# وهذا يُضخّم مدة الحلقة النهائية كثيراً عن duration_min الذي طلبه المستخدم
# (مثال فعلي: طلب 2 دقيقة → نتج فيديو ~5 دقائق). هذا السقف يمنع الانفلات
# دون المساس بجودة السرد أو حذف تفاصيل أساسية من القسم.
MAX_SECTION_OVERSHOOT_RATIO = 1.25


class DocumentaryPipeline:
    # ⚠️ يُستخدم فقط في الطلبات التي تتطلب رداً بصيغة JSON (outline, scenes, seo, ideas)
    SYS_WRITER = "أنت كاتب وثائقي عربي محترف متخصص في الأسرار والتاريخ والعلوم. أجب دائماً بصيغة JSON صالحة فقط، بدون أي شرح أو نص إضافي قبل أو بعد الـ JSON."
    SYS_DIRECTOR = "أنت مخرج فني وثائقي محترف متخصص في التصوير السينمائي والذكاء الاصطناعي التوليدي (Veo3, Midjourney). أجب دائماً بصيغة JSON صالحة فقط."
    SYS_SEO = "أنت خبير YouTube SEO عربي محترف متخصص في تحسين محركات البحث للمحتوى الوثائقي العربي. أجب دائماً بصيغة JSON صالحة فقط."

    # ⚠️ حرِج: يُستخدم فقط لتوليد نص الأقسام المنطوقة (سرد حر). لا يجب أبداً أن
    # يذكر كلمة JSON — لأن ذلك كان يتسبب فعلياً (مؤكَّد بالاختبار المباشر على
    # عدة حلقات) بارتباك النموذج فيُرجع نصاً مغلَّفاً بصيغة {"script": "..."}
    # بدلاً من نص سردي خام، فيقرأه محرك TTS حرفياً بصوت عالٍ ويفسد الحلقة.
    SYS_NARRATOR = (
        "أنت راوي عربي محترف يروي قصصاً وثائقية شفهياً أمام الكاميرا، بصوته الطبيعي، "
        "تمام كما يفعل صانعو محتوى حقيقيون على يوتيوب. أنت لست كاتباً يكتب مقالاً، بل إنسان "
        "يتحدث مباشرة إلى المشاهد بعفوية وثقة، بلا أي حشو أو تكرار أو صياغة نمطية مكررة. "
        "⚠️ تتحدث بالعربية الفصحى المعاصرة السهلة فقط (فصحى الإعلام)، بدون أي كلمة عامية أو "
        "لهجة محلية إطلاقاً مهما كانت — كل جملة يجب أن تكون سليمة نحوياً بالفصحى، لكن بأسلوب "
        "منطوق طبيعي لا مكتوب رسمياً جافاً. "
        "تجنب دائماً البدء بعبارات مستهلكة مثل 'هل تعلم أن' أو 'تخيل أن' أو 'ما السر الذي' "
        "أو أي افتتاحية استُخدمت من قبل في الحلقة نفسها. اكتب فقط الكلام المنطوق ذاته، "
        "بدون أي تنسيق أو أقواس أو علامات JSON أو عناوين — نص عربي فصيح حر متصل فقط."
    )

    # علامات عامية/لهجات محلية شائعة يجب رصدها كطبقة تحقق فعلي (وليس افتراضاً)
    # بعد التوليد — إن ظهرت، يُعاد توليد القسم بتعليمات أشد صرامة.
    COLLOQUIAL_MARKERS = [
        "مش ", "اللي ", "عاوز", "عايز", "بيحصل", "ماحدش", "مافيش", "كمان ",
        "دلوقتي", "إحنا ", "احنا ", "بتاع", "ازاي", "إزاي", "علشان", "علي شان",
        "يعني كده", "خلاص", "كدا", "كده",
    ]

    @classmethod
    def _has_colloquial(cls, text: str) -> str | None:
        """يتحقق فعلياً (لا افتراضاً) من وجود أي علامة لهجة عامية في النص.
        يعيد أول علامة عثر عليها، أو None إذا كان النص فصيحاً بالكامل."""
        for marker in cls.COLLOQUIAL_MARKERS:
            if marker in text:
                return marker
        return None

    @staticmethod
    def _is_valid_arabic_narration(text: str) -> str | None:
        """
        ⚠️ طبقة تحقق حرِجة اكتُشفت ضرورتها فعلياً بالاختبار المباشر: أحد مزودي
        g4f المجانيين قد "ينجح" ظاهرياً (يرجع رداً غير فارغ بلا استثناء) لكن
        محتوى الرد يكون في الحقيقة صفحة خطأ/سبام لخدمة صينية (نص بالصينية عن
        حظر IP وحسابات WeChat وروابط تسجيل GPT مقرصن) لا علاقة له إطلاقاً
        بموضوع الحلقة — وهذا لا يُكتشف بفاحص العامية (لأن الصينية لا تطابق أي
        علامة عامية عربية) فيمر كـ"فصيح" خطأً! هذه الدالة تتحقق فعلياً أن
        غالبية الحروف الفعلية في النص عربية، وترفض أي نص تسيطر عليه حروف/رموز
        لغة أخرى (صينية، إنجليزية، روابط، إلخ) بنسبة كبيرة.
        تعيد وصف السبب إن كان النص غير صالح، أو None إذا كان عربياً فعلياً.
        """
        if not text or len(text.strip()) < 15:
            return "نص فارغ أو قصير جداً"
        arabic_count = len(re.findall(r"[\u0600-\u06FF]", text))
        cjk_count = len(re.findall(r"[\u4e00-\u9fff\u3040-\u30ff]", text))
        latin_count = len(re.findall(r"[a-zA-Z]", text))
        total_letters = arabic_count + cjk_count + latin_count
        if total_letters == 0:
            return "لا يحتوي أي حروف قابلة للتصنيف"
        arabic_ratio = arabic_count / total_letters
        if cjk_count > 5:
            return f"يحتوي محتوى بلغة شرق آسيوية غير متوقع ({cjk_count} حرف) — استجابة فاسدة من مزود AI"
        if arabic_ratio < 0.55:
            return f"نسبة الحروف العربية منخفضة جداً ({arabic_ratio*100:.0f}%) — قد يكون محتوى غير صالح/غير عربي"
        if "http://" in text or "https://" in text or "微信" in text or "@" in text:
            return "يحتوي روابط/محتوى دعائي غير متوقع في نص سردي — استجابة فاسدة من مزود AI"
        return None

    @staticmethod
    def _opening_too_similar(text: str, used_openings: list[str], threshold: float = 0.55) -> bool:
        """
        ⚠️ طبقة حماية فعلية ثانية ضد التكرار النمطي (اكتُشف بالاختبار الفعلي: النموذج
        كرر بنية "لكن الغريب أن ... لم تكن/يكن عشوائية/اً" بين قسمين غير متتاليين
        في نفس الحلقة، حتى مع منع الافتتاحيات الحرفية المتطابقة). تقارن أول جزء من
        النص الجديد بكل الافتتاحيات السابقة عبر تشابه نصي فعلي (لا فقط تطابق حرفي).
        """
        import difflib
        new_open = text.strip()[:70]
        for old_open in used_openings:
            ratio = difflib.SequenceMatcher(None, new_open, old_open[:70]).ratio()
            if ratio >= threshold:
                return True
        return False

    # ══════════════════════════════════════════════
    # حدود مدة "اللقطة" البصرية الواحدة (شرط صريح من المستخدم):
    # لا تتجاوز أي صورة 10 ثوانٍ على الشاشة، وتتناسب مع كمية الكلام
    # المصاحب لها فعلياً فقط، لا مدة القسم السردي الكامل.
    # ══════════════════════════════════════════════
    MAX_SHOT_SECONDS = 10.0
    MIN_SHOT_SECONDS = 4.0

    @classmethod
    def _split_text_into_shots(cls, text: str, max_sec: float = None, min_sec: float = None) -> list[str]:
        """
        يقسّم نص القسم السردي الكامل إلى "لقطات" (shots) قصيرة، بحيث لا تتجاوز
        مدة نطق أي لقطة واحدة max_sec ثانية (مقاسة تقديرياً بمعدل CHARS_PER_SEC
        نفسه المستخدم أصلاً لضبط طول السكريبت الصوتي). هذا يضمن أن كل صورة في
        الفيديو النهائي تظهر لمدة محدودة تتناسب مع كمية الكلام المصاحب لها
        فعلياً في تلك اللحظة بالذات، لا مدة القسم الكاملة (التي قد تصل لعشرات
        الثواني في الأقسام الطويلة).
        """
        max_sec = max_sec or cls.MAX_SHOT_SECONDS
        min_sec = min_sec or cls.MIN_SHOT_SECONDS
        max_chars = max_sec * CHARS_PER_SEC
        min_chars = min_sec * CHARS_PER_SEC

        text = (text or "").strip()
        if not text:
            return []

        sentences = re.split(r"(?<=[.!؟?])\s+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        # جملة واحدة أطول من الحد الأقصى بمفردها -> تُقسَّم قسراً عند حدود الكلمات
        # (ضمان صارم لعدم تجاوز أي لقطة الحد الأقصى مهما طالت الجملة الأصلية)
        normalized = []
        for s in sentences:
            if len(s) <= max_chars:
                normalized.append(s)
                continue
            words = s.split()
            chunk = ""
            for w in words:
                candidate = f"{chunk} {w}".strip()
                if len(candidate) > max_chars and chunk:
                    normalized.append(chunk)
                    chunk = w
                else:
                    chunk = candidate
            if chunk:
                normalized.append(chunk)

        shots = []
        current = ""
        for s in normalized:
            candidate = f"{current} {s}".strip()
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    shots.append(current)
                current = s
        if current:
            shots.append(current)

        # دمج أي لقطة أخيرة قصيرة جداً (أقل من الحد الأدنى) مع سابقتها لتجنّب
        # لقطات مفرطة القصر لا تحمل مضموناً بصرياً كافياً
        merged = []
        for s in shots:
            if merged and len(s) < min_chars and len(merged[-1]) + len(s) + 1 <= max_chars:
                merged[-1] = f"{merged[-1]} {s}".strip()
            else:
                merged.append(s)

        return merged if merged else [text]

    @staticmethod
    def _dedupe_shot_prompts(shots: list, threshold: float = 0.62) -> list:
        """
        ⚠️ طبقة حماية فعلية أخيرة ضد تكرار الصور بصرياً (شرط صريح من المستخدم:
        "لا يتم تكرار أي صورة فى الفيديو"): تفحص كل midjourney_prompt الناتج عبر
        الحلقة كاملة، وإن وجدت لقطتين متشابهتين جداً في الوصف (تشابه نصي فعلي
        عبر difflib ≥ threshold) تُضيف زاوية تصوير/تكوين مغايراً صريحاً للقطة
        الثانية لضمان اختلافها بصرياً فعلياً عند التوليد الحقيقي عبر Pollinations،
        حتى لو تشابه النص السردي المصاحب لها في الأصل.
        """
        # ⚠️ ملاحظة مهمة من الاختبار الفعلي: مقارنة difflib الخام للنص الكامل (بما في
        # ذلك اللاحقة التنسيقية الموحدة متل "ultra-realistic ... --ar 16:9") تُعطي تشابهاً
        # وهمياً مرتفعاً للقطتين مختلفتين تماماً في المحتوى (محقّق فعلياً: "dark street in
        # Berlin" مقابل "old documents on desk" أَعطتا نسبة تشابه مرتفعة زوراً بسبب
        # اللاحقة المشتركة). الحل المُطبق هنا: نقارن "الكلمات المحتوى الجوهرية"
        # فقط (بعد اسطناء كلمات الأسلوب/التنسيق المشتركة ورموز --ar/--v) عبر
        # تشابه Jaccard لمجموعات الكلمات — أدق وأقل عرضةً للإيجابيات المزيفة.
        style_stopwords = {
            "ultra-realistic", "ultrarealistic", "documentary", "photography", "photorealistic",
            "photojournalism", "style", "natural", "lighting", "cinematic", "real", "photo",
            "shot", "scene", "the", "a", "an", "of", "in", "on", "at", "with", "and", "dslr",
            "film", "grain", "35mm", "illustration", "painting", "drawing", "poster", "art",
            "text", "caption", "frame", "border", "watermark", "no",
        }

        def _core_words(p: str) -> set:
            p = re.sub(r"--\w+\s*\S+", "", p)
            words = re.findall(r"[a-zA-Z']+", p.lower())
            return {w for w in words if w not in style_stopwords and len(w) > 2}

        variants = [
            "wide establishing shot", "extreme close-up detail shot", "medium shot",
            "aerial drone view", "over-the-shoulder shot", "low-angle shot",
            "high-angle shot", "macro texture detail", "tracking shot", "point-of-view shot",
        ]
        seen_cores = []
        for i, sh in enumerate(shots):
            p = sh.get("midjourney_prompt", "")
            core = _core_words(p)
            is_dup = False
            for prev_core in seen_cores:
                if not core or not prev_core:
                    continue
                union = core | prev_core
                jaccard = len(core & prev_core) / len(union) if union else 0
                if jaccard >= threshold:
                    is_dup = True
                    break
            if is_dup:
                variant = variants[i % len(variants)]
                sh["midjourney_prompt"] = f"{p}, {variant}, distinct composition from other shots"
                sh["veo3_prompt"] = f"{sh.get('veo3_prompt', '')}, {variant}"
                log.info(f"   🔀 لقطة {sh.get('section_id')}: تشابه بصري محتوى مكتشف — أُضيفت زاوية '{variant}' لضمان صورة مختلفة")
            seen_cores.append(_core_words(sh.get("midjourney_prompt", p)))
        return shots

    def __init__(self, voice_key="أنتوني_رسمي", output_dir=None):
        self.voice_key = voice_key
        self.out = Path(output_dir) if output_dir else Path(__file__).parent / "output"
        self._ensure_dirs()
        log.info(f"🎬 قناة: {CHANNEL} │ محرك: g4f (مجاني) + Edge-TTS + Pollinations")

    def _ensure_dirs(self):
        for d in ["scripts", "audio", "scenes", "seo", "packages", "videos", "thumbnails", "images"]:
            (self.out / d).mkdir(parents=True, exist_ok=True)

    def _save_json(self, data, sub, prefix):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.out / sub / f"{prefix}_{ts}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    # ══════════════════════════════════════════════
    # 1) السكريبت
    # ══════════════════════════════════════════════
    # أسماء ونسب الأقسام الستة الثابتة (تُطبَّق نسبياً على أي مدة مطلوبة)
    SECTION_NAMES = ["المقدمة", "خلفية تاريخية", "السر الأول", "الدليل العلمي", "السر الأعمق", "الخاتمة"]
    SECTION_RATIOS = [0.08, 0.17, 0.20, 0.20, 0.20, 0.15]  # تجمع = 1.0

    def script(self, topic, duration=4, style="غامض_ومشوق"):
        """
        ⚠️ ملاحظة تقنية حرجة (تم اكتشافها واختبارها فعلياً):
        نماذج g4f المجانية (خصوصاً gpt-4o-mini) تتوقف عن الكتابة من نفسها
        (finish_reason=stop) عند طلب نص طويل جداً (آلاف الأحرف) في استدعاء
        واحد، بغض النظر عن max_tokens المسموح أو التعليمات الصريحة بالطول.
        الحل المُثبت بالاختبار: توليد كل قسم من الأقسام الستة بطلب AI
        منفصل بهدف حرفي صغير وقابل للتحقيق، مع إعادة محاولة تلقائية
        لكل قسم على حدة إذا قصر — هذا أسلوب أكثر موثوقية بكثير من
        طلب نص ضخم دفعة واحدة.
        """
        style_desc = STYLES.get(style, style)
        total_seconds = duration * 60
        names = self.SECTION_NAMES
        sec_durations = [max(15, round(total_seconds * r)) for r in self.SECTION_RATIOS]

        log.info(f"   🎯 الهدف: {duration} دقيقة = {total_seconds}ث │ توزيع الأقسام: {sec_durations}")

        # الخطوة 1: بيانات وصفية عامة (عنوان، مقدمة صادمة، حقائق) — طلب صغير وسريع
        outline = self._generate_outline(topic, style, style_desc)

        # الخطوة 2: توليد نص كل قسم بشكل منفصل مع تحقق فعلي من الطول وإعادة محاولة
        # نمرر آخر جملة من القسم السابق (للانسياب الطبيعي) وكل الافتتاحيات
        # السابقة (لمنع التكرار النمطي الروبوتي بين الأقسام).
        sections = []
        prev_ending = ""
        used_openings = []
        for i in range(6):
            target_chars_i = int(sec_durations[i] * CHARS_PER_SEC)
            text = self._generate_section_text(
                topic, style, style_desc, names[i], i + 1, sec_durations[i], target_chars_i,
                prev_ending=prev_ending, used_openings=used_openings,
            )
            sections.append({
                "id": i + 1,
                "name": names[i],
                "duration_seconds": sec_durations[i],
                "script": text,
                "tone": style,
                "key_visual": outline.get("key_visual_hint", topic),
            })
            prev_ending = text[-120:] if text else ""
            used_openings.append(text[:60])

        full_script = " ".join(s["script"] for s in sections)
        target_chars_total = int(total_seconds * CHARS_PER_SEC)
        total_len = len(full_script)
        log.info(f"   📏 الطول الإجمالي النهائي لـ full_script: {total_len} حرف "
                 f"(الهدف: {target_chars_total} حرف، النسبة: {total_len/target_chars_total*100:.0f}%)")

        data = {
            "title": outline.get("title") or f"أسرار {topic}",
            "subtitle": outline.get("subtitle", ""),
            "hook": outline.get("hook") or sections[0]["script"][:180],
            "sections": sections,
            "full_script": full_script,
            "key_facts": outline.get("key_facts", []),
            "closing_question": outline.get("closing_question", ""),
        }
        self._normalize_script(data)
        self._save_json(data, "scripts", "script")
        return data

    def _generate_outline(self, topic, style, style_desc):
        """طلب AI صغير وسريع لتوليد العنوان والحقائق الرئيسية فقط (بدون نص طويل)."""
        prompt = f"""أنت كاتب وثائقي عربي محترف. الموضوع: "{topic}". الأسلوب السردي: {style} — {style_desc}.

أعطني فقط البيانات الوصفية التالية لهذه الحلقة الوثائقية (بدون كتابة السكريبت الكامل):
أجب فقط بصيغة JSON صالحة تماماً بالشكل التالي بالضبط:
{{"title":"عنوان جذاب بحد أقصى 55 حرفاً",
"subtitle":"وصف فرعي بحد أقصى 80 حرفاً",
"hook":"جملة افتتاحية صادمة وقوية من 2-3 جمل",
"key_facts":["حقيقة1 بأرقام دقيقة","حقيقة2 بأرقام دقيقة","حقيقة3","حقيقة4"],
"closing_question":"سؤال ختامي تأملي للمشاهد",
"key_visual_hint":"وصف قصير بالإنجليزية للمشهد البصري العام المناسب لهذا الموضوع"}}"""
        try:
            data = ai_engine.complete(prompt, self.SYS_WRITER, max_tokens=1200, temperature=0.85)
            if isinstance(data, dict):
                return data
        except Exception as e:
            log.warning(f"   ⚠️ فشل توليد outline: {e} — استخدام قيم افتراضية")
        return {}

    # عبارات افتتاحية نمطية مستهلكة يجب تجنبها بشكل صريح (اكتُشفت فعلياً
    # عبر تحليل نصوص سابقة تكررت فيها هذه الصياغات الروبوتية أكثر من مرة،
    # بل تكررت حرفياً بين قسمين في الحلقة نفسها)
    # ⚠️ ملاحظة مؤكَّدة بالاختبار الفعلي: عند منع "هل تعلم/تخيل"، يهرب النموذج
    # تلقائياً إلى بديل نمطي آخر وهو "لكن الغريب أن... لم يكن/تكن عشوائياً/ة"
    # فتم رصده وحظره صريحاً هنا أيضاً.
    BANNED_OPENERS = [
        "هل تعلم أن", "تخيل أن", "تخيل أنك", "ما السر الذي أخفاه",
        "في هذا الجزء", "في هذا القسم", "لكن الغريب أن",
    ]

    @staticmethod
    def _strip_json_leak(text: str) -> str:
        """
        ⚠️ دفاع حرِج ضد عطل حقيقي مؤكَّد بالاختبار: النموذج قد يرتبك ويُرجع
        نص القسم مغلَّفاً بصيغة JSON خام مثل {"script": "..."} أو
        {"النص": "..."} بدلاً من نص سردي خام، فيقرأه محرك TTS حرفياً
        بصوت عالٍ (يتضمن أقواساً وعلامات تنصيص!) ويفسد الحلقة بالكامل.
        هذه الدالة تكتشف وتُزيل هذا التغليف إذا حدث، كطبقة حماية إضافية
        فوق تصحيح System Prompt نفسه (SYS_NARRATOR بدون أي ذكر لـ JSON).
        """
        if not text:
            return text
        t = text.strip()
        # الحالة: كل النص عبارة عن JSON object واحد يحتوي مفتاحاً نصياً واحداً
        if t.startswith("{") and t.endswith("}"):
            try:
                obj = json.loads(t)
                if isinstance(obj, dict) and obj:
                    # أول قيمة نصية طويلة في الـ dict هي النص الفعلي المقصود
                    for v in obj.values():
                        if isinstance(v, str) and len(v) > 20:
                            return v.strip()
            except Exception:
                pass
        # الحالة: تسرّب جزئي في البداية/النهاية مثل: {"script":" أو ٌ في النهاية "}
        t = re.sub(r'^\s*\{\s*["\']?\w+["\']?\s*:\s*["\']', "", t)
        t = re.sub(r'["\']\s*\}\s*$', "", t)
        return t.strip()

    @staticmethod
    def _truncate_to_target(text: str, target_chars: int, section_name: str = "",
                             max_ratio: float = MAX_SECTION_OVERSHOOT_RATIO) -> str:
        """
        شبكة أمان أخيرة: تقصّ النص عند حدود جملة كاملة إن تجاوز الحد الأقصى
        المسموح به من الهدف (max_ratio × target_chars)، بحيث لا تنفلت مدة
        الحلقة النهائية عن duration_min الذي طلبه المستخدم حتى لو تجاهل
        النموذج تعليمات الإيجاز الموجّهة له صريحاً في الـ prompt. يقصّ عند
        نهاية أقرب جملة كاملة (لا يقطع في وسط جملة) للحفاظ على تماسك السرد.
        """
        text = (text or "").strip()
        if not text or not target_chars:
            return text
        cap = int(target_chars * max_ratio)
        if len(text) <= cap:
            return text
        sentences = re.split(r"(?<=[.!؟?])\s+", text)
        sentences = [s.strip() for s in sentences if s.strip()]
        kept = ""
        for s in sentences:
            candidate = f"{kept} {s}".strip()
            if len(candidate) > cap and kept:
                break
            kept = candidate
        result = kept or text[:cap]
        log.warning(f"   ✂️ قسم '{section_name}': النص تجاوز الحد الأقصى المسموح "
                    f"({len(text)}/{cap} حرف) — تم قصّه عند حدود جملة كاملة إلى {len(result)} حرف")
        return result

    def _generate_section_text(self, topic, style, style_desc, section_name, section_num,
                                duration_seconds, target_chars, prev_ending="",
                                used_openings=None, max_attempts=4):
        """
        يولّد نص قسم واحد فقط، مع تحقق فعلي من الطول الحرفي الناتج ومقارنته
        بالهدف المحسوب من مدة القسم بالثواني. إذا كان النص قصيراً، يعيد
        المحاولة (حتى max_attempts مرات) مع تعليمات أوضح وأشد صرامة،
        ويحتفظ بأطول نسخة تم توليدها عبر كل المحاولات.

        كما يوجّه النموذج ليروي بأسلوب إنسان حقيقي عفوي (وليس روبوتياً)،
        ويمنع صراحةً تكرار نفس الافتتاحيات النمطية بين الأقسام، ويربط
        القسم الحالي بنهاية القسم السابق حتى يبدو حديثاً متصلاً طبيعياً
        كما يروي شخص عاش التجربة أو يحكيها بشكل مباشر، لا كمقال مكتوب.
        """
        used_openings = used_openings or []
        continuity_hint = (
            f'\nنهاية القسم السابق مباشرة كانت: "...{prev_ending}"\n'
            f"⚠️ اربط بداية هذا القسم بما سبق بشكل طبيعي وسلس، كأنك تستمر في نفس الحديث "
            f"مباشرة أمام الكاميرا، لا كأنك تبدأ موضوعاً جديداً منقطعاً."
        ) if prev_ending else ""
        # ⚠️ يجب تمرير كل الافتتاحيات السابقة في الحلقة كاملة (لا فقط آخر واحدة أو اثنتين)
        # لأن الاختبار الفعلي أثبت أن النموذج قد يكرر نمطاً استخدمه في قسم بعيد (مثل القسم
        # الثاني) عند الوصول لقسم لاحق (كالقسم الخامس) إن لم يُمنع صريحاً من كل التاريخ السابق.
        banned_hint = (
            "\n⚠️ ممنوع تماماً استخدام أي من هذه الافتتاحيات المستهلكة والمكررة، أو أي صياغة "
            "مشابهة لها في المعنى أو البنية حتى لو اختلفت الكلمات: "
            + "، ".join(f'"{o}..."' for o in (self.BANNED_OPENERS + used_openings))
            + ". ابدأ بطريقتك الخاصة، بجملة طبيعية وعفوية كأنك تتحدث فعلاً، لا كأنك تقرأ نصاً."
        )

        best_text = ""           # أطول نص تم توليده عبر كل المحاولات (احتياطي أخير)
        best_clean_text = ""     # أطول نص فصيح خالٍ من أي علامة عامية (الخيار المفضّل)
        success_text = None      # ⚠️ أول نص حقق النجاح الكامل (طول ضمن النطاق [0.85–1.25] + فصيح
                                  # + افتتاحية غير مكررة) — له الأولوية القصوى عند الإرجاع، لأن
                                  # "أطول نص فصيح" (best_clean_text) قد يكون نصاً تجاوز الحد الأقصى
                                  # في محاولة سابقة (overshoot) بينما محاولة لاحقة أنجح فعلياً ضمن
                                  # النطاق المطلوب بالضبط — يجب عدم استبدالها بنص تجاوزي أطول.
        last_fail_reason = ""    # "short" | "similar" | "colloquial" | "long" — لتخصيص رسالة إعادة المحاولة
        for attempt in range(1, max_attempts + 1):
            extra_push = ""
            if attempt > 1:
                if last_fail_reason == "short":
                    extra_push = (
                        f"\n⚠️ محاولتك السابقة كانت قصيرة جداً ({len(best_text)} حرف فقط من أصل "
                        f"{target_chars} مطلوب). هذه المرة اكتب نصاً أطول بوضوح، بإضافة تفاصيل "
                        f"وأمثلة وشرح أعمق لكل نقطة — لا تلخص ولا تختصر أبداً."
                    )
                elif last_fail_reason == "similar":
                    extra_push = (
                        "\n⚠️ محاولتك السابقة بدأت بنفس بنية افتتاحية استُخدمت من قبل في قسم "
                        "آخر من هذه الحلقة (حتى لو اختلفت بعض الكلمات). ابدأ هذه المرة بجملة "
                        "مختلفة تماماً في بنيتها وصياغتها عن أي شيء سبق."
                    )
                elif last_fail_reason == "invalid_lang":
                    extra_push = (
                        "\n⚠️ تنبيه حرِج: ردّك السابق لم يكن نصاً عربياً سردياً عن الموضوع إطلاقاً "
                        "(كان محتوى غير ذي صلة). اكتب هذه المرة نصاً عربياً فصيحاً خالصاً يتحدث فقط "
                        f"عن \"{section_name}\" ضمن موضوع \"{topic}\" — بدون أي روابط أو نصوص بلغات أخرى."
                    )
                elif last_fail_reason == "long":
                    extra_push = (
                        f"\n⚠️ محاولتك السابقة كانت أطول من المطلوب بكثير ({len(best_text)} حرف "
                        f"من أصل {target_chars} مطلوب فقط). هذه المرة اكتب بإيجاز أكبر وركّز على "
                        "أهم النقاط فقط دون حشو أو استطراد أو تفاصيل جانبية زائدة — لا تتجاوز "
                        f"{int(target_chars * MAX_SECTION_OVERSHOOT_RATIO)} حرفاً كحد أقصى مطلقاً."
                    )
                else:
                    extra_push = (
                        "\n⚠️ محاولتك السابقة تضمّنت كلمات عامية/لهجة محلية وهذا ممنوع تماماً. "
                        "أعد كتابة النص بالفصحى المعاصرة السليمة بالكامل، بدون أي كلمة عامية إطلاقاً."
                    )
            prompt = f"""اروِ (بصوتك، بالعربية الفصحى الواضحة والمشوقة) قسماً واحداً فقط من حلقة وثائقية عن: "{topic}"

هذا القسم هو: "{section_name}" (القسم رقم {section_num} من 6)
الأسلوب: {style} — {style_desc}
مدة هذا القسم عند النطق: {duration_seconds} ثانية بالضبط.
⚠️ لذلك يجب أن يكون طول الكلام حوالي {target_chars} حرفاً بالعربية بالضبط (± 10%) — لا تكتب أقصر من ذلك أبداً،
ولا تكتب أطول من {int(target_chars * MAX_SECTION_OVERSHOOT_RATIO)} حرفاً كحد أقصى مطلقاً (الإيجاز المركّز مطلوب،
وليس السرد المطوّل أو الاستطراد الجانبي) — الالتزام بالمدة الزمنية المطلوبة للحلقة كاملة أهم من إضافة تفاصيل زائدة.

🎙️ مهم جداً — أسلوب الرواية:
- تحدّث كإنسان حقيقي يروي الحدث مباشرة أمام الكاميرا، بعفوية وثقة، لا كمن يقرأ من ورقة.
- ⚠️ استخدم العربية الفصحى المعاصرة السهلة فقط (فصحى الإعلام والوثائقيات) — بدون أي عامية أو لهجة محلية إطلاقاً (ممنوع كلمات مثل: مش، اللي، عاوز، بيحصل، ماحدش، كمان، دلوقتي، إحنا). كل كلمة يجب أن تكون فصحى سليمة نحوياً، لكن بجُمل قصيرة وطبيعية كأنها منطوقة لا مكتوبة.
- استخدم جملاً طبيعية متوسطة الطول كما يتحدث الناس فعلاً، لا جملاً طويلة معقدة حشوية.
- اربط الأفكار بروابط حديث طبيعية بالفصحى متنوعة (وهنا بالضبط... / والمفاجأة أن... / لم يكن أحد يتوقع... / والأعجب من ذلك... / وما زاد الأمر خطورة... / في المقابل...) لا بروابط كتابية جافة، وبدون أي كلمة عامية. ⚠️ لا تستخدم نفس الرابط الذي استُخدم في أقسام سابقة من الحلقة، ونوّع دائماً حتى لا يتكرر أي أسلوب افتتاحي بين الأقسام.
- اذكر تفاصيل وأرقاماً وحقائق دقيقة فعلية دون حشو فارغ، ودون تلخيص أو اختصار.{continuity_hint}{banned_hint}{extra_push}

⚠️ أجب فقط بالكلام المنطوق ذاته، متصلاً، بدون أي عناوين أو تعداد نقطي أو علامات تنصيص محيطة أو أقواس JSON أو أي شرح إضافي قبله أو بعده — نص عربي حر خام فقط، كأنه سكريبت مقروء بصوت عالٍ."""
            try:
                text = ai_engine.complete_text(prompt, self.SYS_NARRATOR, max_tokens=2200, temperature=0.9)
                text = (text or "").strip()
                # إزالة أي علامات تنصيص محيطة أو مقدمات زائدة قد يضيفها النموذج
                text = text.strip('"“”\n ')
                # ⚠️ دفاع حرِج: إزالة أي تسرّب JSON خام (مؤكَّد الحدوث فعلياً في اختبارات سابقة)
                text = self._strip_json_leak(text)

                # ⚠️ أولوية قصوى: رفض أي استجابة "فاسدة" (سبام/لغة أخرى) قبل أي فحص آخر
                # أو حتى قبل اعتبارها احتياطاً أخيراً — استجابة كهذه لا يجوز أبداً أن
                # تنتهي في السكريبت النهائي بأي حال، حتى لو كانت "أطول نص متاح".
                invalid_lang_hit = self._is_valid_arabic_narration(text)
                if not invalid_lang_hit and len(text) > len(best_text):
                    best_text = text

                ratio = len(text) / target_chars if target_chars else 1.0
                colloquial_hit = None if invalid_lang_hit else self._has_colloquial(text)
                similar_hit = False if invalid_lang_hit else self._opening_too_similar(text, used_openings)
                if invalid_lang_hit:
                    status = "❌ محتوى فاسد/غير عربي!"
                elif colloquial_hit:
                    status = "⚠️ يحتوي عامية!"
                elif similar_hit:
                    status = "⚠️ افتتاحية مكررة!"
                else:
                    status = "✅ فصيح"
                log.info(f"   📝 قسم '{section_name}' — محاولة {attempt}: {len(text)} حرف "
                         f"(الهدف: {target_chars}, النسبة: {ratio*100:.0f}%) │ {status}"
                         + (f" ({invalid_lang_hit})" if invalid_lang_hit else "")
                         + (f" ('{colloquial_hit}')" if colloquial_hit else ""))

                if invalid_lang_hit:
                    last_fail_reason = "invalid_lang"
                    log.warning(f"   🚫 قسم '{section_name}': استجابة AI مرفوضة تماماً وسيُعاد المحاولة — {invalid_lang_hit}")
                    continue

                if not colloquial_hit and not similar_hit and len(text) > len(best_clean_text):
                    best_clean_text = text

                if colloquial_hit:
                    last_fail_reason = "colloquial"
                elif similar_hit:
                    last_fail_reason = "similar"
                elif ratio < 0.85:
                    last_fail_reason = "short"
                elif ratio > MAX_SECTION_OVERSHOOT_RATIO:
                    last_fail_reason = "long"

                # النجاح الكامل: طول ضمن النطاق المقبول (لا قصير جداً ولا طويل جداً)
                # + فصيح بالكامل + افتتاحية غير مكررة
                if 0.85 <= ratio <= MAX_SECTION_OVERSHOOT_RATIO and not colloquial_hit and not similar_hit:
                    success_text = text
                    break
            except Exception as e:
                log.warning(f"   ⚠️ فشل توليد قسم '{section_name}' (محاولة {attempt}): {e}")

        # ⚠️ أعلى أولوية مطلقة: محاولة نجحت بالكامل (طول ضمن النطاق + فصيح +
        # افتتاحية غير مكررة) — تُستخدم كما هي فوراً دون أي حاجة للقص، لأنها
        # بالتعريف ضمن الحد الأقصى المسموح أصلاً.
        if success_text:
            return success_text

        # الأولوية التالية: نص فصيح خالٍ من العامية وقريب من الطول المطلوب
        # ⚠️ شبكة أمان أخيرة في جميع مسارات الإرجاع: قصّ عند حدود جملة كاملة
        # إن تجاوز النص المُختار الحد الأقصى المسموح، لضمان التزام مدة الحلقة
        # النهائية بـ duration_min المطلوب بغض النظر عن سلوك النموذج.
        if best_clean_text and len(best_clean_text) >= target_chars * 0.6:
            return self._truncate_to_target(best_clean_text, target_chars, section_name)
        if best_clean_text:
            log.warning(f"   ⚠️ قسم '{section_name}': أفضل نص فصيح متاح قصير نسبياً "
                        f"({len(best_clean_text)}/{target_chars}) — يُستخدم كأولوية على النص الأطول المحتوي على عامية")
            return self._truncate_to_target(best_clean_text, target_chars, section_name)
        if best_text:
            log.warning(f"   ⚠️ قسم '{section_name}': لم يُعثر على نص فصيح خالٍ من العامية بالكامل "
                        f"بعد {max_attempts} محاولات — استخدام أطول نص متاح (قد يحتوي عامية)")
            return self._truncate_to_target(best_text, target_chars, section_name)
        return f"في هذا الجزء، نتحدث عن {topic}."

    @staticmethod
    def _normalize_script(data):
        """يضمن وجود جميع الحقول المطلوبة مع قيم افتراضية آمنة."""
        data.setdefault("title", "حلقة وثائقية")
        data.setdefault("subtitle", "")
        data.setdefault("hook", "")
        data.setdefault("sections", [])
        data.setdefault("key_facts", [])
        data.setdefault("closing_question", "")
        if not data.get("full_script"):
            data["full_script"] = " ".join(s.get("script", "") for s in data.get("sections", []))

    # ══════════════════════════════════════════════
    # 2) المشاهد البصرية
    # ══════════════════════════════════════════════
    def scenes(self, sc):
        """
        ⚠️ تصميم بصري على مستوى "اللقطة" لا "القسم" (شرط صريح من المستخدم):
        كل قسم سردي قد يمتد لعشرات الثواني يُقسَّم أولاً إلى لقطات قصيرة
        (≤ 10 ثوانٍ للقطة، محسوبة من طول النص المنطوق فيها فعلياً) عبر
        _split_text_into_shots، ثم يُطلب من المخرج AI برومبت بصري مستقل لكل
        لقطة على حدة يعرض بالضبط ما تصفه تلك اللقطة تحديداً (لا القسم كاملاً)
        لضمان أن كل صورة واقعية ومرتبطة منطقياً بمحتوى السرد الفعلي في تلك
        اللحظة بالذات، مع تنويع صريح لزاوية اللقطة بين اللقطات المتتالية،
        ثم فحص _dedupe_shot_prompts على مستوى الحلقة كاملة لضمان عدم تكرار
        أي صورة بصرياً في الفيديو النهائي.
        """
        all_shots = []
        for sec in sc.get("sections", []):
            sec_id = sec.get("id")
            sec_name = sec.get("name", "")
            sec_text = sec.get("script", "")
            chunks = self._split_text_into_shots(sec_text)
            if not chunks:
                continue

            numbered = "\n".join(
                f'[{j + 1}] (~{len(c) / CHARS_PER_SEC:.1f}ث): "{c}"' for j, c in enumerate(chunks)
            )
            prompt = f"""أنت مخرج فني وثائقي محترف. القسم: "{sec_name}" من حلقة بعنوان "{sc.get('title', '')}".
هذا القسم مُقسَّم إلى اللقطات المرقّمة التالية بالترتيب الزمني (كل لقطة = جزء من السرد الصوتي المصاحب لها فعلياً):
{numbered}

لكل لقطة مرقّمة أعلاه، صمّم توجيهاً بصرياً مستقلاً يعرض بالضبط ما يصفه نص تلك اللقطة تحديداً (لا وصفاً عاماً للقسم كله) — الصورة يجب أن تكون واقعية منطقياً ومطابقة تماماً لما يُقال في تلك اللحظة بالذات.
⚠️ نوّع زاوية اللقطة ونوعها بشكل صريح بين اللقطات المتتالية (wide establishing shot / close-up / medium shot / aerial view / over-the-shoulder / low-angle / macro detail) لضمان عدم تكرار أي تكوين بصري بين لقطتين.
⚠️ كل الصور يجب أن تكون فوتوغرافية واقعية تماماً (ultra-realistic documentary photography) — ممنوع أي رسم أو لوحة أو بوستر أو أي نص/عنوان داخل الصورة.

أجب فقط بصيغة JSON صالحة تماماً، بمصفوفة تحتوي على نفس عدد اللقطات أعلاه بالضبط وبنفس ترتيبها:
{{"shots":[
  {{"shot_index":1,
  "veo3_prompt":"Cinematic 4K documentary shot, ultra-realistic, detailed English prompt describing exactly this specific moment...",
  "midjourney_prompt":"ultra-realistic documentary photography, [specific scene matching the narration], photojournalism style, natural lighting --ar 16:9 --v 6",
  "shot_type":"نوع اللقطة بالعربية","lighting":"وصف الإضاءة بالعربية",
  "broll_ideas":["فكرة1","فكرة2"],
  "sfx":["صوت1","صوت2"],"music_mood":"وصف الجو الموسيقي","overlay_text":""}}
]}}"""
            # ⚠️ مرونة ضد انقطاعات g4f الكلية: بما أن التصميم الجديد يستدعي AI مرة
            # واحدة لكل قسم (بدل مرة واحدة للحلقة كاملة)، فالتعرض لفشل تام لجميع
            # النماذج أعلى بعدة أضعاف. عليه: نعيد المحاولة على مستوى القسم نفسه
            # (لا فقط داخل ai_engine.complete) بتأخير متصاعد، وإن فشلت كل المحاولات
            # لا نُسقط الحلقة كاملة (ونهدر السكريبت الجاهز)، بل نتراجع لبرومبتات
            # مبنية مباشرة من نص اللقطة الفعلي (لا تزال واقعية ومطابقة للمحتوى،
            # فقط بدون صياغة إخراجية إضافية من AI).
            data = {}
            for attempt, delay in enumerate((0, 12, 30), start=1):
                if delay:
                    log.warning(f"   ⏳ إعادة محاولة تصميم لقطات قسم '{sec_name}' بعد {delay}ث (محاولة {attempt})...")
                    time.sleep(delay)
                try:
                    data = ai_engine.complete(prompt, self.SYS_DIRECTOR, max_tokens=4000, temperature=0.75)
                    break
                except Exception as e:
                    log.warning(f"   ⚠️ فشل تصميم لقطات قسم '{sec_name}' (محاولة {attempt}): {str(e)[:200]}")
                    data = {}
            if not data:
                log.warning(f"   🔻 تعذّر الحصول على توجيه AI لقسم '{sec_name}' بعد كل المحاولات — سيتم استخدام برومبتات مبنية مباشرة من نص اللقطات (لا تزال واقعية ومطابقة للسرد الفعلي)")
            shot_results = data.get("shots", []) if isinstance(data, dict) else []

            for j, chunk_text in enumerate(chunks):
                shot_data = shot_results[j] if j < len(shot_results) else {}
                dur = max(self.MIN_SHOT_SECONDS, min(self.MAX_SHOT_SECONDS, len(chunk_text) / CHARS_PER_SEC))
                all_shots.append({
                    "section_id": f"{sec_id}.{j + 1}",
                    "parent_section_id": sec_id,
                    "parent_section_name": sec_name,
                    "shot_text": chunk_text,
                    "veo3_prompt": shot_data.get("veo3_prompt") or f"Cinematic 4K ultra-realistic documentary shot: {chunk_text[:150]}",
                    "midjourney_prompt": shot_data.get("midjourney_prompt") or f"ultra-realistic documentary photography, {chunk_text[:150]} --ar 16:9 --v 6",
                    "shot_type": shot_data.get("shot_type", ""),
                    "lighting": shot_data.get("lighting", ""),
                    "duration_seconds": round(dur, 2),
                    "broll_ideas": shot_data.get("broll_ideas", []),
                    "sfx": shot_data.get("sfx", []),
                    "music_mood": shot_data.get("music_mood", ""),
                    "overlay_text": shot_data.get("overlay_text", ""),
                })
            log.info(f"   🎬 قسم '{sec_name}': {len(chunks)} لقطة (≤{self.MAX_SHOT_SECONDS:.0f}ث لكل لقطة)")

        self._dedupe_shot_prompts(all_shots)

        data = {
            "color_grade": "توجيه لوني وثائقي متماسك عبر كل اللقطات",
            "music_theme": sc.get("subtitle", "") or sc.get("title", ""),
            "font_recommendation": "Cairo",
            "sections": all_shots,  # ⚠️ الاسم "sections" محفوظ للتوافق مع image_engine/video_engine
            "thumbnail_prompt": (
                f"Epic YouTube thumbnail, ultra-realistic 4K documentary photography, dramatic lighting, "
                f"{sc.get('title', '')}, photojournalism style, no text, no illustration"
            ),
        }
        self._save_json(data, "scenes", "scenes")
        log.info(
            f"   🎯 إجمالي اللقطات البصرية للحلقة كاملة: {len(all_shots)} لقطة "
            f"(بدلاً من {len(sc.get('sections', []))} صورة واحدة لكل قسم)"
        )
        return data

    # ══════════════════════════════════════════════
    # 3) حزمة SEO
    # ══════════════════════════════════════════════
    def seo(self, sc, topic):
        facts = "\n".join(f"• {f}" for f in sc.get("key_facts", []))
        prompt = f"""أنت خبير YouTube SEO عربي محترف. القناة: {CHANNEL}.
الموضوع: "{topic}". العنوان الحالي: "{sc.get('title', '')}".
الحقائق الرئيسية:
{facts}
السؤال الختامي: {sc.get('closing_question', '')}

أنشئ حزمة SEO كاملة ومحسّنة لهذه الحلقة. أجب فقط بصيغة JSON صالحة تماماً بالشكل التالي بالضبط:
{{"titles":["عنوان1 بحد أقصى 55 حرفاً","عنوان2","عنوان3"],
"description":"وصف يوتيوب بحوالي 300-400 كلمة، احترافي، يبدأ بـ hook قوي ويحتوي على كلمات مفتاحية وCTA في النهاية",
"tags":["وسم1","وسم2","...حتى 18 وسم"],
"hashtags":["#هاشتاغ1","#هاشتاغ2","...حتى 10 هاشتاقات"],
"thumbnail_text":"3-4 كلمات صادمة تظهر على الثمبنيل",
"thumbnail_style":"توجيه تصميم الثمبنيل بالعربية",
"chapters":[{{"time":"0:00","title":"المقدمة"}},{{"time":"0:30","title":"..."}}],
"primary_keywords":["كلمة1","كلمة2","كلمة3"],
"call_to_action":"جملة CTA قوية للمشاهدين",
"best_upload_day":"يوم الجمعة",
"best_upload_time":"8:00 مساءً بتوقيت القاهرة",
"community_post_text":"نص Community Post تشويقي قصير"}}"""
        # ⚠️ اكتُشف فعلياً بالاختبار المباشر: هذا الاستدعاء كان بلا أي حماية —
        # فشل تام لكل سلسلة نماذج g4f هنا كان يُسقط المهمة كاملة (بعد أن تجاوزت
        # فعلياً مرحلتي السكريبت وتصميم اللقطات بنجاح!) لأن run() لا يلتقط أي
        # استثناء حول seo(). نطبّق هنا نفس نمط المرونة المستخدم في scenes():
        # إعادة محاولة على مستوى الاستدعاء بتأخير متصاعد، وإن فشلت كل المحاولات
        # نبني حزمة SEO احتياطية محلياً من بيانات السكريبت نفسه بدل إسقاط الحلقة
        # كاملة وإهدار كل العمل السابق (سكريبت + تصميم لقطات جاهزين).
        data = {}
        for attempt, delay in enumerate((0, 12, 30), start=1):
            if delay:
                log.warning(f"   ⏳ إعادة محاولة توليد SEO بعد {delay}ث (محاولة {attempt})...")
                time.sleep(delay)
            try:
                data = ai_engine.complete(prompt, self.SYS_SEO, max_tokens=3500, temperature=0.70)
                if isinstance(data, dict) and data:
                    break
            except Exception as e:
                log.warning(f"   ⚠️ فشل توليد SEO (محاولة {attempt}): {str(e)[:200]}")
                data = {}
        if not data:
            log.warning("   🔻 تعذّر توليد SEO عبر AI بعد كل المحاولات — سيتم بناء حزمة SEO احتياطية من بيانات السكريبت مباشرة")
            title = sc.get("title", topic)[:55]
            data = {
                "titles": [title, f"{title} 🔥", f"سر {topic}"[:55]],
                "description": (sc.get("hook", "") + "\n\n" + "\n".join(f"• {f}" for f in sc.get("key_facts", []))
                                 + f"\n\n{sc.get('closing_question', '')}\n\nتابعوا قناة {CHANNEL} لمزيد من أسرار التاريخ والحضارات."),
                "tags": [topic] + [w for w in topic.split() if len(w) > 2][:17],
                "hashtags": [f"#{w}" for w in topic.split() if len(w) > 2][:10],
                "thumbnail_text": title[:30],
                "thumbnail_style": sc.get("key_visual_hint", "مشهد وثائقي دراماتيكي"),
                "chapters": [{"time": "0:00", "title": "المقدمة"}],
                "primary_keywords": [w for w in topic.split() if len(w) > 2][:3],
                "call_to_action": "لا تنسوا الإعجاب والاشتراك بالقناة!",
                "best_upload_day": "يوم الجمعة",
                "best_upload_time": "8:00 مساءً بتوقيت القاهرة",
                "community_post_text": sc.get("hook", "")[:150],
            }
        self._save_json(data, "seo", "seo")
        return data

    # ══════════════════════════════════════════════
    # 4) مولّد أفكار الحلقات
    # ══════════════════════════════════════════════
    @staticmethod
    def idea_generator(count=9, topic_hint=""):
        hint = f"\nتلميح إضافي من المستخدم: {topic_hint}" if topic_hint else ""
        prompt = f"""أنت مستشار محتوى خبير لقناة وثائقية عربية اسمها "{CHANNEL}".
مجالات القناة: أسرار التاريخ، حضارات قديمة، مخطوطات نادرة، ظواهر علمية غامضة، اختفاء مدن، نبوءات، مواقع أثرية، فراعنة، حضارات ما قبل التاريخ، آثار غامضة، أساطير عالمية، كنوز مفقودة.{hint}

اقترح {count} أفكار حلقات مشوقة ونادرة وغير مكررة في المحتوى العربي. كل فكرة يجب أن تكون:
- حقيقية ومبنية على حقائق تاريخية أو علمية موثقة
- غير مستهلكة أو مكررة في المحتوى العربي الحالي
- قابلة للتصوير الوثائقي بصرياً
- تحتوي على حقيقة صادمة واحدة على الأقل بالأرقام

أجب فقط بصيغة JSON صالحة تماماً بالشكل التالي:
{{"ideas":[
  {{"id":1,"topic":"موضوع الحلقة الكامل","hook_fact":"الحقيقة الصادمة بأرقام دقيقة",
  "mystery_level":8,"estimated_audience":"وصف فئة المشاهدين المستهدفة","potential":"عالي",
  "keywords":["كلمة1","كلمة2","كلمة3"],"estimated_duration":"4-5 دقائق"}}
]}}"""
        data = ai_engine.complete(prompt, max_tokens=3000, temperature=0.92)
        ideas = data.get("ideas", [])
        return ideas

    # ══════════════════════════════════════════════
    # 5) الصوت
    # ══════════════════════════════════════════════
    def voiceover(self, text):
        return voice_engine.generate_voiceover(text, self.voice_key, self.out / "audio", label="full")

    # ══════════════════════════════════════════════
    # 6) الصور والفيديو
    # ══════════════════════════════════════════════
    def generate_images(self, scenes_data):
        return image_engine.generate_images_for_scenes(scenes_data, self.out / "images")

    def create_video(self, image_paths, audio_file, scenes_data):
        # ⚠️ نمرّر بيانات "اللقطات" (scenes_data من scenes()) لا السكريبت الأصلي —
        # لأن كل لقطة الآن تحمل duration_seconds دقيقة خاصة بها (≤10ث) محسوبة من
        # طول نصها الفعلي، بدل مدة القسم الكاملة (التي قد تصل لعشرات الثواني).
        audio_full = self.out / "audio" / audio_file
        return video_engine.create_episode_video(image_paths, audio_full, scenes_data, self.out / "videos")

    # ══════════════════════════════════════════════
    # التشغيل الكامل (End-to-End)
    # ══════════════════════════════════════════════
    def run(self, topic, duration=4, style="غامض_ومشوق", audio=True, generate_video=False, progress_cb=None):
        def _p(pct, msg):
            if progress_cb:
                try:
                    progress_cb(pct, msg)
                except Exception:
                    pass

        t0 = time.time()

        _p(5, "جاري كتابة السكريبت بالذكاء الاصطناعي المجاني...")
        sc = self.script(topic, duration, style)

        _p(30, "جاري تصميم المشاهد البصرية...")
        scn = self.scenes(sc)

        _p(50, "جاري إعداد حزمة SEO...")
        seo_data = self.seo(sc, topic)

        mp3 = None
        if audio:
            _p(65, "جاري توليد الصوت العربي (Edge-TTS)...")
            mp3 = self.voiceover(sc.get("full_script", ""))

        video_file = None
        image_paths = []
        thumbnail_file = None
        if generate_video and mp3:
            _p(80, "جاري توليد صور المشاهد (Pollinations)...")
            image_paths = self.generate_images(scn)
            if image_paths:
                _p(92, "جاري دمج الفيديو النهائي (FFmpeg)...")
                video_file = self.create_video(image_paths, mp3, scn)
            if scn.get("thumbnail_prompt"):
                thumb = image_engine.generate_thumbnail(scn["thumbnail_prompt"], self.out / "thumbnails")
                thumbnail_file = thumb

        elapsed = time.time() - t0
        _p(100, "اكتمل الإنتاج بنجاح!")

        pkg = {
            "channel": CHANNEL,
            "topic": topic,
            "duration_min": duration,
            "style": style,
            "voice": self.voice_key,
            "generated_at": datetime.now().isoformat(),
            "elapsed_sec": round(elapsed, 1),
            "script": sc,
            "scenes": scn,
            "seo": seo_data,
            "audio_file": mp3,
            "video_file": video_file,
            "thumbnail_file": thumbnail_file,
            "images": [Path(p).name for p in image_paths],
            "images_count": len(image_paths),
        }
        self._save_json(pkg, "packages", "production_package")
        ep_id = db_insert_episode(pkg)
        pkg["episode_id"] = ep_id
        return pkg
