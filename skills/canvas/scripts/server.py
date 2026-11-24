#!/usr/bin/env python3
import argparse
import base64
import http.server
import json
import os
import socketserver
import sys
import tempfile
import threading
import time
import webbrowser

# Static page files; resolved from this script so it works from any cwd.
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "web")

saved_path = None
prompt_text = ""
shutdown_event = threading.Event()


class Handler(http.server.SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def log_message(self, format, *args):
        pass  # Keep stdout clean for the agent

    def list_directory(self, path):
        self.send_error(404)  # No directory listings

    def do_GET(self):
        if self.path == "/prompt":
            body = json.dumps(prompt_text).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            super().do_GET()

    def do_POST(self):
        global saved_path
        if self.path == "/save":
            try:
                length = int(self.headers["Content-Length"])
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                img_bytes = base64.b64decode(payload["image"].split(",")[1])
            except (KeyError, IndexError, TypeError, ValueError):
                self.send_response(400)
                self.end_headers()
                return

            fd, saved_path = tempfile.mkstemp(prefix="agent_sketch_", suffix=".png")
            with os.fdopen(fd, "wb") as f:
                f.write(img_bytes)

            self.send_response(200)
            self.end_headers()
            shutdown_event.set()
        elif self.path == "/cancel":
            self.send_response(200)
            self.end_headers()
            shutdown_event.set()
        else:
            self.send_response(404)
            self.end_headers()


def main():
    global prompt_text
    parser = argparse.ArgumentParser(description="Open a sketch canvas and print the saved PNG path.")
    parser.add_argument("--prompt", default="", help="Instruction shown above the canvas")
    parser.add_argument("--timeout", type=float, default=600, help="Seconds to wait before giving up (default 600)")
    args = parser.parse_args()
    prompt_text = args.prompt

    with socketserver.TCPServer(("127.0.0.1", 0), Handler) as httpd:
        port = httpd.server_address[1]
        url = f"http://127.0.0.1:{port}"

        server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        server_thread.start()

        # stderr so stdout stays just the path; lets the agent hand the URL to the user if no browser opened.
        print(f"Canvas open at {url}", file=sys.stderr, flush=True)
        webbrowser.open(url)
        shutdown_event.wait(args.timeout)  # Blocks until Done, Cancel or timeout
        time.sleep(0.2)  # Allow HTTP response to flush
        httpd.shutdown()

    if saved_path:
        print(saved_path)
    else:
        print("No drawing received (cancelled or timed out).", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
