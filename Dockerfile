FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home academy && mkdir /data && chown academy /data
COPY --chown=academy:academy app ./app
USER academy
ENV ACADEMY_DB=/data/academy.db
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
