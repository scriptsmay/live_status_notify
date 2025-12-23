# --- 第一阶段：提取 Node.js ---
FROM node:20-slim AS node_holder

# --- 第二阶段：生产环境 ---
FROM python:3.11-slim

LABEL org.opencontainers.image.source https://github.com/scriptsmay/live_status_notify

WORKDIR /app

# 1. 拷贝 Node.js
COPY --from=node_holder /usr/local/bin/node /usr/local/bin/
COPY --from=node_holder /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm

# 2. 动态配置 APT 和 Pip 源
ARG USE_CHINA_MIRROR=false
RUN if [ "$USE_CHINA_MIRROR" = "true" ]; then \
        # 兼容 Debian 12 的新旧两种源格式
        [ -f /etc/apt/sources.list ] && sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list; \
        [ -f /etc/apt/sources.list.d/debian.sources ] && sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources; \
        # 配置 Pip 国内源
        pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple; \
    fi

# 3. 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    ca-certificates \
    && ln -snf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo "Asia/Shanghai" > /etc/timezone \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 4. 安装 Python 依赖
# 先拷贝 requirements.txt 可以利用 Docker 缓存层
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir distro && \
    pip install --no-cache-dir -r requirements.txt

# 最后拷贝代码
COPY . .

CMD ["python", "main.py"]