# start.ps1 — 创建虚拟环境、安装依赖并启动 ai4se-sdd-loop-workflow（Windows）
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
  -n, --name NAME     需求目录名，产出落在 <应用根>/spec/<NAME>/（docs_dir 可配）
  -t, --tool TOOL     覆盖 AI 工具: cursor | claude_code | oh_my_pi | omp | echo
  -d, --docs-dir DIR  覆盖完整产出目录（相对应用根或绝对路径）
  --skip-clarification  跳过需求澄清 loop（echo 调试 / CI）
  --auto                无人值守：禁止向用户提问，内容就绪后自动过门禁
  --fresh               清除已有产出（保留 00-requirement.md）后重来
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
$SkipInstall = $false
$SkipClarification = $false
$AutoMode = $false
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
    } elseif ($a -eq "--skip-install") {
        $SkipInstall = $true
        $i++
    } elseif ($a -eq "--skip-clarification") {
        $SkipClarification = $true
        $i++
    } elseif ($a -eq "--auto") {
        $AutoMode = $true
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

function Test-VenvHealthy([string]$Dir) {
    $py = Join-Path $Dir "Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $py)) {
        $py = Join-Path $Dir "bin\python"
    }
    if (-not (Test-Path -LiteralPath $py)) { return $false }
    $activate = Join-Path $Dir "Scripts\Activate.ps1"
    if (-not (Test-Path -LiteralPath $activate)) {
        $activate = Join-Path $Dir "bin\activate"
    }
    if (-not (Test-Path -LiteralPath $activate)) { return $false }
    & $py -m pip --version 2>$null | Out-Null
    return ($LASTEXITCODE -eq 0)
}

if (Test-VenvHealthy $VenvDir) {
    Write-Host "==> 复用虚拟环境: $VenvDir"
} else {
    if (Test-Path -LiteralPath $VenvDir) {
        Write-Host "==> 虚拟环境不完整，重建: $VenvDir"
        Remove-Item -LiteralPath $VenvDir -Recurse -Force
    } else {
        Write-Host "==> 创建虚拟环境: $VenvDir"
    }
    Invoke-Python $Python @("-m", "venv", $VenvDir)
    if (-not (Test-VenvHealthy $VenvDir)) {
        Die "虚拟环境创建后仍不可用（缺少 activate/pip），请检查 Python 是否带 ensurepip"
    }
}

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $VenvPython)) {
    $VenvPython = Join-Path $VenvDir "bin\python"
}
if (-not (Test-Path -LiteralPath $VenvPython)) {
    Die "虚拟环境不完整，未找到 python"
}

if (-not $SkipInstall) {
    Write-Host "==> 升级 pip"
    & $VenvPython -m pip install --upgrade pip | Out-Null
    Write-Host "==> 安装 ai4se-sdd-loop-workflow（editable，含 langgraph 等依赖）"
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
if ($AutoMode) { [void]$RunArgs.Add("--auto") }
if ($Fresh) { [void]$RunArgs.Add("--fresh") }

Write-Host "==> 启动 workflow"
Write-Host ("    {0} run.py {1}" -f $VenvPython, ($RunArgs -join " "))
Write-Host ""

& $VenvPython run.py @RunArgs
exit $LASTEXITCODE
