@echo off
chcp 65001 >nul
title 量化交易系统

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║     量化交易系统 v2.0  一键启动         ║
echo  ╚══════════════════════════════════════════╝
echo.

:: 启动后端 API 服务
echo [1/3] 启动后端服务 (FastAPI :8000)...
start "量化API服务" cmd /c "cd /d %~dp0project && python web/api_server.py"

:: 等待后端就绪
timeout /t 3 /nobreak >nul

:: 启动前端 Web 服务
echo [2/3] 启动前端界面 (Streamlit :8501)...
start "量化Web界面" cmd /c "cd /d %~dp0project && python -m streamlit run web/app.py --server.port 8501"

:: 等待前端就绪
timeout /t 5 /nobreak >nul

:: 打开浏览器
echo [3/3] 打开浏览器...
start http://localhost:8501

echo.
echo  ═══════════════════════════════════════════
echo  ✅ 启动完成！
echo  ═══════════════════════════════════════════
echo.
echo  服务地址:
echo    后端 API:  http://localhost:8000
echo    前端界面:  http://localhost:8501
echo.
echo  提示: 关闭此窗口不会停止服务
echo         按任意键打开浏览器...
pause >nul
