"""
How to expose vLLM from a Jupyter-only server so local Docker can reach it.

Paste each cell into a Jupyter notebook on the GPU server.
The URL printed at the end goes into VLLM_URL in your local .env.
"""

# ============================================================
# CELL 1 — Install dependencies (run once)
# ============================================================
# !pip install vllm pyngrok --quiet
# OR use cloudflared (no account needed):
# !wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O cloudflared
# !chmod +x cloudflared

# ============================================================
# CELL 2 — Start vLLM server in the background
# ============================================================
import subprocess, time, os

# Adjust model name, port, and GPU args for your server
vllm_proc = subprocess.Popen(
    [
        "python", "-m", "vllm.entrypoints.openai.api_server",
        "--model", "google/gemma-2-9b-it",   # heavy local model
        "--port", "8000",
        "--max-model-len", "8192",
        "--enable-auto-tool-choice",
        "--tool-call-parser", "hermes",
        # "--tensor-parallel-size", "2",       # uncomment if multi-GPU
        # "--dtype", "bfloat16",
    ],
    stdout=open("/tmp/vllm.log", "w"),
    stderr=subprocess.STDOUT,
)
print(f"vLLM started (PID {vllm_proc.pid}). Waiting for it to load...")

# Wait until the server responds (model load takes 30-120s)
import urllib.request
for i in range(120):
    try:
        urllib.request.urlopen("http://localhost:8000/health", timeout=2)
        print(f"vLLM ready after {i*2}s")
        break
    except Exception:
        time.sleep(2)
else:
    print("vLLM did not start in time — check /tmp/vllm.log")

# ============================================================
# CELL 3 — Expose via ngrok (option A — requires free ngrok account)
# ============================================================
# from pyngrok import ngrok, conf
# conf.get_default().auth_token = "YOUR_NGROK_TOKEN"   # paste once
# tunnel = ngrok.connect(8000, "http")
# vllm_url = tunnel.public_url
# print(f"\nSet in your local .env:\nVLLM_URL={vllm_url}\n")

# ============================================================
# CELL 3 — Expose via cloudflared (option B — no account needed)
# ============================================================
import subprocess, threading, re, time

_url_found = []

def _tail(proc):
    for line in proc.stderr:
        line = line.decode("utf-8", errors="replace")
        m = re.search(r"https://[a-z0-9\-]+\.trycloudflare\.com", line)
        if m and not _url_found:
            _url_found.append(m.group(0))
            print(f"\n{'='*50}")
            print(f"  VLLM_URL={m.group(0)}")
            print(f"  Paste this into your local .env file")
            print(f"{'='*50}\n")

cf_proc = subprocess.Popen(
    ["./cloudflared", "tunnel", "--url", "http://localhost:8000"],
    stderr=subprocess.PIPE,
)
t = threading.Thread(target=_tail, args=(cf_proc,), daemon=True)
t.start()
print("cloudflared starting — URL will appear below in a few seconds...")

# Wait up to 30s for the URL
for _ in range(15):
    if _url_found:
        break
    time.sleep(2)

# ============================================================
# CELL 4 — Verify the tunnel works (run this from your LAPTOP)
# ============================================================
# import httpx
# r = httpx.get("https://YOUR-TUNNEL-URL/health")
# print(r.json())   # should print {"status": "ok"}

# ============================================================
# CELL 5 — (Optional) serve a second, lighter model on port 8001
# ============================================================
# vllm_light = subprocess.Popen(
#     [
#         "python", "-m", "vllm.entrypoints.openai.api_server",
#         "--model", "google/gemma-2-2b-it",
#         "--port", "8001",
#         "--max-model-len", "8192",
#     ],
#     stdout=open("/tmp/vllm_light.log", "w"),
#     stderr=subprocess.STDOUT,
# )
# Expose port 8001 via a second cloudflared tunnel if needed.
# Then set VLLM_URL to the light-model URL and FIREWORKS_KEY stays optional.

# ============================================================
# CELL 6 — Shutdown (run when done)
# ============================================================
# vllm_proc.terminate()
# cf_proc.terminate()
# print("Servers stopped.")
