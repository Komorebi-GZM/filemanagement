@echo off

rem 本地文件多标记交叉管理系统启动脚本

echo 启动本地文件多标记交叉管理系统...
echo ------------------------------------

rem 切换到项目根目录
cd /d "%~dp0"

rem 运行应用
echo 正在启动应用...
conda run -n py311-pack python -m src.main

rem 捕获退出码
if %errorlevel% neq 0 (
    echo 应用启动失败，错误码：%errorlevel%
    echo 请确保已创建并激活py311-pack环境，且安装了所需依赖
    echo 创建环境：conda create -n py311-pack python=3.11 -y
    echo 激活环境：conda activate py311-pack
    echo 安装依赖：pip install -r requirements.txt
    pause
    exit /b %errorlevel%
)
