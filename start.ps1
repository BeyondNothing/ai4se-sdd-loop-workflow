# start.ps1 — 创建虚拟环境、安装依赖并启动 workflow（Windows）
# 本文件须以 UTF-8 BOM 保存，Windows PowerShell 5.1 才能正确解析中文。
$ErrorActionPreference = "Stop"
try {
    $utf8 = New-Object System.Text.UTF8Encoding $false
    [Console]::InputEncoding = $utf8
    [Console]::OutputEncoding = $utf8
    $OutputEncoding = $utf8
    $PSDefaultParameterValues['*:Encoding'] = 'utf8'
} catch {
}
if (-not $env:PYTHONIOENCODING) { $env:PYTHONIOENCODING = 'utf-8' }
if (-not $env:PYTHONUTF8) { $env:PYTHONUTF8 = '1' }
try { chcp 65001 | Out-Null } catch { }

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$VenvDir = if ($env:VENV_DIR) { $env:VENV_DIR } else { ".venv" }
$MinNodeMajor = 18

function Show-Usage {
    @"
用法:
  .\start.cmd [选项] [需求描述]
  .\start.ps1 [选项] --file <需求文件>

选项:
  -f, --file PATH     从文件读取需求（推荐）
  -n, --name NAME     需求目录名，产出落在 <应用根>/docs/<NAME>/
  -t, --tool TOOL     覆盖 AI 工具: cursor | claude_code | oh_my_pi | omp | echo
  -d, --docs-dir DIR  覆盖完整产出目录（相对应用根或绝对路径）
  --skip-clarification  跳过需求澄清 loop（echo 调试 / CI）
  --fresh               清除已有产出（保留 00-requirement.md）后重来
  --skip-mcp-setup      跳过 Playwright MCP 自动配置
  --skip-install      跳过依赖安装（已装过时加速启动）
  -h, --help          显示帮助

示例:
  .\start.cmd --tool echo --skip-clarification --file ..\docs\requirements\jwt-login-requirement.md --name jwt-login
  .\start.cmd --name jwt-login --file ..\docs\requirements\jwt-login-requirement.md
  .\start.cmd --name jwt-login
  .\start.cmd --tool echo "实现用户登录功能，支持 JWT 认证"
"@
}

function Die([string]$Message) {
    [Console]::Error.WriteLine("错误: $Message")
    exit 1
}

function Get-NodeMajor {
    $node = Get-Command node -ErrorAction SilentlyContinue
    if (-not $node) { return 0 }
    try {
        $major = & node -p "process.versions.node.split('.')[0]" 2>$null
        return [int]("$major".Trim())
    } catch {
        return 0
    }
}

function Ensure-NodeForPlaywright([bool]$SkipMcpSetup) {
    if ($SkipMcpSetup) { return }

    $major = Get-NodeMajor
    if ($major -ge $MinNodeMajor) {
        Write-Host "==> Node: $(node -v)（满足 Playwright MCP 要求）"
        return
    }

    if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
        Write-Host "==> 未检测到 node，尝试通过 nvm-windows 切换..."
    } else {
        Write-Host "==> 当前 Node $(node -v)，Playwright MCP 需要 ${MinNodeMajor}+，尝试 nvm 切换..."
    }

    $nvm = Get-Command nvm -ErrorAction SilentlyContinue
    if (-not $nvm) {
        Die "Node 版本低于 ${MinNodeMajor} 且未找到 nvm-windows，请先安装 Node.js 18+ 或 nvm install 20"
    }

    foreach ($ver in @("20", "18")) {
        & nvm use $ver 2>$null | Out-Null
        $major = Get-NodeMajor
        if ($major -ge $MinNodeMajor) {
            Write-Host "==> 已切换 Node: $(node -v)（nvm use $ver）"
            return
        }
    }

    Die "无法切换到 Node ${MinNodeMajor}+，Playwright MCP 将无法连接。请运行: nvm install 20"
}

function Test-SystemChrome {
    $candidates = @(
        (Join-Path ${env:ProgramFiles} "Google\Chrome\Application\chrome.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Google\Chrome\Application\chrome.exe"),
        (Join-Path $env:LOCALAPPDATA "Google\Chrome\Application\chrome.exe")
    )
    foreach ($path in $candidates) {
        if ($path -and (Test-Path -LiteralPath $path)) { return $true }
    }
    return $false
}

function Ensure-PlaywrightBrowsers([bool]$SkipMcpSetup) {
    if ($SkipMcpSetup) { return }

    if (Test-SystemChrome) {
        Write-Host "==> Playwright MCP: 使用系统 Google Chrome"
        return
    }

    Write-Host "==> 安装 Playwright MCP 浏览器（无系统 Chrome 时）..."
    $pkg = if ($env:PLAYWRIGHT_MCP_PKG) { $env:PLAYWRIGHT_MCP_PKG } else { "@playwright/mcp@0.0.79" }
    try {
        & npx -y $pkg install-browser chrome-for-testing
    } catch {
        try { & npx -y playwright install chrome } catch { }
    }
}

function Resolve-PythonCommand {
    $candidates = @()
    if ($env:PYTHON_BIN) { $candidates += $env:PYTHON_BIN }
    $candidates += @("python3", "python", "py")

    foreach ($name in $candidates) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if (-not $cmd) { continue }
        if ($name -eq "py") {
            return @{ File = $cmd.Source; Prefix = @("-3") }
        }
        return @{ File = $cmd.Source; Prefix = @() }
    }
    Die "未找到 python / python3 / py，请先安装 Python 3.10+"
}

function Invoke-Python($Python, [string[]]$PyArgs) {
    & $Python.File @($Python.Prefix + $PyArgs)
    if ($LASTEXITCODE -ne 0) {
        throw "python 退出码 $LASTEXITCODE"
    }
}

# ---------- parse args ----------
$SkipMcpSetup = $false
$SkipInstall = $false
$SkipClarification = $false
$Fresh = $false
$Tool = ""
$DocsDir = ""
$ReqName = ""
$ReqFile = ""
$ReqText = New-Object System.Collections.Generic.List[string]

$tokens = @($args)
$i = 0
while ($i -lt $tokens.Count) {
    $a = [string]$tokens[$i]
    if ($a -in @("-h", "--help")) {
        Show-Usage
        exit 0
    } elseif ($a -eq "--skip-mcp-setup") {
        $SkipMcpSetup = $true
        $i++
    } elseif ($a -eq "--skip-install") {
        $SkipInstall = $true
        $i++
    } elseif ($a -eq "--skip-clarification") {
        $SkipClarification = $true
        $i++
    } elseif ($a -eq "--fresh") {
        $Fresh = $true
        $i++
    } elseif ($a -in @("-t", "--tool")) {
        if ($i + 1 -ge $tokens.Count) { Die "--tool 需要参数" }
        $Tool = [string]$tokens[$i + 1]
        $i += 2
    } elseif ($a -in @("-n", "--name")) {
        if ($i + 1 -ge $tokens.Count) { Die "--name 需要参数" }
        $ReqName = [string]$tokens[$i + 1]
        $i += 2
    } elseif ($a -in @("-d", "--docs-dir")) {
        if ($i + 1 -ge $tokens.Count) { Die "--docs-dir 需要参数" }
        $DocsDir = [string]$tokens[$i + 1]
        $i += 2
    } elseif ($a -in @("-f", "--file")) {
        if ($i + 1 -ge $tokens.Count) { Die "--file 需要参数" }
        $ReqFile = [string]$tokens[$i + 1]
        $i += 2
    } elseif ($a -eq "--") {
        $i++
        while ($i -lt $tokens.Count) {
            [void]$ReqText.Add([string]$tokens[$i])
            $i++
        }
        break
    } elseif ($a.StartsWith("-")) {
        Die "未知选项: $a（用 --help 查看用法）"
    } else {
        [void]$ReqText.Add($a)
        $i++
    }
}

if (-not $ReqFile -and $ReqText.Count -eq 1) {
    $single = $ReqText[0]
    if ($single -like "*.md" -and (Test-Path -LiteralPath $single)) {
        $ReqFile = $single
        $ReqText.Clear()
    }
}

# ---------- python / venv ----------
$Python = Resolve-PythonCommand
$pyVersion = & $Python.File @($Python.Prefix + @("-c", "import sys; print('%d.%d' % sys.version_info[:2])"))
Write-Host "==> Python: $($Python.File) ($pyVersion)"

if (-not (Test-Path -LiteralPath $VenvDir)) {
    Write-Host "==> 创建虚拟环境: $VenvDir"
    Invoke-Python $Python @("-m", "venv", $VenvDir)
} else {
    Write-Host "==> 复用虚拟环境: $VenvDir"
}

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $VenvPython)) {
    Die "虚拟环境不完整，未找到 $VenvPython"
}

if (-not $SkipInstall) {
    Write-Host "==> 升级 pip"
    & $VenvPython -m pip install --upgrade pip | Out-Null
    Write-Host "==> 安装 dev-workflow（editable，含 langgraph 等依赖）"
    & $VenvPython -m pip install -e .
    if ($LASTEXITCODE -ne 0) { Die "pip install -e . 失败" }
} else {
    Write-Host "==> 跳过依赖安装 (--skip-install)"
}

# ---------- default requirement ----------
if (-not $ReqFile -and $ReqText.Count -eq 0) {
    $defaultReq = "..\docs\requirements\jwt-login-requirement.md"
    if (Test-Path -LiteralPath $defaultReq) {
        Write-Host "==> 未传需求，使用默认: $defaultReq"
        $ReqFile = $defaultReq
    } else {
        Die "请提供需求文本或 --file；也可用 --help 查看示例"
    }
}

# ---------- build run.py args ----------
$RunArgs = New-Object System.Collections.Generic.List[string]
if ($ReqFile) {
    if (-not (Test-Path -LiteralPath $ReqFile)) { Die "需求文件不存在: $ReqFile" }
    [void]$RunArgs.Add("--file")
    [void]$RunArgs.Add($ReqFile)
} elseif ($ReqText.Count -gt 0) {
    [void]$RunArgs.Add(($ReqText -join " "))
}
if ($Tool) { [void]$RunArgs.Add("--tool"); [void]$RunArgs.Add($Tool) }
if ($ReqName) { [void]$RunArgs.Add("--name"); [void]$RunArgs.Add($ReqName) }
if ($DocsDir) { [void]$RunArgs.Add("--docs-dir"); [void]$RunArgs.Add($DocsDir) }
if ($SkipClarification) { [void]$RunArgs.Add("--skip-clarification") }
if ($Fresh) { [void]$RunArgs.Add("--fresh") }
if ($SkipMcpSetup) { [void]$RunArgs.Add("--skip-mcp-setup") }

Ensure-NodeForPlaywright $SkipMcpSetup
Ensure-PlaywrightBrowsers $SkipMcpSetup

Write-Host "==> 启动 workflow"
Write-Host ("    {0} run.py {1}" -f $VenvPython, ($RunArgs -join " "))
Write-Host ""

& $VenvPython run.py @RunArgs
exit $LASTEXITCODE
