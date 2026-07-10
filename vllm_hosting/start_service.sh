#!/usr/bin/env bash
# =============================================================================
#  Findable — Combined vLLM + Cloudflare Tunnel Launcher
#  AMD Radeon PRO W7900 | 48 GB VRAM | ROCm 7.2.1
#
#  Starts sequentially:
#    1. Gemma 2 2B light model on port 8000
#    2. Gemma 2 9B heavy model on port 8001
#    3. Cloudflare tunnel for light model
#    4. Cloudflare tunnel for heavy model
#
#  Usage:
#    bash start_service.sh
#    bash start_service.sh --no-tunnel
#    bash start_service.sh --light-only
#    bash start_service.sh --heavy-only
#
#  Override examples:
#    MAX_LEN=6000 bash start_service.sh
#    VLLM_HOST=10.244.x.x bash start_service.sh
#    LIGHT_VRAM=0.25 HEAVY_VRAM=0.58 bash start_service.sh
#
#  Logs:
#    /root/vllm_logs/light.log
#    /root/vllm_logs/heavy.log
#    /root/vllm_logs/cloudflared_light.log
#    /root/vllm_logs/cloudflared_heavy.log
# =============================================================================

set -euo pipefail

# ── Model configuration ───────────────────────────────────────────────────────

LIGHT_MODEL_PATH="${LIGHT_MODEL_PATH:-/workspace/models/google--gemma-2-2b-it}"
HEAVY_MODEL_PATH="${HEAVY_MODEL_PATH:-/workspace/models/google--gemma-2-9b-it}"

LIGHT_PORT=8000
HEAVY_PORT=8001

# Conservative defaults for one AMD Radeon PRO W7900, ~48 GB VRAM
LIGHT_VRAM="${LIGHT_VRAM:-0.22}"
HEAVY_VRAM="${HEAVY_VRAM:-0.62}"

# Start safe. Increase only after load testing.
MAX_LEN="${MAX_LEN:-6000}"

LOG_DIR="${HOME}/vllm_logs"

# Persistent cloudflared binary path
CLOUDFLARED="${CLOUDFLARED:-/workspace/bin/cloudflared}"

# Auto-detect internal host IP. Override manually if needed:
#   VLLM_HOST=10.244.xxx.xxx bash start_service.sh
VLLM_HOST="${VLLM_HOST:-$(hostname -I | awk '{print $1}')}"

# ── Flags ─────────────────────────────────────────────────────────────────────

TUNNEL=true
START_LIGHT=true
START_HEAVY=true

for arg in "$@"; do
  case "$arg" in
    --no-tunnel)
      TUNNEL=false
      ;;
    --light-only)
      START_HEAVY=false
      ;;
    --heavy-only)
      START_LIGHT=false
      ;;
    *)
      echo "Unknown argument: $arg"
      echo ""
      echo "Usage:"
      echo "  bash start_service.sh"
      echo "  bash start_service.sh --no-tunnel"
      echo "  bash start_service.sh --light-only"
      echo "  bash start_service.sh --heavy-only"
      exit 1
      ;;
  esac
done

mkdir -p "$LOG_DIR"

# ── File paths ────────────────────────────────────────────────────────────────

LIGHT_LOG="${LOG_DIR}/light.log"
HEAVY_LOG="${LOG_DIR}/heavy.log"

LIGHT_PID_FILE="${LOG_DIR}/light.pid"
HEAVY_PID_FILE="${LOG_DIR}/heavy.pid"

LIGHT_TUNNEL_LOG="${LOG_DIR}/cloudflared_light.log"
HEAVY_TUNNEL_LOG="${LOG_DIR}/cloudflared_heavy.log"

LIGHT_TUNNEL_URL_FILE="${LOG_DIR}/cloudflared_light.url"
HEAVY_TUNNEL_URL_FILE="${LOG_DIR}/cloudflared_heavy.url"

LIGHT_TUNNEL_PID_FILE="${LOG_DIR}/cloudflared_light.pid"
HEAVY_TUNNEL_PID_FILE="${LOG_DIR}/cloudflared_heavy.pid"

# ── Helpers ───────────────────────────────────────────────────────────────────

check_model_path() {
  local label="$1"
  local path="$2"

  if [ ! -d "$path" ]; then
    echo "ERROR: ${label} model path not found:"
    echo "  $path"
    echo ""
    echo "Download the model first or fix the path."
    exit 1
  fi

  if [ ! -f "${path}/config.json" ]; then
    echo "ERROR: ${label} model config.json not found:"
    echo "  ${path}/config.json"
    exit 1
  fi
}

check_cloudflared() {
  if [ "$TUNNEL" = false ]; then
    return 0
  fi

  if [ ! -x "$CLOUDFLARED" ]; then
    echo "ERROR: cloudflared not found or not executable at:"
    echo "  $CLOUDFLARED"
    echo ""
    echo "Install it with:"
    echo "  mkdir -p /workspace/bin"
    echo "  curl -k -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /workspace/bin/cloudflared"
    echo "  chmod +x /workspace/bin/cloudflared"
    exit 1
  fi
}

is_pid_running() {
  local pid_file="$1"

  if [ -f "$pid_file" ]; then
    local pid
    pid=$(cat "$pid_file" 2>/dev/null || true)

    if [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
  fi

  return 1
}

wait_ready() {
  local label="$1"
  local port="$2"
  local pid_file="$3"
  local timeout="${4:-600}"

  local url="http://${VLLM_HOST}:${port}/health"
  local deadline=$(( $(date +%s) + timeout ))
  local dots=0

  printf "  [%s] waiting for server at %s " "$label" "$url"

  while [ "$(date +%s)" -lt "$deadline" ]; do
    if [ -f "$pid_file" ]; then
      local pid
      pid=$(cat "$pid_file" 2>/dev/null || true)

      if [ -n "${pid:-}" ] && ! kill -0 "$pid" 2>/dev/null; then
        echo ""
        echo "  ERROR: [$label] vLLM process exited early."
        echo "  Last 100 lines from ${LOG_DIR}/${label}.log:"
        tail -100 "${LOG_DIR}/${label}.log" || true
        return 1
      fi
    fi

    if curl -sf --max-time 5 "$url" >/dev/null 2>&1; then
      echo " READY"
      return 0
    fi

    sleep 5
    dots=$(( dots + 1 ))

    if [ $(( dots % 6 )) -eq 0 ]; then
      printf "\n  [%s] still loading (%d min elapsed)..." \
        "$label" "$(( ($(date +%s) - deadline + timeout) / 60 ))"
    else
      printf "."
    fi
  done

  echo ""
  echo "  ERROR: [$label] did not start within ${timeout}s."
  echo "  Check log:"
  echo "    tail -100 ${LOG_DIR}/${label}.log"
  return 1
}

start_vllm() {
  local label="$1"
  local model="$2"
  local port="$3"
  local dtype="$4"
  local vram="$5"
  local log_file="${LOG_DIR}/${label}.log"
  local pid_file="${LOG_DIR}/${label}.pid"

  if is_pid_running "$pid_file"; then
    echo "  [$label] already running with pid $(cat "$pid_file")"
    return 0
  fi

  echo "  [$label] launching"
  echo "    model : $model"
  echo "    port  : $port"
  echo "    dtype : $dtype"
  echo "    vram  : $vram"
  echo "    log   : $log_file"

  rm -f "$log_file"

  HIP_VISIBLE_DEVICES=0 \
  ROCR_VISIBLE_DEVICES=0 \
  vllm serve "$model" \
    --host 0.0.0.0 \
    --port "$port" \
    --dtype "$dtype" \
    --max-model-len "$MAX_LEN" \
    --gpu-memory-utilization "$vram" \
    --tensor-parallel-size 1 \
    --disable-log-requests \
    --served-model-name "$label" \
    >> "$log_file" 2>&1 &

  echo $! > "$pid_file"
  echo "  [$label] pid=$!"
}

stop_existing_tunnel() {
  local label="$1"
  local pid_file="$2"

  if [ -f "$pid_file" ]; then
    local old_pid
    old_pid=$(cat "$pid_file" 2>/dev/null || true)

    if [ -n "${old_pid:-}" ] && kill -0 "$old_pid" 2>/dev/null; then
      echo "  stopping existing ${label} tunnel pid=${old_pid}"
      kill "$old_pid" 2>/dev/null || true
      sleep 2
    fi

    rm -f "$pid_file"
  fi
}

start_tunnel_and_get_url() {
  local label="$1"
  local port="$2"
  local log_file="$3"
  local url_file="$4"
  local pid_file="$5"

  local max_attempts=5

  for attempt in $(seq 1 "$max_attempts"); do
    echo "  [$label] starting Cloudflare tunnel attempt ${attempt}/${max_attempts}"
    echo "  [$label] origin: http://${VLLM_HOST}:${port}"

    # Stop any previous attempt for this label
    stop_existing_tunnel "$label" "$pid_file"

    rm -f "$log_file" "$url_file"

    "$CLOUDFLARED" tunnel \
      --url "http://${VLLM_HOST}:${port}" \
      --protocol http2 \
      --edge-ip-version 4 \
      --no-autoupdate \
      > "$log_file" 2>&1 &

    local tunnel_pid=$!
    echo "$tunnel_pid" > "$pid_file"
    echo "  [$label] cloudflared pid=${tunnel_pid}"

    for i in {1..60}; do
      # If cloudflared died, stop waiting and retry
      if ! kill -0 "$tunnel_pid" 2>/dev/null; then
        echo "  [$label] cloudflared exited early."
        echo "  [$label] last log lines:"
        tail -30 "$log_file" || true
        break
      fi

      # Extract only real quick-tunnel subdomains, not api.trycloudflare.com
      local url
      url=$(
        grep -oE 'https://[-a-zA-Z0-9]+\.trycloudflare\.com' "$log_file" 2>/dev/null \
          | grep -v '^https://api\.trycloudflare\.com$' \
          | head -1 || true
      )

      if [ -n "$url" ]; then
        echo "$url" > "$url_file"
        echo "  [$label] URL: $url"
        return 0
      fi

      # Known quick tunnel creation failure
      if grep -q "failed to request quick Tunnel" "$log_file" 2>/dev/null; then
        echo "  [$label] quick tunnel request failed. Retrying..."
        echo "  [$label] last log lines:"
        tail -10 "$log_file" || true
        kill "$tunnel_pid" 2>/dev/null || true
        sleep 5
        break
      fi

      sleep 1
    done

    echo "  [$label] attempt ${attempt} failed."
    sleep 5
  done

  echo ""
  echo "ERROR: Could not create ${label} Cloudflare tunnel after ${max_attempts} attempts."
  echo "Check log:"
  echo "  cat $log_file"
  exit 1
}

cleanup_on_interrupt() {
  echo ""
  echo "Interrupted."
  echo "To stop everything cleanly, run:"
  echo "  bash stop_service.sh"
  echo ""
  echo "If stop script is unavailable, run:"
  echo "  pkill -f cloudflared"
  echo "  pkill -f 'vllm serve'"
  exit 130
}

trap cleanup_on_interrupt INT TERM

# ── Main ──────────────────────────────────────────────────────────────────────

echo ""
echo "============================================================"
echo "  Findable vLLM + Cloudflare Launcher"
echo "  GPU: AMD Radeon PRO W7900 | 48 GB | ROCm 7.2.1"
echo "============================================================"
echo ""
echo "Configuration:"
echo "  VLLM_HOST    : ${VLLM_HOST}"
echo "  MAX_LEN      : ${MAX_LEN}"
echo "  Tunnel       : ${TUNNEL}"
echo "  Light model  : ${LIGHT_MODEL_PATH}"
echo "  Heavy model  : ${HEAVY_MODEL_PATH}"
echo ""

if [ "$START_LIGHT" = true ]; then
  check_model_path "light" "$LIGHT_MODEL_PATH"
fi

if [ "$START_HEAVY" = true ]; then
  check_model_path "heavy" "$HEAVY_MODEL_PATH"
fi

check_cloudflared

echo "Starting vLLM servers sequentially..."
echo ""

if [ "$START_LIGHT" = true ]; then
  start_vllm "light" "$LIGHT_MODEL_PATH" "$LIGHT_PORT" "bfloat16" "$LIGHT_VRAM"
  wait_ready "light" "$LIGHT_PORT" "$LIGHT_PID_FILE"
fi

if [ "$START_HEAVY" = true ]; then
  start_vllm "heavy" "$HEAVY_MODEL_PATH" "$HEAVY_PORT" "bfloat16" "$HEAVY_VRAM"
  wait_ready "heavy" "$HEAVY_PORT" "$HEAVY_PID_FILE"
fi

echo ""
echo "vLLM servers are ready."
echo ""

if [ "$TUNNEL" = true ]; then
  echo "Starting Cloudflare tunnels..."
  echo ""

  if [ "$START_LIGHT" = true ]; then
    start_tunnel_and_get_url "light" "$LIGHT_PORT" "$LIGHT_TUNNEL_LOG" "$LIGHT_TUNNEL_URL_FILE" "$LIGHT_TUNNEL_PID_FILE"
  fi

  if [ "$START_HEAVY" = true ]; then
    start_tunnel_and_get_url "heavy" "$HEAVY_PORT" "$HEAVY_TUNNEL_LOG" "$HEAVY_TUNNEL_URL_FILE" "$HEAVY_TUNNEL_PID_FILE"
  fi

  echo ""
  echo "============================================================"
  echo "  Cloudflare tunnels are ready"
  echo "============================================================"
  echo ""

  if [ -f "$LIGHT_TUNNEL_URL_FILE" ]; then
    LIGHT_URL=$(cat "$LIGHT_TUNNEL_URL_FILE")
    echo "Light model:"
    echo "  VLLM_LIGHT_URL=${LIGHT_URL}"
    echo "  Test: curl ${LIGHT_URL}/health"
    echo "  Test: curl ${LIGHT_URL}/v1/models"
    echo ""
  fi

  if [ -f "$HEAVY_TUNNEL_URL_FILE" ]; then
    HEAVY_URL=$(cat "$HEAVY_TUNNEL_URL_FILE")
    echo "Heavy model:"
    echo "  VLLM_URL=${HEAVY_URL}"
    echo "  Test: curl ${HEAVY_URL}/health"
    echo "  Test: curl ${HEAVY_URL}/v1/models"
    echo ""
  fi

  echo "Tunnel logs:"
  echo "  tail -f ${LIGHT_TUNNEL_LOG}"
  echo "  tail -f ${HEAVY_TUNNEL_LOG}"
  echo ""
else
  echo "Tunnel skipped."
  echo ""
  echo "Internal URLs:"
  [ "$START_LIGHT" = true ] && echo "  Light: http://${VLLM_HOST}:${LIGHT_PORT}"
  [ "$START_HEAVY" = true ] && echo "  Heavy: http://${VLLM_HOST}:${HEAVY_PORT}"
  echo ""
fi

echo "============================================================"
echo "  All requested services are running"
echo "============================================================"
echo ""
echo "Logs:"
[ "$START_LIGHT" = true ] && echo "  Light vLLM: tail -f ${LIGHT_LOG}"
[ "$START_HEAVY" = true ] && echo "  Heavy vLLM: tail -f ${HEAVY_LOG}"
echo ""
echo "To cleanup services, run:"
echo "  bash stop_service.sh"
echo ""
echo "This script will now keep running."
echo ""

wait
