import os, sys, traceback

print("Starting music-api...", flush=True)

try:
    from server import app
    print("Server module loaded OK", flush=True)
except Exception as e:
    print(f"FATAL: Failed to load server module: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)

import uvicorn

port = int(os.environ.get("PORT", "8000"))
print(f"Listening on port {port}", flush=True)
uvicorn.run(app, host="0.0.0.0", port=port, proxy_headers=True, forwarded_allow_ips="*")
