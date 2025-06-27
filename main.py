from http.server import BaseHTTPRequestHandler, HTTPServer
import subprocess
import os
import threading
import queue

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
            runsc_cmd = ["runsc", "--network=host", "do", "python3", "fib.py"]
            process = subprocess.Popen(runsc_cmd, preexec_fn=os.setsid, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            
            # Start a thread to read the output from the process
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

if __name__ == "__main__":
    with HTTPServer(("", PORT), MyServer) as httpd:
        print("serving at port", PORT)
        httpd.serve_forever()