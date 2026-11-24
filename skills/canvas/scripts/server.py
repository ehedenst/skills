#!/usr/bin/env python3
import base64
import http.server
import json
import os
import socketserver
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
  <canvas id="pad" width="800" height="500"></canvas>
  <div class="toolbar">
    <input type="color" id="color" value="#000000" title="Brush Color">
    <input type="range" id="size" min="1" max="20" value="4" title="Brush Size">
    <button id="clear">Clear</button>
    <button id="done">Done & Send to Agent</button>
  </div>
  <script>
    const canvas = document.getElementById('pad');
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    let drawing = false;
    canvas.onmousedown = (e) => { drawing = true; ctx.beginPath(); ctx.moveTo(e.offsetX, e.offsetY); };
    canvas.onmousemove = (e) => {
      if (!drawing) return;
      ctx.strokeStyle = document.getElementById('color').value;
      ctx.lineWidth = document.getElementById('size').value;
      ctx.lineCap = 'round';
      ctx.lineTo(e.offsetX, e.offsetY);
      ctx.stroke();
    };
    window.onmouseup = () => { drawing = false; };

    document.getElementById('clear').onclick = () => {
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
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
shutdown_event = threading.Event()


class Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass  # Keep stdout clean for the agent

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(HTML_PAGE.encode("utf-8"))

    def do_POST(self):
        global saved_path
        if self.path == "/save":
            length = int(self.headers["Content-Length"])
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            img_data = payload["image"].split(",")[1]

            fd, saved_path = tempfile.mkstemp(prefix="agent_sketch_", suffix=".png")
            with os.fdopen(fd, "wb") as f:
                f.write(base64.b64decode(img_data))

            self.send_response(200)
            self.end_headers()
            shutdown_event.set()


def main():
    with socketserver.TCPServer(("127.0.0.1", 0), Handler) as httpd:
        port = httpd.server_address[1]
        url = f"http://127.0.0.1:{port}"

        server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        server_thread.start()

        webbrowser.open(url)
        shutdown_event.wait()  # Blocks until user clicks Done
        time.sleep(0.2)  # Allow HTTP response to flush
        httpd.shutdown()

    if saved_path:
        print(saved_path)


if __name__ == "__main__":
    main()
