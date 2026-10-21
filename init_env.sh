#!/usr/bin/env bash
# init_env.sh — 仅初始化本地环境（venv + pip≥21.3 + editable 安装），不启动 workflow
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="${VENV_DIR:-.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
MIN_PIP="21.3"
FORCE=0

usage() {
  cat <<'EOF'
用法:
  ./init_env.sh [--force]
  Windows: .\init_env.cmd [--force]

作用:
  创建/修复 .venv，将 pip 升到 ≥ 21.3，再执行 pip install -e .
  不启动 workflow（启动请用 ./start.sh 或 sddl:start）

选项:
  --force   强制删除并重建虚拟环境
  -h, --help

环境变量:
  VENV_DIR      虚拟环境目录（默认 .venv）
  PYTHON_BIN    创建 venv 用的解释器（默认 python3）
EOF
}

die() {
  echo "错误: $*" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --force) FORCE=1; shift ;;
    *) die "未知参数: $1（见 --help）" ;;
  esac
done

venv_python() {
  if [[ -x "$VENV_DIR/bin/python" ]]; then
    echo "$VENV_DIR/bin/python"
  elif [[ -x "$VENV_DIR/Scripts/python.exe" ]]; then
    echo "$VENV_DIR/Scripts/python.exe"
  else
    echo ""
  fi
}

venv_is_healthy() {
  local py
  py="$(venv_python)"
  [[ -n "$py" ]] || return 1
  if [[ ! -f "$VENV_DIR/bin/activate" && ! -f "$VENV_DIR/Scripts/activate.bat" ]]; then
    return 1
  fi
  "$py" -m pip --version >/dev/null 2>&1
}

pip_meets_min() {
  local py="$1"
  "$py" -c "
import sys
from pip import __version__ as v
parts = []
for x in v.split('.')[:2]:
    try:
        parts.append(int(''.join(c for c in x if c.isdigit()) or '0'))
    except ValueError:
        parts.append(0)
while len(parts) < 2:
    parts.append(0)
sys.exit(0 if tuple(parts[:2]) >= (21, 3) else 1)
"
}

command -v "$PYTHON_BIN" >/dev/null 2>&1 || die "未找到 $PYTHON_BIN，请先安装 Python 3.10+"

PY_VERSION="$("$PYTHON_BIN" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
PY_OK="$("$PYTHON_BIN" -c 'import sys; print(1 if sys.version_info >= (3, 10) else 0)')"
[[ "$PY_OK" == "1" ]] || die "需要 Python 3.10+，当前: $PY_VERSION"
echo "==> Python: $PYTHON_BIN ($PY_VERSION)"

if [[ "$FORCE" -eq 1 && -e "$VENV_DIR" ]]; then
  echo "==> --force：删除虚拟环境 $VENV_DIR"
  rm -rf "$VENV_DIR"
fi

if venv_is_healthy; then
  echo "==> 复用虚拟环境: $VENV_DIR"
else
  if [[ -e "$VENV_DIR" ]]; then
    echo "==> 虚拟环境不完整，重建: $VENV_DIR"
    rm -rf "$VENV_DIR"
  else
    echo "==> 创建虚拟环境: $VENV_DIR"
  fi
  "$PYTHON_BIN" -m venv "$VENV_DIR" || die "创建虚拟环境失败: $VENV_DIR"
  venv_is_healthy || die "虚拟环境创建后仍不可用（缺少 activate/pip），请检查 Python 是否带 ensurepip"
fi

VENV_PY="$(venv_python)"
[[ -n "$VENV_PY" ]] || die "未找到虚拟环境 Python"

echo "==> 升级 pip / setuptools / wheel（editable 安装需要 pip ≥ $MIN_PIP）"
"$VENV_PY" -m pip install -U "pip>=${MIN_PIP}" setuptools wheel || die "升级 pip/setuptools/wheel 失败"
pip_meets_min "$VENV_PY" || die "pip 仍低于 $MIN_PIP，请检查网络或手动: $VENV_PY -m pip install -U 'pip>=${MIN_PIP}'"
PIP_VER="$("$VENV_PY" -m pip --version | head -n1)"
echo "    $PIP_VER"

echo "==> 安装 ai4se-sdd-loop-workflow（editable: python -m pip install -e .）"
"$VENV_PY" -m pip install -e . || die "pip install -e . 失败。请把完整报错贴出；常见原因：pip < 21.3、未进 venv、网络/代理"

echo
echo "==> 环境就绪"
if [[ -f "$VENV_DIR/bin/activate" ]]; then
  echo "    激活: source $VENV_DIR/bin/activate"
else
  echo "    激活: $VENV_DIR\\Scripts\\activate"
fi
echo "    业务项目根执行: sddl:init"
echo "    启动 workflow:   sddl:start ...  或  ./start.sh ..."
