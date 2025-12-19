@echo off
REM Windows 11 TensorFlow GPU安装脚本
REM 自动检测GPU硬件并安装匹配的CUDA和TensorFlow GPU版本
REM 
REM 使用方法：
REM 1. 确保已安装NVIDIA驱动和CUDA Toolkit
REM 2. 运行此脚本进行GPU环境配置
REM 3. 脚本会自动检测GPU并安装对应的TensorFlow GPU版本

echo ========================================
echo Windows 11 TensorFlow GPU安装脚本
echo ========================================
echo.

REM 检查Python环境
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Python未安装或不在PATH中
    echo 请先安装Python 3.8-3.12版本
    pause
    exit /b 1
)

echo [信息] 检测到Python环境
python --version
echo.

REM 检查pip版本
pip --version >nul 2>&1
if errorlevel 1 (
    echo [错误] pip未安装或不可用
    pause
    exit /b 1
)

echo [信息] pip环境正常
pip --version
echo.

REM 升级pip
echo [步骤] 升级pip到最新版本...
python -m pip install --upgrade pip
echo.

REM 检查NVIDIA驱动
echo [检查] NVIDIA GPU驱动状态...
nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo [警告] 未检测到NVIDIA GPU驱动
    echo 请访问 https://www.nvidia.com/drivers 下载安装最新驱动
    echo.
) else (
    echo [成功] NVIDIA GPU驱动正常
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits
    echo.
)

REM 临时安装nvidia-ml-py3进行GPU检测
echo [检查] 安装GPU检测工具...
pip install nvidia-ml-py3 --quiet
echo.

REM 运行GPU检测脚本
echo [检测] 开始GPU硬件检测...
python "%~dp0..\scripts\verify_gpu_system.py"
echo.

REM 询问是否安装GPU版本
echo [选择] GPU环境配置选项：
echo 1. 自动安装TensorFlow GPU版本（推荐）
echo 2. 仅安装CPU版本（兼容性最好）
echo 3. 手动配置CUDA环境
echo.
set /p choice="请选择配置方案 (1-3): "

if "%choice%"=="1" goto install_gpu
if "%choice%"=="2" goto install_cpu
if "%choice%"=="3" goto manual_cuda
goto invalid_choice

:install_gpu
echo [安装] 开始安装TensorFlow GPU版本...
echo [警告] 此过程可能需要下载大量数据，请确保网络连接稳定
echo.

REM 安装TensorFlow GPU版本
pip install tensorflow-gpu==2.19.0 --quiet
if errorlevel 1 (
    echo [错误] TensorFlow GPU安装失败
    echo 建议手动安装：pip install tensorflow-gpu==2.19.0
    pause
    exit /b 1
)

echo [成功] TensorFlow GPU安装完成
goto test_gpu

:install_cpu
echo [安装] 安装TensorFlow CPU版本...
pip install tensorflow==2.19.0 --quiet
if errorlevel 1 (
    echo [错误] TensorFlow CPU安装失败
    pause
    exit /b 1
)
echo [成功] TensorFlow CPU版本安装完成
echo [提示] 如需GPU加速，请参考安装指南手动配置CUDA环境
goto finish

:manual_cuda
echo [信息] 手动CUDA配置指南：
echo.
echo 1. 下载CUDA Toolkit 12.1或12.3
echo    https://developer.nvidia.com/cuda-downloads
echo.
echo 2. 下载cuDNN 8.9或8.10
echo    https://developer.nvidia.com/cudnn
echo.
echo 3. 配置环境变量：
echo    CUDA_PATH=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1
echo    PATH=%CUDA_PATH%\bin;%PATH%
echo.
echo 4. 安装TensorFlow GPU版本：
echo    pip install tensorflow-gpu==2.19.0
echo.
echo 更多详情请参考安装文档
pause
goto finish

:test_gpu
echo [测试] 验证GPU安装...
python -c "import tensorflow as tf; print(f'TensorFlow版本: {tf.__version__}'); gpus = tf.config.list_physical_devices('GPU'); print(f'检测到GPU设备: {len(gpus)}个')"
echo.

:finish
echo [完成] 安装配置完成！
echo.
echo 建议下一步操作：
echo 1. 运行GPU验证脚本：python scripts/verify_gpu_system.py
echo 2. 启动应用：python main.py
echo 3. 查看日志输出确认GPU状态
echo.
pause
exit /b 0

:invalid_choice
echo [错误] 无效选择
pause
exit /b 1