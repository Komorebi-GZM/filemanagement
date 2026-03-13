@echo off

rem 本地文件多标记交叉管理系统启动脚本

echo 启动本地文件多标记交叉管理系统...
echo ------------------------------------

rem 检查是否存在conda环境
if not exist ".conda-env" (
    echo 错误：未找到conda环境 ".conda-env"
    echo 请先创建并配置conda环境
    pause
    exit /b 1
)

rem 切换到项目根目录
cd /d "%~dp0"

rem 运行应用
echo 正在启动应用...
conda run -p .\.conda-env python -m src.main

rem 捕获退出码
if %errorlevel% neq 0 (
    echo 应用启动失败，错误码：%errorlevel%
    pause
    exit /b %errorlevel%
)
