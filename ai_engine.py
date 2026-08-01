#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
طبقة الذكاء الاصطناعي المجانية بالكامل — بدون أي مفتاح API
تعتمد على مكتبة g4f (GPT4Free) التي توفر وصولاً مجانياً لعدة نماذج ذكاء اصطناعي
(GPT-4o-mini, GPT-4, Llama, وغيرها) عبر مزودين متعددين مع نظام تبديل تلقائي (fallback)
لضمان أعلى معدل نجاح ممكن.
"""
import json
import logging
import re
import time

from g4f.client import Client
import g4f.Provider as _Providers

log = logging.getLogger("🤖")

# ترتيب النماذج من الأسرع/الأكثر استقراراً إلى الأبطأ (تبديل تلقائي عند الفشل)
MODEL_CHAIN = [
    "gpt-4o-mini",
    "gpt-4",
    "gpt-4o",
    "llama-3.3-70b",
    "gpt-4o-mini",  # إعادة محاولة أخيرة
]

_client = Client()

# ⚠️ طبقة مرونة متقدمة إضافية (مُكتشفة فعلياً بفحص منهجي مباشر لكل مزودي g4f
# المتاحين — أكثر من 90 مزوداً — أثناء انقطاع تام متزامن لكل نماذج MODEL_CHAIN
# الخمسة أعلاه دفعة واحدة، بما فيها المسار الاحتياطي الداخلي "default" الذي
# اكتُشف أنه محدود بحصة صارمة 200 طلب/يوم). "OperaAria" تحديداً تم تأكيده حياً
# وفعلياً (نجح بردود عربية سليمة 100% وبصيغة JSON صحيحة على برومبتات إنتاج
# حقيقية) رغم أن كل شيء آخر كان معطلاً تماماً في نفس اللحظة. نستخدمه هنا
# كملاذ أخير صريح (مزوّد مباشر لا عبر اسم "model") بعد استنفاد MODEL_CHAIN
# كاملاً، بدل إسقاط الطلب فوراً — يمنحنا مساراً حياً فعلياً حتى في حالات
# الانقطاع الشامل المتزامن لكل النماذج المُدرجة في MODEL_CHAIN.
_FALLBACK_PROVIDERS = [
    ("OperaAria", getattr(_Providers, "OperaAria", None)),
]

# ⚠️ رصد فعلي مؤكَّد بالاختبار المباشر: بعض مزودي g4f المجانيين (عبر بروكسي WeWordle/
# llmproxy.org وغيره) قد "ينجحون" ظاهرياً (يرجعون رداً 200 غير فارغ بلا أي استثناء)
# لكن محتوى الرد الفعلي هو صفحة سبام/خطأ ثابتة لخدمة صينية (حظر IP، حسابات WeChat،
# روابط تسجيل GPT مقرصن) لا علاقة لها بالطلب الأصلي إطلاقاً. هذا لا يُكتشف بأي فحص
# JSON/فراغ عادي، فنرصده هنا صريحاً برموز/نطاقات مميزة لهذا النوع من الاستجابات
# الفاسدة، ونرفعه كخطأ فعلي لإجبار النظام على تبديل النموذج التالي في MODEL_CHAIN
# فوراً (أسرع بكثير من انتظار طبقات تحقق أعلى في pipeline.py).
_SPAM_MARKERS = (
    "aichatos8.com.cn", "binjie09.shop", "binjie.site", "chatavx.com",
    "apifox.com/apidoc", "触发防滥用检测", "您的ip已", "微信",
)


def _looks_like_spam_response(content: str) -> bool:
    if not content:
        return False
    if any(m in content for m in _SPAM_MARKERS):
        return True
    cjk = len(re.findall(r"[\u4e00-\u9fff]", content))
    return cjk > 20 and cjk > len(content) * 0.15


def _parse_json(raw: str):
    """يحاول استخراج JSON صالح من رد النص الحر للذكاء الاصطناعي."""
    t = raw.strip()
    # إزالة أي تفكير/reasoning قد يظهر قبل JSON
    try:
        return json.loads(t)
    except Exception:
        pass
    # كتلة ```json ... ```
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", t)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except Exception:
            pass
    # أكبر كتلة { ... } بالنص
    m2 = re.search(r"\{[\s\S]*\}", t)
    if m2:
        candidate = m2.group()
        try:
            return json.loads(candidate)
        except Exception:
            # محاولة تنظيف فواصل زائدة (trailing commas)
            cleaned = re.sub(r",\s*([\]}])", r"\1", candidate)
            try:
                return json.loads(cleaned)
            except Exception:
                pass
    raise ValueError("تعذّر تحليل رد الذكاء الاصطناعي إلى JSON صالح")


def complete(prompt: str, system: str = "", max_tokens: int = 4500,
             temperature: float = 0.85, json_mode: bool = True, retries_per_model: int = 2):
    """
    يستدعي نموذج ذكاء اصطناعي مجاني (بدون مفتاح) عبر g4f، مع تبديل تلقائي
    بين عدة نماذج حتى ينجح الطلب ويُرجع بيانات JSON صالحة (عند json_mode=True).
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    last_error = None
    for model in MODEL_CHAIN:
        for attempt in range(retries_per_model):
            try:
                t0 = time.time()
                resp = _client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    timeout=90,
                )
                content = resp.choices[0].message.content or ""
                elapsed = time.time() - t0
                if not content.strip():
                    raise ValueError("رد فارغ من النموذج")
                if _looks_like_spam_response(content):
                    raise ValueError("استجابة فاسدة/سبام مكتشفة من مزود الخدمة (لا علاقة لها بالطلب الأصلي)")
                if json_mode:
                    data = _parse_json(content)
                    log.info(f"   ✅ {model} نجح في {elapsed:.1f}ث")
                    return data
                log.info(f"   ✅ {model} نجح في {elapsed:.1f}ث")
                return content
            except Exception as e:
                last_error = e
                log.warning(f"   ⚠️ {model} (محاولة {attempt+1}) فشل: {str(e)[:150]}")
                time.sleep(1.2)
                continue

    # ⚠️ استُنفدت كل نماذج MODEL_CHAIN — نحاول مزودات احتياطية إضافية مباشرة
    # قبل الاستسلام كلياً (انظر تعليق _FALLBACK_PROVIDERS أعلاه لسبب وجودها).
    for name, provider_cls in _FALLBACK_PROVIDERS:
        if provider_cls is None:
            continue
        try:
            t0 = time.time()
            fb_client = Client(provider=provider_cls)
            resp = fb_client.chat.completions.create(
                model="",
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=60,
            )
            content = resp.choices[0].message.content or ""
            elapsed = time.time() - t0
            if not content.strip():
                raise ValueError("رد فارغ من المزود الاحتياطي")
            if _looks_like_spam_response(content):
                raise ValueError("استجابة فاسدة/سبام من المزود الاحتياطي")
            if json_mode:
                data = _parse_json(content)
                log.info(f"   ✅ مزود احتياطي {name} نجح في {elapsed:.1f}ث (بعد استنفاد MODEL_CHAIN)")
                return data
            log.info(f"   ✅ مزود احتياطي {name} نجح في {elapsed:.1f}ث (بعد استنفاد MODEL_CHAIN)")
            return content
        except Exception as e:
            last_error = e
            log.warning(f"   ⚠️ مزود احتياطي {name} فشل أيضاً: {str(e)[:150]}")
            continue

    raise RuntimeError(f"فشلت جميع نماذج الذكاء الاصطناعي المجانية: {last_error}")


def complete_text(prompt: str, system: str = "", max_tokens: int = 2000, temperature: float = 0.8):
    """نص حر بدون تحليل JSON — يُستخدم لردود قصيرة/حرة."""
    return complete(prompt, system, max_tokens, temperature, json_mode=False)
