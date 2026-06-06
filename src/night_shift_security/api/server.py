"""Lightweight public findings API — stdlib HTTP server."""

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from night_shift_security.api.query import (
    check_api_auth,
    filter_findings,
    paginate_findings,
    parse_query_params,
)


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

    def _auth_or_reject(self, params: dict) -> bool:
        header_key = self.headers.get("X-API-Key") or self.headers.get("Authorization", "").removeprefix("Bearer ")
        if not check_api_auth(params, header_key):
            self._send_json({"error": "Unauthorized"}, status=401)
            return False
        return True

    def _filtered_response(self, feed: dict, params: dict, *, include_meta: bool = True) -> dict:
        findings = filter_findings(feed["findings"], params)
        page_data = paginate_findings(findings, params["page"], params["limit"])

        response: dict = {
            "schema_version": feed["schema_version"],
            "generated_at": feed["generated_at"],
            "total": page_data["pagination"]["total"],
            "pagination": page_data["pagination"],
            "findings": page_data["findings"],
        }
        if include_meta:
            response["by_severity"] = feed["summary"]["by_severity"]
            response["filters_applied"] = {
                k: v for k, v in {
                    "severity": params.get("severity"),
                    "template_id": params.get("template_id"),
                    "disclosure_status": params.get("disclosure_status"),
                    "min_severity_score": params.get("min_severity_score"),
                }.items()
                if v is not None
            }
        return response

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        params = parse_query_params(parsed.query)

        if path == "/api/v1/health":
            feed = self._load_feed()
            self._send_json({
                "status": "ok" if feed else "no_data",
                "findings_loaded": feed["summary"]["total_findings"] if feed else 0,
                "auth_required": bool(os.environ.get("NIGHT_SHIFT_API_KEY")),
            })
            return

        if not self._auth_or_reject(params):
            return

        feed = self._load_feed()
        if not feed:
            self._send_json({"error": "No dataset found. Run pipeline first."}, status=503)
            return

        if path == "/api/v1/findings":
            self._send_json(self._filtered_response(feed, params))
            return

        if path == "/api/v1/feed":
            self._send_json(self._filtered_response(feed, params, include_meta=True))
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
                "/api/v1/findings?page=1&limit=50",
                "/api/v1/feed?severity=critical&template_id=governance_capture",
                "/api/v1/findings/{id}",
                "/api/v1/bridge/tokenomics",
            ],
            "query_params": [
                "page", "limit", "severity", "template_id", "min_severity_score",
                "disclosure_status", "api_key",
            ],
            "auth": "Set NIGHT_SHIFT_API_KEY env; pass via X-API-Key header or ?api_key=",
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
    auth_note = " (auth required)" if os.environ.get("NIGHT_SHIFT_API_KEY") else ""
    print(f"Night Shift Security API serving at http://{host}:{port}{auth_note}")
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