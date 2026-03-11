#!/usr/bin/env python3
"""One-shot HTTP server that accepts a POST with base64 PNG data and saves it."""
import http.server
import base64
import os
import json

class SaveHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        data = json.loads(body)

        # Extract base64 from data URL
        b64 = data['image'].split(',', 1)[1]
        filename = data.get('filename', 'cover.png')

        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        with open(filepath, 'wb') as f:
            f.write(base64.b64decode(b64))

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({'saved': filepath, 'size': os.path.getsize(filepath)}).encode())

        # Shutdown after saving
        import threading
        threading.Thread(target=self.server.shutdown).start()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

if __name__ == '__main__':
    server = http.server.HTTPServer(('', 8766), SaveHandler)
    print("Waiting for image on port 8766...")
    server.serve_forever()
