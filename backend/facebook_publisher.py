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
"""
import requests

GRAPH_VERSION = "v19.0"
GRAPH_VIDEO_UPLOAD_URL = f"https://graph-video.facebook.com/{GRAPH_VERSION}/{{page_id}}/videos"
GRAPH_BASE_URL = f"https://graph.facebook.com/{GRAPH_VERSION}"

# مهلة سخية لرفع الفيديو (بالثواني) — الرفع قد يستغرق دقائق حسب حجم الملف وسرعة الشبكة.
UPLOAD_TIMEOUT = 600


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
