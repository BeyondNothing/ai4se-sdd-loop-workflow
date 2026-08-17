#!/usr/bin/env bash
# 启动 Playwright MCP（stdio）。供 Cursor / Claude / Oh My Pi agent 调用。
set -euo pipefail

MIN_NODE_MAJOR=18
# 固定 minor 版本，避免 @latest 与本地 browser 二进制 revision 漂移
PLAYWRIGHT_MCP_PKG="${PLAYWRIGHT_MCP_PKG:-@playwright/mcp@0.0.79}"

node_major_version() {
  if ! command -v node >/dev/null 2>&1; then
    echo 0
    return
  fi
  node -p "process.versions.node.split('.')[0]" 2>/dev/null || echo 0
}

ensure_node() {
  local major
  major="$(node_major_version)"
  if [[ "$major" -ge "$MIN_NODE_MAJOR" ]]; then
    return 0
  fi

  export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
  if [[ -s "$NVM_DIR/nvm.sh" ]]; then
    # shellcheck disable=SC1091
    source "$NVM_DIR/nvm.sh"
  else
    echo "Playwright MCP 需要 Node ${MIN_NODE_MAJOR}+，且未找到 nvm（\$NVM_DIR/nvm.sh）" >&2
    exit 1
  fi

  local ver
  for ver in 20 18; do
    if nvm use "$ver" >/dev/null 2>&1; then
      major="$(node_major_version)"
      if [[ "$major" -ge "$MIN_NODE_MAJOR" ]]; then
        export PATH="$(dirname "$(command -v node)"):${PATH}"
        return 0
      fi
    fi
  done

  echo "Playwright MCP 需要 Node ${MIN_NODE_MAJOR}+，请运行: nvm install 20" >&2
  exit 1
}

system_chrome_path() {
  case "$(uname -s)" in
    Darwin)
      local mac="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
      [[ -x "$mac" ]] && echo "$mac" && return 0
      ;;
    Linux)
      for candidate in google-chrome google-chrome-stable chromium chromium-browser; do
        if command -v "$candidate" >/dev/null 2>&1; then
          command -v "$candidate"
          return 0
        fi
      done
      ;;
  esac
  return 1
}

ensure_playwright_browser() {
  if system_chrome_path >/dev/null 2>&1; then
    return 0
  fi

  echo "Playwright MCP: 未检测到系统 Chrome，安装 chrome-for-testing..." >&2
  npx -y "$PLAYWRIGHT_MCP_PKG" install-browser chrome-for-testing >&2 || \
    npx -y playwright install chrome >&2 || true
}

ensure_node
ensure_playwright_browser

# 默认 headed（有界面）；headless 由 workflow.e2e.headless 经 MCP sync 注入 --headless
DEFAULT_ARGS=(--browser chrome --timeout-navigation 60000 --timeout-action 60000)
if [[ "$#" -eq 0 ]]; then
  set -- "${DEFAULT_ARGS[@]}"
fi

exec npx -y "$PLAYWRIGHT_MCP_PKG" "$@"
