# ═══════════════════════════════════════════════════════════════
# Documentary Genius — Backend Dockerfile
# صورة جاهزة لتشغيل الخادم الخلفي على أي استضافة تدعم Docker
# (Railway, Fly.io, Render, أو أي VPS عادي)
# ═══════════════════════════════════════════════════════════════
FROM python:3.12-slim

# ffmpeg مطلوب لتجميع الفيديو النهائي
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/output /app/db_data

ENV PORT=5000
ENV DB_PATH=/app/db_data/production.db
EXPOSE 5000

# ⚠️ مهم جداً: worker واحد فقط (--workers 1)
# التطبيق يخزّن مهام الإنتاج الجارية (JOBS) ورموز الدخول (TOKENS) في
# الذاكرة، لا في قاعدة بيانات مشتركة. لو شغّلت أكثر من worker process،
# كل عملية سيكون لها ذاكرة منفصلة، فيختفي job_id أو يُرفض رمز الدخول
# بشكل عشوائي حسب أي عملية استقبلت الطلب. للتوازي نستخدم threads بدل
# processes (مناسب هنا لأن العمل إما I/O شبكة أو FFmpeg subprocess،
# وكلاهما يحرّر الـ GIL أثناء الانتظار).
CMD ["sh", "-c", "gunicorn --workers 1 --threads 8 --timeout 300 --bind 0.0.0.0:${PORT} app:app"]
