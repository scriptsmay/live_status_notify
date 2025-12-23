# --- 第一阶段：只用来提取 Node.js 二进制文件 ---
FROM node:20-slim AS node_holder

# --- 第二阶段：python生产环境 ---
FROM python:3.11-slim

WORKDIR /app

# 1. 直接从 node 镜像中把 node 拷贝过来 (非常快，无需下载脚本)
COPY --from=node_holder /usr/local/bin/node /usr/local/bin/
COPY --from=node_holder /usr/local/lib/node_modules /usr/local/lib/node_modules
# 创建 npm 软链接
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm

# 2. 配置 APT 源
RUN if [ -f /etc/apt/sources.list ]; then \
        sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list && \
        sed -i 's/security.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list; \
    elif [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
        sed -i 's/security.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources; \
    fi

# 3. 安装系统依赖（合并了之前的多个 RUN，减少镜像层数）
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    ca-certificates \
    && ln -snf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo "Asia/Shanghai" > /etc/timezone \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 4. 配置 Python 环境
COPY . /app
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir distro && \
    pip install --no-cache-dir -r requirements.txt

CMD ["python", "main.py"]