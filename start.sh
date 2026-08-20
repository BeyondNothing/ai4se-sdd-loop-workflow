#!/usr/bin/env bash
# start.sh — 创建虚拟环境、安装依赖并启动 ai4se-sdd-loop-workflow
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="${VENV_DIR:-.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

# ---------- helpers ----------
usage() {
  cat <<'EOF'
用法:
  ./start.sh [选项] [需求描述]
  ./start.sh [选项] --file <需求文件>
  Windows: .\\start.cmd [同样选项]

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
  # 调试：不调真实 AI，只跑通编排
  # 产出在 <应用根>/docs/<name>/（非本仓库内）
  ./start.sh --tool echo --skip-clarification --file ../docs/requirements/jwt-login-requirement.md --name jwt-login

  # 指定需求目录名
  ./start.sh --name jwt-login --file ../docs/requirements/jwt-login-requirement.md

  # 续跑：已有 docs/jwt-login/00-requirement.md 时可只传 --name
  ./start.sh --name jwt-login

  # 直接传需求文本
  ./start.sh --tool echo "实现用户登录功能，支持 JWT 认证"
EOF
}

die() {
  echo "错误: $*" >&2
  exit 1
}

MIN_NODE_MAJOR=18

node_major_version() {
  if ! command -v node >/dev/null 2>&1; then
    echo 0
    return
  fi
  node -p "process.versions.node.split('.')[0]" 2>/dev/null || echo 0
}

ensure_node_for_playwright() {
  if [[ "$SKIP_MCP_SETUP" -eq 1 ]]; then
    return 0
  fi

  local major
  major="$(node_major_version)"
  if [[ "$major" -ge "$MIN_NODE_MAJOR" ]]; then
    echo "==> Node: $(node -v)（满足 Playwright MCP 要求）"
    return 0
  fi

  if ! command -v node >/dev/null 2>&1; then
    echo "==> 未检测到 node，尝试通过 nvm 安装/切换..."
  else
    echo "==> 当前 Node $(node -v)，Playwright MCP 需要 ${MIN_NODE_MAJOR}+，尝试 nvm 切换..."
  fi

  export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
  if [[ -s "$NVM_DIR/nvm.sh" ]]; then
    # shellcheck disable=SC1091
    source "$NVM_DIR/nvm.sh"
  else
    die "Node 版本低于 ${MIN_NODE_MAJOR} 且未找到 nvm（\$NVM_DIR/nvm.sh），请先 nvm install 20"
  fi

  local ver
  for ver in 20 18; do
    if nvm use "$ver" >/dev/null 2>&1; then
      major="$(node_major_version)"
      if [[ "$major" -ge "$MIN_NODE_MAJOR" ]]; then
        echo "==> 已切换 Node: $(node -v)（nvm use ${ver}）"
        return 0
      fi
    fi
  done

  echo "==> 本地无 Node ${MIN_NODE_MAJOR}+，尝试 nvm install 20..."
  if nvm install 20 >/dev/null 2>&1 && nvm use 20 >/dev/null 2>&1; then
    echo "==> 已安装并切换 Node: $(node -v)"
    return 0
  fi

  die "无法切换到 Node ${MIN_NODE_MAJOR}+，Playwright MCP 将无法连接"
}

ensure_playwright_browsers() {
  if [[ "$SKIP_MCP_SETUP" -eq 1 ]]; then
    return 0
  fi

  local script="$SCRIPT_DIR/scripts/playwright-mcp.sh"
  [[ -x "$script" ]] || chmod +x "$script"

  if [[ "$(uname -s)" == "Darwin" ]] && [[ -x "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]]; then
    echo "==> Playwright MCP: 使用系统 Google Chrome"
    return 0
  fi

  echo "==> 安装 Playwright MCP 浏览器（无系统 Chrome 时）..."
  npx -y @playwright/mcp@0.0.79 install-browser chrome-for-testing || \
    npx -y playwright install chrome || true
}

# ---------- parse args ----------
SKIP_MCP_SETUP=0
SKIP_INSTALL=0
TOOL=""
DOCS_DIR=""
REQ_NAME=""
REQ_FILE=""
REQ_TEXT=()
SKIP_CLARIFICATION=0
FRESH=0
REQ_FILE=""
REQ_TEXT=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --skip-mcp-setup)
      SKIP_MCP_SETUP=1
      shift
      ;;
    --skip-install)
      SKIP_INSTALL=1
      shift
      ;;
    --skip-clarification)
      SKIP_CLARIFICATION=1
      shift
      ;;
    --fresh)
      FRESH=1
      shift
      ;;
    -t|--tool)
      [[ $# -ge 2 ]] || die "--tool 需要参数"
      TOOL="$2"
      shift 2
      ;;
    -n|--name)
      [[ $# -ge 2 ]] || die "--name 需要参数"
      REQ_NAME="$2"
      shift 2
      ;;
    -d|--docs-dir)
      [[ $# -ge 2 ]] || die "--docs-dir 需要参数"
      DOCS_DIR="$2"
      shift 2
      ;;
    -f|--file)
      [[ $# -ge 2 ]] || die "--file 需要参数"
      REQ_FILE="$2"
      shift 2
      ;;
    --)
      shift
      REQ_TEXT+=("$@")
      break
      ;;
    -*)
      die "未知选项: $1（用 --help 查看用法）"
      ;;
    *)
      REQ_TEXT+=("$1")
      shift
      ;;
  esac
  done

# 单个 .md 路径参数视为 --file
if [[ -z "$REQ_FILE" && ${#REQ_TEXT[@]} -eq 1 ]]; then
  single="${REQ_TEXT[0]}"
  if [[ "$single" == *.md && -f "$single" ]]; then
    REQ_FILE="$single"
    REQ_TEXT=()
  fi
fi

# ---------- python / venv ----------
command -v "$PYTHON_BIN" >/dev/null 2>&1 || die "未找到 $PYTHON_BIN，请先安装 Python 3.10+"

PY_VERSION="$("$PYTHON_BIN" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
echo "==> Python: $PYTHON_BIN ($PY_VERSION)"

if [[ ! -d "$VENV_DIR" ]]; then
  echo "==> 创建虚拟环境: $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
else
  echo "==> 复用虚拟环境: $VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

if [[ "$SKIP_INSTALL" -eq 0 ]]; then
  echo "==> 升级 pip"
  python -m pip install --upgrade pip >/dev/null
  echo "==> 安装 ai4se-sdd-loop-workflow（editable，含 langgraph 等依赖）"
  pip install -e .
else
  echo "==> 跳过依赖安装 (--skip-install)"
fi

# ---------- default requirement ----------
if [[ -z "$REQ_FILE" && ${#REQ_TEXT[@]} -eq 0 ]]; then
  DEFAULT_REQ="../docs/requirements/jwt-login-requirement.md"
  if [[ -f "$DEFAULT_REQ" ]]; then
    echo "==> 未传需求，使用默认: $DEFAULT_REQ"
    REQ_FILE="$DEFAULT_REQ"
  else
    die "请提供需求文本或 --file；也可用 --help 查看示例"
  fi
fi

# ---------- build run.py args ----------
RUN_ARGS=()
if [[ -n "$REQ_FILE" ]]; then
  [[ -f "$REQ_FILE" ]] || die "需求文件不存在: $REQ_FILE"
  RUN_ARGS+=(--file "$REQ_FILE")
elif [[ ${#REQ_TEXT[@]} -gt 0 ]]; then
  RUN_ARGS+=("${REQ_TEXT[*]}")
fi

if [[ -n "$TOOL" ]]; then
  RUN_ARGS+=(--tool "$TOOL")
fi
if [[ -n "$REQ_NAME" ]]; then
  RUN_ARGS+=(--name "$REQ_NAME")
fi
if [[ -n "$DOCS_DIR" ]]; then
  RUN_ARGS+=(--docs-dir "$DOCS_DIR")
fi
if [[ "$SKIP_CLARIFICATION" -eq 1 ]]; then
  RUN_ARGS+=(--skip-clarification)
fi
if [[ "$FRESH" -eq 1 ]]; then
  RUN_ARGS+=(--fresh)
fi
if [[ "$SKIP_MCP_SETUP" -eq 1 ]]; then
  RUN_ARGS+=(--skip-mcp-setup)
fi

ensure_node_for_playwright
ensure_playwright_browsers

echo "==> 启动 workflow"
echo "    python run.py ${RUN_ARGS[*]}"
echo

exec python run.py "${RUN_ARGS[@]}"
