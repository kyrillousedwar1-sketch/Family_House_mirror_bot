FROM python:3.9-slim
RUN apt-get update && apt-get install -y ffmpeg libmagic1-dev gcc-multilib build-essential --no-install-recommends && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["bash", "start.sh"]
