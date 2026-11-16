FROM python:3.13-slim

WORKDIR /srv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Run as a non-root user
RUN useradd --create-home ledgerly && mkdir /data && chown ledgerly /data
USER ledgerly
ENV LEDGERLY_DATABASE_URL=sqlite:////data/ledgerly.db

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
