# init_env.ps1 — 项目 venv + pip install -e .，并把 .venv\Scripts 写入用户 PATH（免每次 activate）
# 推荐入口: .\init_env.cmd
# 本文件须以 UTF-8 BOM 保存，供 Windows PowerShell 5.1 解析中文。
$ErrorActionPreference = "Stop"
try {
    $utf8 = New-Object System.Text.UTF8Encoding $false
    [Console]::InputEncoding = $utf8
    [Console]::OutputEncoding = $utf8
    $OutputEncoding = $utf8
} catch { }
if (-not $env:PYTHONIOENCODING) { $env:PYTHONIOENCODING = 'utf-8' }
if (-not $env:PYTHONUTF8) { $env:PYTHONUTF8 = '1' }
try { chcp 65001 | Out-Null } catch { }

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$VenvDir = if ($env:VENV_DIR) { $env:VENV_DIR } else { ".venv" }
$MinPipMajor = 21
$MinPipMinor = 3
$PyMinMinor = 10
$PyMaxMinor = 14
$Force = $false
$SkipPath = $false

function Show-Usage {
    @"
用法:
  .\init_env.cmd [--force] [--skip-path]
  .\init_env.ps1 [--force] [--skip-path]

作用:
  1. 用 Python 3.10～3.14 创建/复用项目 .venv
  2. 升级 pip（>=21.3）并 pip install -e .
  3. 把 .venv\Scripts 的绝对路径写入【用户 PATH】（办法 1：免每次 activate）
  4. 同步到当前终端 PATH，立刻可试 sddl

选项:
  --force       删除并重建 .venv
  --skip-path   只装环境，不改用户 PATH
  -h, --help
"@
}

function Die([string]$Message) {
    [Console]::Error.WriteLine("错误: $Message")
    exit 1
}

function Test-PythonCandidate($File, [string[]]$Prefix) {
    if ($File -match '(?i)\\WindowsApps\\') { return $false }
    try {
        $out = & $File @($Prefix + @("--version")) 2>&1 | Out-String
        if ($LASTEXITCODE -ne 0) { return $false }
        if ($out -notmatch 'Python\s+(\d+)\.(\d+)') { return $false }
        $maj = [int]$Matches[1]
        $min = [int]$Matches[2]
        return ($maj -eq 3 -and $min -ge $PyMinMinor -and $min -le $PyMaxMinor)
    } catch {
        return $false
    }
}

function Resolve-PythonCommand {
    $candidates = New-Object System.Collections.Generic.List[object]
    if ($env:PYTHON_BIN) {
        [void]$candidates.Add(@{ Name = $env:PYTHON_BIN; Prefix = @() })
    }
    # 优先高版本：py -3.14 … -3.10，再 python / python3
    foreach ($m in 14..10) {
        [void]$candidates.Add(@{ Name = "py"; Prefix = @("-3.$m") })
    }
    [void]$candidates.Add(@{ Name = "py"; Prefix = @("-3") })
    [void]$candidates.Add(@{ Name = "python"; Prefix = @() })
    [void]$candidates.Add(@{ Name = "python3"; Prefix = @() })

    foreach ($c in $candidates) {
        $cmd = Get-Command $c.Name -ErrorAction SilentlyContinue
        if (-not $cmd) { continue }
        if (-not (Test-PythonCandidate $cmd.Source $c.Prefix)) { continue }
        return @{ File = $cmd.Source; Prefix = $c.Prefix }
    }
    Die "未找到 Python 3.$PyMinMinor～3.$PyMaxMinor（已试 py -3.14… / python / python3）。请安装官网 Python 或设置 PYTHON_BIN。"
}

function Invoke-Python($Python, [string[]]$PyArgs) {
    & $Python.File @($Python.Prefix + $PyArgs)
    if ($LASTEXITCODE -ne 0) {
        throw "python 退出码 $LASTEXITCODE"
    }
}

function Get-PythonVersionText($Python) {
    $out = & $Python.File @($Python.Prefix + @("--version")) 2>&1 | Out-String
    if ($out -match 'Python\s+(\d+\.\d+\.\d+|\d+\.\d+)') {
        return $Matches[1]
    }
    return $out.Trim()
}

function Test-VenvHealthy([string]$Dir) {
    $py = Join-Path $Dir "Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $py)) { return $false }
    $activate = Join-Path $Dir "Scripts\Activate.ps1"
    if (-not (Test-Path -LiteralPath $activate)) {
        $activate = Join-Path $Dir "Scripts\activate.bat"
    }
    if (-not (Test-Path -LiteralPath $activate)) { return $false }
    & $py -m pip --version 2>$null | Out-Null
    return ($LASTEXITCODE -eq 0)
}

function Test-PipMeetsMin([string]$Py) {
    $out = & $Py -m pip --version 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) { return $false }
    if ($out -match 'pip\s+(\d+)\.(\d+)') {
        $maj = [int]$Matches[1]
        $min = [int]$Matches[2]
        if ($maj -gt $MinPipMajor) { return $true }
        if ($maj -eq $MinPipMajor -and $min -ge $MinPipMinor) { return $true }
    }
    return $false
}

function Assert-PythonExeInRange([string]$PyExe, [string]$Label) {
    $out = & $PyExe --version 2>&1 | Out-String
    if ($out -notmatch 'Python\s+(\d+)\.(\d+)') {
        Die "$Label 无法解析版本: $out"
    }
    $maj = [int]$Matches[1]
    $min = [int]$Matches[2]
    if (-not ($maj -eq 3 -and $min -ge $PyMinMinor -and $min -le $PyMaxMinor)) {
        Die "$Label 版本为 $maj.$min，需要 3.$PyMinMinor～3.$PyMaxMinor。请加 --force 重建 venv，或安装对应 Python。"
    }
}

function Remove-StalePipArtifacts([string]$VenvRoot) {
    $sitePackages = Join-Path $VenvRoot "Lib\site-packages"
    if (-not (Test-Path -LiteralPath $sitePackages)) { return }

    $staleItems = @(Get-ChildItem -LiteralPath $sitePackages -Force |
        Where-Object { $_.Name.StartsWith("~") })
    if ($staleItems.Count -eq 0) { return }

    Write-Host "==> 清理 pip 残留目录/文件"
    foreach ($item in $staleItems) {
        Write-Host "    删除: $($item.FullName)"
        try {
            Remove-Item -LiteralPath $item.FullName -Recurse -Force -ErrorAction Stop
        } catch {
            Die "无法清理 pip 残留: $($item.FullName)。请关闭占用该 venv 的 Python/终端后重试。详情: $_"
        }
    }
}

function Add-UserPath([string]$Entry) {
    $entry = [System.IO.Path]::GetFullPath($Entry).TrimEnd('\')
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if (-not $userPath) { $userPath = "" }
    $parts = $userPath -split ';' | Where-Object { $_ -and $_.Trim() -ne "" }
    foreach ($p in $parts) {
        try {
            if ([System.IO.Path]::GetFullPath($p.TrimEnd('\')) -eq $entry) {
                Write-Host "==> 用户 PATH 已包含: $entry"
                return $false
            }
        } catch { }
    }
    $newPath = if ($userPath.Trim() -eq "") { $entry } else { "$userPath;$entry" }
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Host "==> 已写入用户 PATH: $entry"
    return $true
}

# ---------- args ----------
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
    } elseif ($a -eq "--skip-path") {
        $SkipPath = $true
        $i++
    } else {
        Die "未知参数: $a（见 --help）"
    }
}

# ---------- python / venv ----------
$Python = Resolve-PythonCommand
$verText = Get-PythonVersionText $Python
Write-Host "==> Python: $($Python.File) $($Python.Prefix -join ' ') ($verText)"

if ($Force -and (Test-Path -LiteralPath $VenvDir)) {
    Write-Host "==> --force：删除 $VenvDir"
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
        Die "虚拟环境不可用，请确认 Python 安装时勾选 pip / ensurepip"
    }
}

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $VenvPython)) {
    Die "未找到 $VenvPython"
}
Assert-PythonExeInRange $VenvPython "虚拟环境 Python"
Write-Host "==> 虚拟环境 Python 版本 OK（须为 3.$PyMinMinor～3.$PyMaxMinor）"

$VenvRoot = (Resolve-Path $VenvDir).Path
Remove-StalePipArtifacts $VenvRoot

Write-Host "==> 升级 pip / setuptools / wheel"
& $VenvPython -m pip install -U "pip>=$MinPipMajor.$MinPipMinor" setuptools wheel
if ($LASTEXITCODE -ne 0) { Die "升级 pip 失败" }
if (-not (Test-PipMeetsMin $VenvPython)) {
    Die "pip 仍低于 $MinPipMajor.$MinPipMinor"
}
Write-Host "    $(& $VenvPython -m pip --version)"

Write-Host "==> pip install -e ."
& $VenvPython -m pip install -e .
if ($LASTEXITCODE -ne 0) { Die "pip install -e . 失败" }

$ScriptsDir = (Resolve-Path (Join-Path $VenvDir "Scripts")).Path
$SddlExe = Join-Path $ScriptsDir "sddl.exe"
if (-not (Test-Path -LiteralPath $SddlExe)) {
    Die "安装后未找到 sddl.exe: $SddlExe"
}

# 当前会话立刻可用
if ($env:Path -notlike "*$ScriptsDir*") {
    $env:Path = "$ScriptsDir;$env:Path"
    Write-Host "==> 已加入当前终端 PATH"
}

if (-not $SkipPath) {
    [void](Add-UserPath $ScriptsDir)
    Write-Host ""
    Write-Host "==> 环境就绪（项目 venv + 用户 PATH）"
    Write-Host "    请【新开一个终端】后任意目录执行: sddl init"
    Write-Host "    本窗口也可直接试: sddl --help"
} else {
    Write-Host ""
    Write-Host "==> 环境就绪（未改用户 PATH，--skip-path）"
    Write-Host "    本窗口: sddl --help"
    Write-Host "    或手动把下列目录加入用户 PATH:"
    Write-Host "    $ScriptsDir"
}
