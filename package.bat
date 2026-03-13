@echo off

rem 文件管理系统打包脚本

echo 开始打包文件管理系统...
echo ------------------------------------

rem 切换到项目根目录
cd /d "%~dp0"

rem 激活mag_app环境并执行打包
echo 正在激活mag_app环境...
conda activate mag_app

if %errorlevel% neq 0 (
    echo 激活环境失败，请确保已创建mag_app环境
    pause
    exit /b 1
)

echo 正在执行打包操作...
pyinstaller filemanagement.spec

if %errorlevel% neq 0 (
    echo 打包失败，请检查错误信息
    pause
    exit /b 1
)

echo 打包完成！
echo 可执行文件已生成在 dist 目录中
pause
