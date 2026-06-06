"""Lightweight public findings API — stdlib HTTP server."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


class FindingsAPIHandler(BaseHTTPRequestHandler):
    """Serve severity-ranked security findings from exported dataset."""

    dataset_path: Path = Path("data/security_results/dataset/latest.json")

    def log_message(self, format: str, *args) -> None:
        pass

    def _load_feed(self) -> dict | None:
        if not self.dataset_path.exists():
            return None
        with open(self.dataset_path) as f:
            return json.load(f)

    def _send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, indent=2, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/api/v1/health":
            feed = self._load_feed()
            self._send_json({
                "status": "ok" if feed else "no_data",
                "findings_loaded": feed["summary"]["total_findings"] if feed else 0,
            })
            return

        feed = self._load_feed()
        if not feed:
            self._send_json({"error": "No dataset found. Run pipeline first."}, status=503)
            return

        if path == "/api/v1/findings":
            self._send_json(feed)
            return

        if path == "/api/v1/feed":
            self._send_json({
                "schema_version": feed["schema_version"],
                "generated_at": feed["generated_at"],
                "total": feed["summary"]["total_findings"],
                "by_severity": feed["summary"]["by_severity"],
                "findings": feed["findings"],
            })
            return

        if path.startswith("/api/v1/findings/"):
            finding_id = path.split("/")[-1]
            match = next((f for f in feed["findings"] if f["finding_id"] == finding_id), None)
            if match:
                self._send_json(match)
            else:
                self._send_json({"error": f"Finding {finding_id} not found"}, status=404)
            return

        if path == "/api/v1/bridge/tokenomics":
            bridge_path = self.dataset_path.parent.parent / "bridge" / "tokenomics_risk_feed.json"
            if bridge_path.exists():
                with open(bridge_path) as f:
                    self._send_json(json.load(f))
            else:
                self._send_json({"error": "Tokenomics bridge feed not exported"}, status=404)
            return

        self._send_json({
            "endpoints": [
                "/api/v1/health",
                "/api/v1/findings",
                "/api/v1/feed",
                "/api/v1/findings/{id}",
                "/api/v1/bridge/tokenomics",
            ]
        })


def serve(
    host: str = "127.0.0.1",
    port: int = 8787,
    dataset_path: Path | None = None,
) -> None:
    """Start the public findings API server."""
    if dataset_path:
        FindingsAPIHandler.dataset_path = dataset_path

    server = ThreadingHTTPServer((host, port), FindingsAPIHandler)
    print(f"Night Shift Security API serving at http://{host}:{port}")
    print(f"Dataset: {FindingsAPIHandler.dataset_path}")
    print("Endpoints: /api/v1/health /api/v1/feed /api/v1/findings /api/v1/bridge/tokenomics")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


def serve_background(
    host: str = "127.0.0.1",
    port: int = 8787,
    dataset_path: Path | None = None,
) -> ThreadingHTTPServer:
    """Start server in background thread (for tests)."""
    if dataset_path:
        FindingsAPIHandler.dataset_path = dataset_path
    server = ThreadingHTTPServer((host, port), FindingsAPIHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server