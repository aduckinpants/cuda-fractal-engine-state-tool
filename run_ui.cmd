@echo off
setlocal

set "REPO_ROOT=%~dp0"
pushd "%REPO_ROOT%" >nul

set "PYTHONPATH=%REPO_ROOT%src;%PYTHONPATH%"
py -3.14 -m cuda_fractal_state_tool.app
set "EXIT_CODE=%ERRORLEVEL%"

popd >nul
exit /b %EXIT_CODE%