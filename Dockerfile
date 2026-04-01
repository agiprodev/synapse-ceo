# استخدام نسخة بايثون خفيفة وسريعة
FROM python:3.11-slim

# تحديد مسار العمل جوه الحاوية
WORKDIR /app

# تسطيب كل المكتبات اللي العقل بتاعنا بيحتاجها
RUN pip install --no-cache-dir fastapi uvicorn httpx docker google-genai pydantic

# نسخ ملفات الكود (main.py و orchestrator.py) للحاوية
COPY apps/api/ .

# تشغيل السيرفر
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
