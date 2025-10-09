@echo off
echo 禁用并行启动，使用顺序模式...
echo ENABLE_PARALLEL_STARTUP=false > config\startup_config.env
echo PARALLEL_WORKERS=4 >> config\startup_config.env
echo STARTUP_MODE=sequential >> config\startup_config.env
echo.
echo ✓ 已切换到顺序启动模式
echo.
echo 运行主程序: python main.py
pause
