#!/usr/bin/env bash
# =============================================================================
#  Findable — Stop Cloudflare tunnels first, then vLLM models
#
#  Usage:
#    bash stop_service.sh
# =============================================================================

set -euo pipefail

LOG_DIR="${HOME}/vllm_logs"

LIGHT_TUNNEL_PID_FILE="${LOG_DIR}/cloudflared_light.pid"
HEAVY_TUNNEL_PID_FILE="${LOG_DIR}/cloudflared_heavy.pid"

LIGHT_PID_FILE="${LOG_DIR}/light.pid"
HEAVY_PID_FILE="${LOG_DIR}/heavy.pid"

stop_from_pidfile() {
  local label="$1"
  local pid_file="$2"
  local force="${3:-false}"

  if [ ! -f "$pid_file" ]; then
    echo "  [$label] no pid file found: $pid_file"
    return 0
  fi

  local pid
  pid=$(cat "$pid_file")

  if ! kill -0 "$pid" 2>/dev/null; then
    echo "  [$label] already stopped. Removing stale pid file."
    rm -f "$pid_file"
    return 0
  fi

  if [ "$force" = true ]; then
    echo "  [$label] force stopping pid=$pid"
    kill -9 "$pid" 2>/dev/null || true
  else
    echo "  [$label] stopping pid=$pid"
    kill "$pid" 2>/dev/null || true
  fi

  for i in {1..20}; do
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "  [$label] stopped"
      rm -f "$pid_file"
      return 0
    fi
    sleep 1
  done

  echo "  [$label] did not stop gracefully. Force killing pid=$pid"
  kill -9 "$pid" 2>/dev/null || true
  rm -f "$pid_file"
}

echo ""
echo "============================================================"
echo "  Stopping Findable services"
echo "============================================================"
echo ""

echo "Step 1: stopping Cloudflare tunnels..."
stop_from_pidfile "cloudflared-light" "$LIGHT_TUNNEL_PID_FILE"
stop_from_pidfile "cloudflared-heavy" "$HEAVY_TUNNEL_PID_FILE"

echo ""
echo "Cleaning any leftover cloudflared processes..."
pkill -f "/workspace/bin/cloudflared" 2>/dev/null || true
pkill -f "cloudflared tunnel" 2>/dev/null || true

echo ""
echo "Step 2: stopping vLLM model servers..."
stop_from_pidfile "vllm-light" "$LIGHT_PID_FILE"
stop_from_pidfile "vllm-heavy" "$HEAVY_PID_FILE"

echo ""
echo "Cleaning any leftover vLLM child processes..."
pkill -f "vllm serve" 2>/dev/null || true
pkill -f "EngineCore" 2>/dev/null || true
pkill -f "APIServer" 2>/dev/null || true

echo ""
echo "Step 3: cleaning tunnel URL files..."
rm -f "${LOG_DIR}/cloudflared_light.url"
rm -f "${LOG_DIR}/cloudflared_heavy.url"
rm -f "${LOG_DIR}/tunnel_light.url"
rm -f "${LOG_DIR}/tunnel_heavy.url"

echo ""
echo "Current relevant processes:"
ps aux | grep -E "vllm|cloudflared|EngineCore|APIServer" | grep -v grep || echo "  No vLLM/cloudflared processes found."

echo ""
echo "GPU status:"
if command -v amd-smi >/dev/null 2>&1; then
  amd-smi
else
  echo "  amd-smi not found"
fi

echo ""
echo "============================================================"
echo "  Stop complete"
echo "============================================================"
echo ""
