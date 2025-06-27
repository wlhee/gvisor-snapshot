from http.server import BaseHTTPRequestHandler, HTTPServer
import subprocess
import os

PORT = 8080
CONTAINER_ID = "fib-container"
process = None

class MyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/start':
            self.start_app()
        elif self.path == '/stop':
            self.stop_app()
        elif self.path == '/suspend':
            self.suspend_app()
        elif self.path == '/restore':
            self.restore_app()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def start_app(self):
        global process
        if process is not None:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"App already running")
            return

        try:
            # Using runsc to start the sandboxed application
            # The container ID is set to "fib-container"
            # We are detaching the process so the server doesn't block
            runsc_cmd = ["runsc", "--network=host", "do", "python3", "fib.py"]
            process = subprocess.Popen(runsc_cmd, preexec_fn=os.setsid)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"App started")
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

    def stop_app(self):
        global process
        if process is None:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"App not running")
            return

        try:
            # Killing the process group
            os.killpg(os.getpgid(process.pid), subprocess.signal.SIGTERM)
            process = None
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"App stopped")
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

    def suspend_app(self):
        try:
            # Using runsc to pause the container
            subprocess.run(["runsc", "pause", CONTAINER_ID], check=True)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"App suspended")
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

    def restore_app(self):
        try:
            # Using runsc to resume the container
            subprocess.run(["runsc", "resume", CONTAINER_ID], check=True)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"App restored")
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())


if __name__ == "__main__":
    with HTTPServer(("", PORT), MyServer) as httpd:
        print("serving at port", PORT)
        httpd.serve_forever()
