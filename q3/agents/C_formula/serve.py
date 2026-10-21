import http.server, os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))
class H(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin','*'); self.send_header('Access-Control-Allow-Private-Network','true'); super().end_headers()
    def do_OPTIONS(self): self.send_response(204); self.end_headers()
http.server.ThreadingHTTPServer(('127.0.0.1',8765),H).serve_forever()
