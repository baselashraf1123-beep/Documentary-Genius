#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
وحدة النشر على صفحة فيسبوك — Facebook Graph API
نظام إنتاج الوثائقيات الذكي v4.1

تنشر ملف فيديو منتَج محلياً مباشرة على صفحة فيسبوك، باستخدام:
- معرّف الصفحة (Page ID)
- رمز وصول الصفحة (Page Access Token) طويل الأمد

لا تتطلب أي مكتبة خارجية غير `requests` (موجودة أصلاً ضمن المتطلبات).

كيفية الحصول على Page Access Token (يُشرح بالتفصيل في دليل النشر المرفق):
1. أنشئ تطبيق على developers.facebook.com (نوع Business).
2. من Graph API Explorer، اختر التطبيق، ثم اطلب صلاحيات:
   pages_show_list, pages_manage_posts, pages_read_engagement
3. ولّد User Access Token، ثم بدّله إلى Long-Lived Token.
4. من نقطة /me/accounts احصل على access_token الخاص بصفحتك تحديداً —
   هذا هو الذي يُستخدم هنا (وهو غير محدود الصلاحية طالما التطبيق نشِط).

ملاحظات تقنية تم التحقق منها (توثيق Meta الرسمي، أغسطس 2026):
- المضيف graph-video.facebook.com أصبح مهجوراً (deprecated) لرفع الفيديو؛
  المضيف الصحيح الحالي هو graph.facebook.com لكل الطلبات، بما فيها الرفع.
- إصداري v18.0 وv19.0 من الـ Graph API لم يعودا يعملان (يرجعان خطأ 400).
  نستخدم هنا إصداراً حديثاً مدعوماً.
- الرفع المباشر (source متعدد الأجزاء) يعمل للملفات حتى 1 غيغابايت تقريباً؛
  لملفات أكبر تتطلب Meta استخدام "Resumable Upload API" على دفعات — غير
  مطبَّق هنا لأن حلقات هذا النظام (فيديو قصير بدقة معتدلة) تقع عادة ضمن
  هذا الحد بمسافة كبيرة.
"""
import os

import requests

GRAPH_VERSION = "v26.0"
GRAPH_VIDEO_UPLOAD_URL = f"https://graph.facebook.com/{GRAPH_VERSION}/{{page_id}}/videos"
GRAPH_BASE_URL = f"https://graph.facebook.com/{GRAPH_VERSION}"

# مهلة سخية لرفع الفيديو (بالثواني) — الرفع قد يستغرق دقائق حسب حجم الملف وسرعة الشبكة.
UPLOAD_TIMEOUT = 600

# حد الرفع المباشر (غير المجزّأ) حسب توثيق فيسبوك — تحذير احترازي قبل المحاولة
# بدل فشل غامض من طرف فيسبوك لاحقاً.
NON_RESUMABLE_LIMIT_BYTES = 1 * 1024 * 1024 * 1024  # 1GB


class FacebookPublishError(Exception):
    """خطأ واضح بالعربية يلخّص سبب فشل النشر، مع الحفاظ على رسالة فيسبوك الأصلية إن وُجدت."""
    pass


def _extract_fb_error(resp):
    try:
        data = resp.json()
        err = data.get("error", {})
        msg = err.get("message") or str(data)
        code = err.get("code")
        sub = err.get("error_subcode")
        return f"{msg} (code={code}, subcode={sub})"
    except Exception:
        return resp.text[:500]


def verify_page_token(page_id: str, access_token: str) -> dict:
    """يتحقق من صلاحية الاعتماد قبل محاولة النشر، ويرجع بيانات أساسية عن الصفحة.
    يُستخدم من واجهة الإعدادات كزر 'اختبار الاتصال بفيسبوك'."""
    if not page_id or not access_token:
        raise FacebookPublishError("معرّف الصفحة أو رمز الوصول غير موجود.")
    try:
        resp = requests.get(
            f"{GRAPH_BASE_URL}/{page_id}",
            params={"fields": "id,name,fan_count", "access_token": access_token},
            timeout=20,
        )
    except requests.RequestException as e:
        raise FacebookPublishError(f"تعذّر الاتصال بفيسبوك: {e}")

    if resp.status_code != 200:
        raise FacebookPublishError(_extract_fb_error(resp))
    return resp.json()


def publish_video_to_page(video_path, page_id: str, access_token: str,
                           title: str = "", description: str = "") -> str:
    """يرفع ملف فيديو وينشره مباشرة على صفحة فيسبوك المحدَّدة.

    يرجع معرّف المنشور (post/video id) عند النجاح.
    يرفع FacebookPublishError برسالة عربية واضحة عند الفشل.
    """
    if not page_id or not access_token:
        raise FacebookPublishError(
            "لم يتم ضبط بيانات صفحة فيسبوك بعد. أضف معرّف الصفحة ورمز الوصول من الإعدادات أولاً."
        )

    video_path = str(video_path)
    if not os.path.exists(video_path):
        raise FacebookPublishError(f"ملف الفيديو غير موجود: {video_path}")

    size = os.path.getsize(video_path)
    if size > NON_RESUMABLE_LIMIT_BYTES:
        raise FacebookPublishError(
            f"حجم الفيديو ({size / (1024*1024):.0f} م.ب) أكبر من حد الرفع المباشر "
            f"(1 غ.ب تقريباً). هذا غير متوقّع لحلقات هذا النظام — راجع إعدادات الدقة/الترميز."
        )

    url = GRAPH_VIDEO_UPLOAD_URL.format(page_id=page_id)

    try:
        with open(video_path, "rb") as f:
            files = {"source": f}
            data = {
                "access_token": access_token,
                "title": title[:255] if title else "",
                "description": description or "",
            }
            resp = requests.post(url, data=data, files=files, timeout=UPLOAD_TIMEOUT)
    except FileNotFoundError:
        raise FacebookPublishError(f"ملف الفيديو غير موجود: {video_path}")
    except requests.RequestException as e:
        raise FacebookPublishError(f"تعذّر الاتصال بفيسبوك أثناء الرفع: {e}")

    if resp.status_code != 200:
        raise FacebookPublishError(_extract_fb_error(resp))

    result = resp.json()
    post_id = result.get("id")
    if not post_id:
        raise FacebookPublishError(f"استجابة غير متوقعة من فيسبوك: {result}")
    return post_id
