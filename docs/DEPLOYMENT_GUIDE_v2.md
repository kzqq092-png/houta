# FactorWeave-Quant v2.0 部署指南

## 概述

本指南详细介绍了FactorWeave-Quant v2.0的部署流程，包括环境准备、依赖安装、配置设置、系统启动和运维监控等各个环节。

## 系统要求

### 最低配置
- **操作系统**: Windows 10/11, macOS 10.15+, Ubuntu 18.04+
- **Python版本**: Python 3.8+
- **内存**: 4GB RAM
- **存储**: 10GB 可用磁盘空间
- **网络**: 稳定的互联网连接

### 推荐配置
- **操作系统**: Windows 11, macOS 12+, Ubuntu 20.04+
- **Python版本**: Python 3.9+
- **内存**: 16GB RAM
- **存储**: 100GB SSD
- **CPU**: 8核心以上
- **网络**: 100Mbps+ 带宽

### 生产环境配置
- **操作系统**: Ubuntu 20.04 LTS Server
- **Python版本**: Python 3.9+
- **内存**: 32GB+ RAM
- **存储**: 500GB+ NVMe SSD
- **CPU**: 16核心以上
- **网络**: 1Gbps+ 带宽
- **数据库**: 独立数据库服务器

## 环境准备

### 1. Python环境设置

#### 使用Conda（推荐）
```bash
# 创建虚拟环境
conda create -n factorweave python=3.9
conda activate factorweave

# 安装基础依赖
conda install numpy pandas scipy scikit-learn
```

#### 使用venv
```bash
# 创建虚拟环境
python -m venv factorweave_env

# 激活环境
# Windows
factorweave_env\Scripts\activate
# Linux/macOS
source factorweave_env/bin/activate
```

### 2. 系统依赖安装

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install -y build-essential python3-dev python3-pip
sudo apt install -y libsqlite3-dev libssl-dev libffi-dev
sudo apt install -y qt5-default libqt5gui5 libqt5widgets5
```

#### CentOS/RHEL
```bash
sudo yum groupinstall -y "Development Tools"
sudo yum install -y python3-devel sqlite-devel openssl-devel libffi-devel
sudo yum install -y qt5-qtbase-devel qt5-qttools-devel
```

#### macOS
```bash
# 安装Homebrew（如果未安装）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装依赖
brew install python@3.9 sqlite openssl libffi
brew install qt5
```

#### Windows
```powershell
# 使用Chocolatey安装依赖
choco install python39 sqlite
choco install visualstudio2019buildtools
```

## 项目部署

### 1. 获取源代码

#### 从Git仓库克隆
```bash
git clone https://github.com/your-org/factorweave-quant.git
cd factorweave-quant
```

#### 从发布包安装
```bash
# 下载并解压发布包
wget https://releases.example.com/factorweave-quant-v2.0.tar.gz
tar -xzf factorweave-quant-v2.0.tar.gz
cd factorweave-quant-v2.0
```

### 2. 安装Python依赖

#### 使用pip安装
```bash
# 升级pip
pip install --upgrade pip

# 安装项目依赖
pip install -r requirements.txt

# 安装可选依赖（用于AI功能）
pip install -r requirements-ai.txt

# 安装开发依赖（仅开发环境）
pip install -r requirements-dev.txt
```

#### 使用Rye（推荐）
```bash
# 安装Rye
curl -sSf https://rye-up.com/get | bash

# 同步依赖
rye sync

# 激活虚拟环境
rye shell
```

### 3. 数据库初始化

#### 创建数据库目录
```bash
mkdir -p db
mkdir -p cache
mkdir -p logs
mkdir -p models
```

#### 初始化SQLite数据库
```bash
python scripts/init_database.py
```

#### 初始化DuckDB数据库
```bash
python scripts/init_duckdb.py
```

### 4. 配置文件设置

#### 复制配置模板
```bash
cp config/config.template.json config/config.json
cp config/database.template.json config/database.json
cp config/cache.template.json config/cache.json
```

#### 编辑主配置文件
```json
{
  "system": {
    "debug": false,
    "log_level": "INFO",
    "max_workers": 8,
    "enable_ai_features": true
  },
  "database": {
    "sqlite_path": "db/factorweave_system.sqlite",
    "duckdb_path": "db/factorweave_analytics.duckdb",
    "backup_enabled": true,
    "backup_interval": 3600
  },
  "cache": {
    "memory_limit_mb": 1024,
    "disk_limit_mb": 10240,
    "default_ttl": 3600
  },
  "performance": {
    "enable_monitoring": true,
    "enable_ai_prediction": true,
    "enable_distributed": false
  }
}
```

### 5. 环境变量设置

#### 创建环境变量文件
```bash
# 创建.env文件
cat > .env << EOF
# 应用配置
FACTORWEAVE_ENV=production
FACTORWEAVE_DEBUG=false
FACTORWEAVE_LOG_LEVEL=INFO

# 数据库配置
DATABASE_URL=sqlite:///db/factorweave_system.sqlite
DUCKDB_URL=db/factorweave_analytics.duckdb

# 缓存配置
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=3600

# AI服务配置
AI_MODEL_PATH=models/
ENABLE_AI_FEATURES=true

# 安全配置
SECRET_KEY=your-secret-key-here
ENCRYPTION_KEY=your-encryption-key-here

# 监控配置
ENABLE_MONITORING=true
METRICS_PORT=9090
EOF
```

#### 加载环境变量
```bash
# Linux/macOS
source .env

# Windows
# 手动设置环境变量或使用批处理文件
```

## 系统启动

### 1. 开发环境启动

#### 直接启动
```bash
python main.py
```

#### 使用调试模式
```bash
python main.py --debug --log-level DEBUG
```

### 2. 生产环境启动

#### 使用systemd（Linux）
```bash
# 创建systemd服务文件
sudo tee /etc/systemd/system/factorweave.service > /dev/null <<EOF
[Unit]
Description=FactorWeave-Quant Trading System
After=network.target

[Service]
Type=simple
User=factorweave
Group=factorweave
WorkingDirectory=/opt/factorweave-quant
Environment=PATH=/opt/factorweave-quant/venv/bin
ExecStart=/opt/factorweave-quant/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
sudo systemctl daemon-reload
sudo systemctl enable factorweave
sudo systemctl start factorweave
```

#### 使用Docker
```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    libsqlite3-dev \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建必要目录
RUN mkdir -p db cache logs models

# 设置环境变量
ENV FACTORWEAVE_ENV=production
ENV PYTHONPATH=/app

# 暴露端口
EXPOSE 8080

# 启动命令
CMD ["python", "main.py"]
```

```bash
# 构建Docker镜像
docker build -t factorweave-quant:v2.0 .

# 运行容器
docker run -d \
  --name factorweave \
  -p 8080:8080 \
  -v $(pwd)/data:/app/db \
  -v $(pwd)/logs:/app/logs \
  factorweave-quant:v2.0
```

#### 使用Docker Compose
```yaml
# docker-compose.yml
version: '3.8'

services:
  factorweave:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./data:/app/db
      - ./logs:/app/logs
      - ./cache:/app/cache
    environment:
      - FACTORWEAVE_ENV=production
      - DATABASE_URL=sqlite:///db/factorweave_system.sqlite
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - factorweave
    restart: unless-stopped

volumes:
  redis_data:
```

```bash
# 启动服务栈
docker-compose up -d

# 查看日志
docker-compose logs -f factorweave
```

## 配置优化

### 1. 性能优化配置

#### 内存配置
```json
{
  "memory": {
    "heap_size": "8G",
    "cache_size": "2G",
    "buffer_pool_size": "4G"
  }
}
```

#### 并发配置
```json
{
  "concurrency": {
    "max_workers": 16,
    "thread_pool_size": 32,
    "async_pool_size": 64
  }
}
```

#### 数据库优化
```json
{
  "database": {
    "sqlite": {
      "journal_mode": "WAL",
      "synchronous": "NORMAL",
      "cache_size": 10000,
      "temp_store": "MEMORY"
    },
    "duckdb": {
      "memory_limit": "8GB",
      "threads": 8,
      "max_memory": "16GB"
    }
  }
}
```

### 2. 安全配置

#### SSL/TLS配置
```json
{
  "security": {
    "ssl_enabled": true,
    "ssl_cert_path": "/etc/ssl/certs/factorweave.crt",
    "ssl_key_path": "/etc/ssl/private/factorweave.key",
    "ssl_protocols": ["TLSv1.2", "TLSv1.3"]
  }
}
```

#### 访问控制
```json
{
  "access_control": {
    "enable_authentication": true,
    "session_timeout": 3600,
    "max_login_attempts": 5,
    "ip_whitelist": ["192.168.1.0/24"]
  }
}
```

### 3. 监控配置

#### 日志配置
```json
{
  "logging": {
    "level": "INFO",
    "format": "json",
    "rotation": "1 day",
    "retention": "30 days",
    "compression": true
  }
}
```

#### 指标配置
```json
{
  "metrics": {
    "enabled": true,
    "port": 9090,
    "path": "/metrics",
    "interval": 30
  }
}
```

## 运维监控

### 1. 健康检查

#### 系统健康检查脚本
```bash
#!/bin/bash
# health_check.sh

# 检查进程状态
if ! pgrep -f "python main.py" > /dev/null; then
    echo "ERROR: FactorWeave process not running"
    exit 1
fi

# 检查端口监听
if ! netstat -ln | grep ":8080" > /dev/null; then
    echo "ERROR: Port 8080 not listening"
    exit 1
fi

# 检查数据库连接
python -c "
import sqlite3
try:
    conn = sqlite3.connect('db/factorweave_system.sqlite')
    conn.execute('SELECT 1')
    conn.close()
    print('OK: Database connection successful')
except Exception as e:
    print(f'ERROR: Database connection failed: {e}')
    exit(1)
"

echo "OK: All health checks passed"
```

#### HTTP健康检查端点
```python
# health_endpoint.py
from flask import Flask, jsonify
import sqlite3
import psutil

app = Flask(__name__)

@app.route('/health')
def health_check():
    try:
        # 检查数据库
        conn = sqlite3.connect('db/factorweave_system.sqlite')
        conn.execute('SELECT 1')
        conn.close()
        
        # 检查系统资源
        cpu_percent = psutil.cpu_percent()
        memory_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage('/').percent
        
        status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected',
            'resources': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'disk_percent': disk_percent
            }
        }
        
        # 检查资源使用率
        if cpu_percent > 90 or memory_percent > 90 or disk_percent > 90:
            status['status'] = 'warning'
            
        return jsonify(status)
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081)
```

### 2. 日志监控

#### 日志聚合配置（ELK Stack）
```yaml
# logstash.conf
input {
  file {
    path => "/opt/factorweave-quant/logs/*.log"
    start_position => "beginning"
    codec => json
  }
}

filter {
  if [level] == "ERROR" {
    mutate {
      add_tag => ["error"]
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "factorweave-%{+YYYY.MM.dd}"
  }
}
```

#### 日志告警规则
```yaml
# alertmanager.yml
groups:
- name: factorweave
  rules:
  - alert: HighErrorRate
    expr: rate(factorweave_errors_total[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High error rate detected"
      
  - alert: DatabaseConnectionFailed
    expr: factorweave_database_connection_status == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Database connection failed"
```

### 3. 性能监控

#### Prometheus配置
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'factorweave'
    static_configs:
      - targets: ['localhost:9090']
    scrape_interval: 30s
    metrics_path: /metrics
```

#### Grafana仪表板
```json
{
  "dashboard": {
    "title": "FactorWeave-Quant Monitoring",
    "panels": [
      {
        "title": "CPU Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(process_cpu_seconds_total[5m]) * 100"
          }
        ]
      },
      {
        "title": "Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "process_resident_memory_bytes / 1024 / 1024"
          }
        ]
      },
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(factorweave_requests_total[5m])"
          }
        ]
      }
    ]
  }
}
```

## 备份与恢复

### 1. 数据备份

#### 自动备份脚本
```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/opt/backups/factorweave"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="factorweave_backup_${DATE}.tar.gz"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 停止服务（可选）
# systemctl stop factorweave

# 备份数据库
sqlite3 db/factorweave_system.sqlite ".backup db/factorweave_system_backup.sqlite"

# 创建完整备份
tar -czf $BACKUP_DIR/$BACKUP_FILE \
    db/ \
    config/ \
    logs/ \
    models/

# 清理旧备份（保留30天）
find $BACKUP_DIR -name "factorweave_backup_*.tar.gz" -mtime +30 -delete

# 重启服务（如果之前停止了）
# systemctl start factorweave

echo "Backup completed: $BACKUP_DIR/$BACKUP_FILE"
```

#### 增量备份
```bash
#!/bin/bash
# incremental_backup.sh

BACKUP_DIR="/opt/backups/factorweave/incremental"
DATE=$(date +%Y%m%d_%H%M%S)
LAST_BACKUP_FILE="$BACKUP_DIR/.last_backup"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 获取上次备份时间
if [ -f $LAST_BACKUP_FILE ]; then
    LAST_BACKUP=$(cat $LAST_BACKUP_FILE)
else
    LAST_BACKUP="1970-01-01"
fi

# 查找修改的文件
find db/ config/ models/ -newer $LAST_BACKUP_FILE -type f > /tmp/changed_files.txt

if [ -s /tmp/changed_files.txt ]; then
    # 创建增量备份
    tar -czf $BACKUP_DIR/incremental_${DATE}.tar.gz -T /tmp/changed_files.txt
    echo $DATE > $LAST_BACKUP_FILE
    echo "Incremental backup completed: incremental_${DATE}.tar.gz"
else
    echo "No changes detected, skipping backup"
fi

rm -f /tmp/changed_files.txt
```

### 2. 数据恢复

#### 完整恢复脚本
```bash
#!/bin/bash
# restore.sh

if [ $# -ne 1 ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

BACKUP_FILE=$1

if [ ! -f $BACKUP_FILE ]; then
    echo "Backup file not found: $BACKUP_FILE"
    exit 1
fi

# 停止服务
systemctl stop factorweave

# 备份当前数据
mv db db_old_$(date +%Y%m%d_%H%M%S)
mv config config_old_$(date +%Y%m%d_%H%M%S)

# 恢复数据
tar -xzf $BACKUP_FILE

# 重启服务
systemctl start factorweave

echo "Restore completed from: $BACKUP_FILE"
```

## 故障排除

### 1. 常见问题

#### 启动失败
```bash
# 检查日志
tail -f logs/application.log

# 检查配置文件
python -c "import json; json.load(open('config/config.json'))"

# 检查依赖
pip check
```

#### 数据库连接问题
```bash
# 检查数据库文件权限
ls -la db/

# 测试数据库连接
python -c "
import sqlite3
conn = sqlite3.connect('db/factorweave_system.sqlite')
print('Database connection successful')
conn.close()
"
```

#### 性能问题
```bash
# 检查系统资源
htop
iostat -x 1
free -h

# 检查应用性能
python -m cProfile main.py
```

### 2. 调试工具

#### 日志分析工具
```bash
# 错误日志统计
grep "ERROR" logs/application.log | wc -l

# 性能慢查询
grep "slow" logs/performance.log | tail -10

# 内存使用分析
grep "memory" logs/application.log | tail -20
```

#### 性能分析工具
```python
# performance_profiler.py
import cProfile
import pstats
import io

def profile_application():
    pr = cProfile.Profile()
    pr.enable()
    
    # 运行应用代码
    import main
    main.run_application()
    
    pr.disable()
    
    # 分析结果
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats()
    
    with open('performance_profile.txt', 'w') as f:
        f.write(s.getvalue())

if __name__ == '__main__':
    profile_application()
```

## 升级指南

### 1. 版本升级流程

#### 准备升级
```bash
# 1. 备份当前版本
./scripts/backup.sh

# 2. 检查系统状态
./scripts/health_check.sh

# 3. 下载新版本
wget https://releases.example.com/factorweave-quant-v2.1.tar.gz
```

#### 执行升级
```bash
# 1. 停止服务
systemctl stop factorweave

# 2. 备份当前安装
mv /opt/factorweave-quant /opt/factorweave-quant-backup

# 3. 解压新版本
tar -xzf factorweave-quant-v2.1.tar.gz -C /opt/

# 4. 恢复配置和数据
cp -r /opt/factorweave-quant-backup/config/* /opt/factorweave-quant/config/
cp -r /opt/factorweave-quant-backup/db/* /opt/factorweave-quant/db/

# 5. 更新依赖
cd /opt/factorweave-quant
pip install -r requirements.txt

# 6. 运行数据库迁移
python scripts/migrate_database.py

# 7. 启动服务
systemctl start factorweave
```

#### 验证升级
```bash
# 检查服务状态
systemctl status factorweave

# 检查应用版本
python -c "from main import __version__; print(__version__)"

# 运行健康检查
./scripts/health_check.sh
```

### 2. 回滚流程

#### 快速回滚
```bash
# 1. 停止服务
systemctl stop factorweave

# 2. 恢复备份
rm -rf /opt/factorweave-quant
mv /opt/factorweave-quant-backup /opt/factorweave-quant

# 3. 启动服务
systemctl start factorweave
```

## 总结

本部署指南涵盖了FactorWeave-Quant v2.0的完整部署流程，从环境准备到生产运维的各个环节。通过遵循本指南，您可以成功部署和运维一个稳定、高性能的量化交易系统。

关键要点：
1. **环境准备**：确保系统满足最低要求，推荐使用虚拟环境
2. **配置管理**：合理配置系统参数，优化性能和安全性
3. **监控告警**：建立完善的监控体系，及时发现和处理问题
4. **备份恢复**：定期备份数据，制定灾难恢复计划
5. **持续运维**：定期更新系统，优化性能，确保系统稳定运行

如有任何问题或需要技术支持，请联系我们的技术团队。
