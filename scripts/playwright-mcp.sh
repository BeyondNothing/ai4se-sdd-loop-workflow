#!/usr/bin/env bash
# 启动 Playwright MCP（stdio）。供 Cursor / Claude agent 调用；路径在 sync 时按本机仓库位置解析。
set -euo pipefail

MIN_NODE_MAJOR=18

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
        return 0
      fi
    fi
  done

  echo "Playwright MCP 需要 Node ${MIN_NODE_MAJOR}+，请运行: nvm install 20" >&2
  exit 1
}

ensure_node
exec npx -y @playwright/mcp@latest "$@"
