FROM python:3.11-slim

WORKDIR /app

COPY . /app

# 安装 Node.js
RUN apt-get update && \
    apt-get install -y curl gnupg && \
    curl -sL https://deb.nodesource.com/setup_20.x  | bash - && \
    apt-get install -y nodejs

# 设置时区
RUN apt-get update && \
    apt-get install -y tzdata && \
    ln -fs /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata

    RUN pip install --no-cache-dir -r requirements.txt

COPY config/config.example.ini /app/config.ini

CMD ["python", "main.py"]
