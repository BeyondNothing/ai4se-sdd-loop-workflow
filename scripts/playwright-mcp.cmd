@echo off
setlocal EnableExtensions
REM 启动 Playwright MCP（stdio）。供 Cursor / Claude / Oh My Pi agent 调用。

set "MIN_NODE_MAJOR=18"
if not defined PLAYWRIGHT_MCP_PKG set "PLAYWRIGHT_MCP_PKG=@playwright/mcp@0.0.79"

where node >nul 2>&1
if errorlevel 1 goto try_nvm

for /f "delims=" %%v in ('node -p "process.versions.node.split('.')[0]" 2^>nul') do set "NODE_MAJOR=%%v"
if not defined NODE_MAJOR set "NODE_MAJOR=0"
if %NODE_MAJOR% GEQ %MIN_NODE_MAJOR% goto have_node

:try_nvm
where nvm >nul 2>&1
if errorlevel 1 (
    echo Playwright MCP 需要 Node %MIN_NODE_MAJOR%+，请安装 Node.js 或 nvm-windows 1>&2
    exit /b 1
)
call nvm use 20 >nul 2>&1
if errorlevel 1 call nvm use 18 >nul 2>&1
where node >nul 2>&1
if errorlevel 1 (
    echo Playwright MCP 需要 Node %MIN_NODE_MAJOR%+，请运行: nvm install 20 1>&2
    exit /b 1
)

:have_node
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" goto run_mcp
if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" goto run_mcp
if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" goto run_mcp

echo Playwright MCP: 未检测到系统 Chrome，安装 chrome-for-testing... 1>&2
call npx -y %PLAYWRIGHT_MCP_PKG% install-browser chrome-for-testing 1>&2
if errorlevel 1 call npx -y playwright install chrome 1>&2

:run_mcp
if "%~1"=="" (
    npx -y %PLAYWRIGHT_MCP_PKG% --browser chrome --timeout-navigation 60000 --timeout-action 60000
) else (
    npx -y %PLAYWRIGHT_MCP_PKG% %*
)
exit /b %ERRORLEVEL%
