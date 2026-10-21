# init_env.ps1 — 仅初始化本地环境（venv + pip>=21.3 + editable 安装），不启动 workflow
# 本文件须以 UTF-8 BOM 保存，Windows PowerShell 5.1 才能正确解析中文。
# 推荐入口: .\init_env.cmd
#
# 注意: 不要把含 % / if 等的 Python 代码塞进 PowerShell 双引号 -c 字符串，
# 否则 PS 5.1 会当成自己的运算符/关键字解析。版本检查尽量用 PS 解析命令输出。
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
$MinPipMajor = 21
$MinPipMinor = 3
$Force = $false

function Show-Usage {
    @"
用法:
  .\init_env.cmd [--force]
  .\init_env.ps1 [--force]

作用:
  创建/修复 .venv，将 pip 升到 >= 21.3，再执行 pip install -e .
  不启动 workflow（启动请用 .\start.cmd 或 sddl start）

选项:
  --force   强制删除并重建虚拟环境
  -h, --help

环境变量:
  VENV_DIR      虚拟环境目录（默认 .venv）
  PYTHON_BIN    优先使用的 Python 命令
"@
}

function Die([string]$Message) {
    [Console]::Error.WriteLine("错误: $Message")
    exit 1
}

function Test-PythonCandidate($File, [string[]]$Prefix) {
    # 跳过 Windows 商店占位符（WindowsApps\...python*.exe），否则会弹商店页
    if ($File -match '(?i)\\WindowsApps\\') { return $false }
    try {
        $out = & $File @($Prefix + @("--version")) 2>&1 | Out-String
        if ($LASTEXITCODE -ne 0) { return $false }
        return ($out -match 'Python\s+3\.')
    } catch {
        return $false
    }
}

function Resolve-PythonCommand {
    # 同事机器常见：官方安装器提供 python / py；部分环境只有 python3。
    # Windows 优先 py -3，再 python / python3；并校验 --version，避开商店 stub。
    $candidates = New-Object System.Collections.Generic.List[object]
    if ($env:PYTHON_BIN) {
        $candidates.Add(@{ Name = $env:PYTHON_BIN; Prefix = @() }) | Out-Null
    }
    $candidates.Add(@{ Name = "py"; Prefix = @("-3") }) | Out-Null
    $candidates.Add(@{ Name = "python"; Prefix = @() }) | Out-Null
    $candidates.Add(@{ Name = "python3"; Prefix = @() }) | Out-Null

    foreach ($c in $candidates) {
        $cmd = Get-Command $c.Name -ErrorAction SilentlyContinue
        if (-not $cmd) { continue }
        $file = $cmd.Source
        if (-not (Test-PythonCandidate $file $c.Prefix)) { continue }
        return @{ File = $file; Prefix = $c.Prefix }
    }
    Die @"
未找到可用的 Python 3.10+（已试: py -3 / python / python3）。
请安装 https://www.python.org/downloads/ （勾选 Add python.exe to PATH），或设置环境变量 PYTHON_BIN 指向 python.exe 全路径。
"@
}

function Invoke-Python($Python, [string[]]$PyArgs) {
    & $Python.File @($Python.Prefix + $PyArgs)
    if ($LASTEXITCODE -ne 0) {
        throw "python 退出码 $LASTEXITCODE"
    }
}

function Get-PythonVersionPair($Python) {
    # 用 --version 输出解析，避免 python -c 里出现 % / if 被 PS 误解析
    $out = & $Python.File @($Python.Prefix + @("--version")) 2>&1 | Out-String
    if ($out -match 'Python\s+(\d+)\.(\d+)') {
        return @{ Major = [int]$Matches[1]; Minor = [int]$Matches[2]; Text = "$($Matches[1]).$($Matches[2])" }
    }
    Die "无法解析 Python 版本: $out"
}

function Test-VenvHealthy([string]$Dir) {
    $py = Join-Path $Dir "Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $py)) {
        $py = Join-Path $Dir "bin\python"
    }
    if (-not (Test-Path -LiteralPath $py)) { return $false }
    $activate = Join-Path $Dir "Scripts\Activate.ps1"
    if (-not (Test-Path -LiteralPath $activate)) {
        $activate = Join-Path $Dir "Scripts\activate.bat"
    }
    if (-not (Test-Path -LiteralPath $activate)) {
        $activate = Join-Path $Dir "bin\activate"
    }
    if (-not (Test-Path -LiteralPath $activate)) { return $false }
    & $py -m pip --version 2>$null | Out-Null
    return ($LASTEXITCODE -eq 0)
}

function Test-PipMeetsMin([string]$Py) {
    $out = & $Py -m pip --version 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) { return $false }
    # 例: pip 24.2 from ...
    if ($out -match 'pip\s+(\d+)\.(\d+)') {
        $maj = [int]$Matches[1]
        $min = [int]$Matches[2]
        if ($maj -gt $MinPipMajor) { return $true }
        if ($maj -eq $MinPipMajor -and $min -ge $MinPipMinor) { return $true }
        return $false
    }
    return $false
}

# ---------- parse args ----------
$tokens = @($args)
$i = 0
while ($i -lt $tokens.Count) {
    $a = [string]$tokens[$i]
    if ($a -in @("-h", "--help")) {
        Show-Usage
        exit 0
    } elseif ($a -eq "--force") {
        $Force = $true
        $i++
    } else {
        Die "未知参数: $a（见 --help）"
    }
}

# ---------- python / venv ----------
$Python = Resolve-PythonCommand
$ver = Get-PythonVersionPair $Python
if ($ver.Major -lt 3 -or ($ver.Major -eq 3 -and $ver.Minor -lt 10)) {
    Die "需要 Python 3.10+，当前: $($ver.Text)"
}
Write-Host "==> Python: $($Python.File) ($($ver.Text))"

if ($Force -and (Test-Path -LiteralPath $VenvDir)) {
    Write-Host "==> --force：删除虚拟环境 $VenvDir"
    Remove-Item -LiteralPath $VenvDir -Recurse -Force
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
    try {
        Invoke-Python $Python @("-m", "venv", $VenvDir)
    } catch {
        Die "创建虚拟环境失败: $VenvDir — $_"
    }
    if (-not (Test-VenvHealthy $VenvDir)) {
        Die "虚拟环境创建后仍不可用（缺少 activate/pip），请检查 Python 是否带 ensurepip（Windows 安装时勾选 pip）"
    }
}

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $VenvPython)) {
    $VenvPython = Join-Path $VenvDir "bin\python"
}
if (-not (Test-Path -LiteralPath $VenvPython)) {
    Die "虚拟环境不完整，未找到 python"
}

Write-Host "==> 升级 pip / setuptools / wheel（editable 安装需要 pip >= $MinPipMajor.$MinPipMinor）"
& $VenvPython -m pip install -U "pip>=$MinPipMajor.$MinPipMinor" setuptools wheel
if ($LASTEXITCODE -ne 0) {
    Die "升级 pip/setuptools/wheel 失败。可手动: `"$VenvPython`" -m pip install -U `"pip>=$MinPipMajor.$MinPipMinor`" setuptools wheel"
}
if (-not (Test-PipMeetsMin $VenvPython)) {
    Die "pip 仍低于 $MinPipMajor.$MinPipMinor"
}
$pipVer = & $VenvPython -m pip --version
Write-Host "    $pipVer"

Write-Host "==> 安装 ai4se-sdd-loop-workflow（editable: python -m pip install -e .）"
& $VenvPython -m pip install -e .
if ($LASTEXITCODE -ne 0) {
    $hint = @(
        "pip install -e . 失败。请把完整报错贴出。"
        "手动排查:"
        "  `"$VenvPython`" -m pip --version"
        "  `"$VenvPython`" -m pip install -U `"pip>=21.3`" setuptools wheel"
        "  `"$VenvPython`" -m pip install -e ."
        "常见原因: pip < 21.3、用了系统 pip 而不是 venv、路径含特殊字符、网络/代理。"
    ) -join [Environment]::NewLine
    Die $hint
}

Write-Host ""
Write-Host "==> 环境就绪"
$activatePs1 = Join-Path $VenvDir "Scripts\Activate.ps1"
$activateBat = Join-Path $VenvDir "Scripts\activate.bat"
if (Test-Path -LiteralPath $activatePs1) {
    Write-Host "    激活 (PowerShell): .\$VenvDir\Scripts\Activate.ps1"
}
if (Test-Path -LiteralPath $activateBat) {
    Write-Host "    激活 (cmd):        .\$VenvDir\Scripts\activate.bat"
}
Write-Host "    业务项目根执行: sddl init"
Write-Host "    启动 workflow:   sddl start ...  或  .\start.cmd ..."
