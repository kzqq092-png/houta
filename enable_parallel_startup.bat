@echo off
echo 启用并行启动优化...
echo ENABLE_PARALLEL_STARTUP=true > config\startup_config.env
echo PARALLEL_WORKERS=4 >> config\startup_config.env
echo STARTUP_MODE=parallel >> config\startup_config.env
echo.
echo ✓ 并行启动已启用
echo.
echo 运行主程序: python main.py
pause
