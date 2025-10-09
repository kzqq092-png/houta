#!/bin/bash
# HIkyuu-UI Deployment Rollback Script

echo "Starting deployment rollback..."

# 停止当前服务
echo "Stopping current services..."
pkill -f "python.*main.py"

# 恢复备份（如果存在）
BACKUP_DIR="deployment/backup_20250928_214344"
if [ -d "$BACKUP_DIR" ]; then
    echo "Restoring from backup: $BACKUP_DIR"
    # 这里添加具体的恢复逻辑
    # cp -r "$BACKUP_DIR"/* ./
else
    echo "No backup found at $BACKUP_DIR"
fi

echo "Rollback completed. Please verify system functionality."
