@echo off
:: 切换到项目根目录
cd /d "C:\Users\17051\opencode\project"

:: 记录运行日志
echo [%date% %time%] 开始执行每日复盘任务 >> logs\daily_review.log

:: 运行复盘脚本
:: 确保在系统环境变量中设置了 SMTP_PASSWORD
python tasks\daily_review.py >> logs\daily_review.log 2>&1

:: 检查运行结果并记录
if %errorlevel% equ 0 (
    echo [%date% %time%] 任务成功完成 >> logs\daily_review.log
) else (
    echo [%date% %time%] 任务执行异常，错误代码: %errorlevel% >> logs\daily_review.log
)

echo ---------------------------------------- >> logs\daily_review.log
