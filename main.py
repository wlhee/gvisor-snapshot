from http.server import BaseHTTPRequestHandler, HTTPServer
import subprocess
import os
import threading
import queue
import json

PORT = 8080
CONTAINER_ID = "fib-container"
process = None
log_queue = queue.Queue()

def reader_thread(pipe):
    while True:
        try:
            line = pipe.readline()
            if line:
                log_queue.put(line)
            else:
                break
        except:
            break

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
        elif self.path == '/status':
            self.get_status()
        elif self.path == '/logs':
            self.get_logs()
        elif self.path == '/list':
            self.list_containers()
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

        bundle_dir = "/runsc_bundle"
        os.makedirs(bundle_dir, exist_ok=True)

        config = {
            "ociVersion": "1.0.0",
            "process": {
                "args": ["python3", "fib.py"],
                "cwd": "/",
                "env": [f"{k}={v}" for k, v in os.environ.items() if k not in ["HOSTNAME", "HOME"]],
            },
            "root": {
                "path": "/",
                "readonly": True
            },
            "mounts": [
                {
                    "destination": "/proc",
                    "type": "proc",
                    "source": "proc"
                }
            ]
        }
        with open(os.path.join(bundle_dir, "config.json"), "w") as f:
            json.dump(config, f, indent=4)

        try:
            # Create the container
            create_cmd = ["runsc", "create", "--bundle", bundle_dir, CONTAINER_ID]
            subprocess.run(create_cmd, check=True)

            # Start the container
            start_cmd = ["runsc", "start", CONTAINER_ID]
            process = subprocess.Popen(start_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

            t = threading.Thread(target=reader_thread, args=(process.stdout,))
            t.daemon = True
            t.start()

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
            # Kill the container process
            kill_cmd = ["runsc", "kill", CONTAINER_ID, "SIGKILL"]
            subprocess.run(kill_cmd, check=False)

            # Delete the container
            delete_cmd = ["runsc", "delete", CONTAINER_ID]
            subprocess.run(delete_cmd, check=False)

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
            subprocess.run(["runsc", "resume", CONTAINER_ID], check=True)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"App restored")
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

    def get_status(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        if process is None:
            self.wfile.write(b"App not running")
        else:
            self.wfile.write(b"App is running")

    def get_logs(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        while not log_queue.empty():
            self.wfile.write(log_queue.get().encode())

    def list_containers(self):
        try:
            result = subprocess.run(["runsc", "list"], check=True, capture_output=True, text=True)
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(result.stdout.encode())
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

if __name__ == "__main__":
    with HTTPServer(("", PORT), MyServer) as httpd:
        print("serving at port", PORT)
        httpd.serve_forever()