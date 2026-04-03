FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y curl wget && rm -rf /var/lib/apt/lists/*
RUN pip install fastapi uvicorn docker google-genai qdrant-client requests pydantic
COPY ./apps/api .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
