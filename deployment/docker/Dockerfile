# FactorWeave-Quant Production Dockerfile
# 专业量化平台生产环境Docker镜像

FROM python:3.11-slim as base

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libffi-dev \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 创建非root用户
RUN groupadd -r hikyuu && useradd -r -g hikyuu hikyuu

# 安装Python依赖
COPY requirements.txt requirements-prod.txt ./
RUN pip install --no-cache-dir -r requirements-prod.txt

# 复制应用代码
COPY . .

# 设置权限
RUN chown -R hikyuu:hikyuu /app && \
    chmod +x /app/deployment/scripts/*.sh

# 创建必要的目录
RUN mkdir -p /app/data /app/logs /app/cache /app/backups && \
    chown -R hikyuu:hikyuu /app/data /app/logs /app/cache /app/backups

# 切换到非root用户
USER hikyuu

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health', timeout=5)"

# 暴露端口
EXPOSE 8080 9090

# 启动命令
CMD ["python", "-m", "deployment.scripts.start_production"]

# 多阶段构建 - 开发环境
FROM base as development

# 安装开发依赖
COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

# 开发环境启动命令
CMD ["python", "-m", "deployment.scripts.start_development"]

# 多阶段构建 - 测试环境
FROM base as testing

# 安装测试依赖
COPY requirements-test.txt ./
RUN pip install --no-cache-dir -r requirements-test.txt

# 运行测试
CMD ["python", "-m", "pytest", "tests/", "-v", "--cov=core", "--cov-report=html"]

# 生产环境镜像（默认）
FROM base as production

# 生产环境优化
ENV ENVIRONMENT=production \
    LOG_LEVEL=INFO \
    UI_DEBUG=false \
    CACHE_L1_MAX_SIZE=20000 \
    CACHE_L2_MAX_SIZE_MB=4096

# 启动脚本
COPY deployment/scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["production"]
