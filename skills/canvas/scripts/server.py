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

HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
  <title>Agent Drawing Canvas</title>
  <style>
    body { margin: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; background: #1e1e1e; color: #fff; font-family: sans-serif; }
    canvas { background: #ffffff; border-radius: 6px; cursor: crosshair; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
    .toolbar { margin-top: 12px; display: flex; gap: 10px; align-items: center; }
    button { padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
    #done { background: #22c55e; color: white; }
    #clear { background: #ef4444; color: white; }
    input[type="color"] { border: none; width: 36px; height: 36px; cursor: pointer; background: none; }
  </style>
</head>
<body>
  <h3 id="prompt" style="margin:0 0 12px;font-weight:normal"></h3>
  <canvas id="pad" width="800" height="500" style="touch-action:none"></canvas>
  <div class="toolbar">
    <input type="color" id="color" value="#000000" title="Brush Color">
    <input type="range" id="size" min="1" max="20" value="4" title="Brush Size">
    <button id="eraser" style="background:#555;color:white">Eraser</button>
    <button id="undo" style="background:#555;color:white">Undo</button>
    <button id="clear">Clear</button>
    <button id="cancel" style="background:#555;color:white">Cancel</button>
    <button id="done">Done & Send to Agent</button>
  </div>
  <script>
    const canvas = document.getElementById('pad');
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    document.getElementById('prompt').textContent = __PROMPT__;

    let drawing = false, erasing = false;
    const history = [];
    const snapshot = () => { history.push(ctx.getImageData(0, 0, canvas.width, canvas.height)); if (history.length > 50) history.shift(); };
    canvas.onpointerdown = (e) => { snapshot(); drawing = true; canvas.setPointerCapture(e.pointerId); ctx.beginPath(); ctx.moveTo(e.offsetX, e.offsetY); };
    canvas.onpointermove = (e) => {
      if (!drawing) return;
      ctx.strokeStyle = erasing ? '#ffffff' : document.getElementById('color').value;
      ctx.lineWidth = erasing ? document.getElementById('size').value * 4 : document.getElementById('size').value;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.lineTo(e.offsetX, e.offsetY);
      ctx.stroke();
    };
    canvas.onpointerup = canvas.onpointercancel = () => { drawing = false; };

    const undo = () => { if (history.length) ctx.putImageData(history.pop(), 0, 0); };
    document.getElementById('undo').onclick = undo;
    window.onkeydown = (e) => { if ((e.metaKey || e.ctrlKey) && e.key === 'z') { e.preventDefault(); undo(); } };
    const eraserBtn = document.getElementById('eraser');
    eraserBtn.onclick = () => { erasing = !erasing; eraserBtn.style.background = erasing ? '#3b82f6' : '#555'; };

    document.getElementById('clear').onclick = () => {
      snapshot();
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
    };

    document.getElementById('cancel').onclick = async () => {
      await fetch('/cancel', { method: 'POST' });
      document.body.innerHTML = "<h2>Cancelled. You can close this tab.</h2>";
      window.close();
    };

    async function submitAndClose() {
      const dataUrl = canvas.toDataURL('image/png');
      await fetch('/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: dataUrl })
      });
      document.body.innerHTML = "<h2>Saved! You can close this tab.</h2>";
      window.close();
    }

    document.getElementById('done').onclick = submitAndClose;
  </script>
</body>
</html>
"""

saved_path = None
prompt_text = ""
shutdown_event = threading.Event()


class Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass  # Keep stdout clean for the agent

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        # json.dumps gives a safe JS string literal; escape '<' so it can't close the <script>.
        page = HTML_PAGE.replace("__PROMPT__", json.dumps(prompt_text).replace("<", "\\u003c"))
        self.wfile.write(page.encode("utf-8"))

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
