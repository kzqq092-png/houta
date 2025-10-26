@echo off
chcp 65001 >nul
echo ====================================
echo 分布式节点功能回归测试
echo ====================================
echo.

echo [步骤1] 检查Python环境...
python --version
if errorlevel 1 (
    echo 错误: 未找到Python
    pause
    exit /b 1
)
echo.

echo [步骤2] 启动分布式节点...
echo 提示: 请在另一个终端窗口中运行以下命令:
echo    cd distributed_node
echo    python start_node.py
echo.
echo 按任意键继续（确保节点已启动）...
pause >nul
echo.

echo [步骤3] 运行回归测试...
python test_distributed_node_regression.py --host localhost --port 8900
echo.

echo [步骤4] 测试完成
pause

