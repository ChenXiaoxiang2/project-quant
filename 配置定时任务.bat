@echo off
:: Windows 任务计划程序配置脚本
:: 功能: 定时执行每日量化工作流 (每天 09:35 开盘前)
:: 用法: 以管理员身份运行此脚本

setlocal enabledelayedexpansion

echo ========================================
echo   量化交易系统 - 定时任务配置
echo ========================================
echo.

:: 检查是否以管理员运行
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [错误] 请右键选择"以管理员身份运行"此脚本
    pause
    exit /b 1
)

:: 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%"

:: 设置环境变量
set PYTHONHOME=
set PATH=%PATH%;%USERPROFILE%\AppData\Local\Programs\Python\Python311;%USERPROFILE%\AppData\Local\Programs\Python\Python312

:: 查找 Python
where python >nul 2>&1
if %errorLevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python
    pause
    exit /b 1
)

:: 创建任务计划
echo [1/3] 创建每日定时任务 (每天 09:35)...
schtasks /create /tn "量化交易每日报告" ^
  /tr "\"%COMSPEC%\" /c cd /d \"%PROJECT_DIR%\" ^&^& python workflows\daily_workflow.py --dry-run" ^
  /sc daily /st 09:35 /f

if %errorLevel% neq 0 (
    echo [警告] 主任务创建失败，尝试备用方式...
    schtasks /create /tn "量化交易每日报告" /tr "python \"%PROJECT_DIR%workflows\daily_workflow.py\"" /sc daily /st 09:35 /f
)

echo.
echo [2/3] 创建盘中监控任务 (每天 14:55 收盘前)...
schtasks /create /tn "量化交易盘中监控" ^
  /tr "python \"%PROJECT_DIR%workflows\daily_workflow.py\"" ^
  /sc daily /st 14:55 /f

echo.
echo [3/3] 验证任务列表...
schtasks /query /tn "量化交易每日报告" >nul 2>&1
if %errorLevel% equ 0 (
    echo   每日报告任务: 已注册
) else (
    echo   每日报告任务: 未找到
)

schtasks /query /tn "量化交易盘中监控" >nul 2>&1
if %errorLevel% equ 0 (
    echo   盘中监控任务: 已注册
) else (
    echo   盘中监控任务: 未找到
)

echo.
echo ========================================
echo   配置完成!
echo ========================================
echo.
echo 任务说明:
echo   - 量化交易每日报告: 每天 09:35 执行（干跑模式，不发邮件）
echo   - 量化交易盘中监控: 每天 14:55 执行
echo.
echo 如需修改执行时间，运行: schtasks /change /tn "量化交易每日报告" /st [新时间]
echo 如需删除任务，运行: schtasks /delete /tn "量化交易每日报告" /f
echo.
pause
