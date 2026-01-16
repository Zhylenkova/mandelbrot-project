import socket
import pickle
import threading
import time
from flask import Flask, render_template, jsonify
from PIL import Image
import os

# Configuration
HOST = os.getenv('MASTER_HOST', '0.0.0.0')
PORT = int(os.getenv('MASTER_PORT', 65433))
WEB_PORT = int(os.getenv('WEB_PORT', 5001))
WIDTH, HEIGHT = 800, 800
MAX_ITER = 256
CHUNK_SIZE = 10  # Average chunk size

app = Flask(__name__)

class MandelbrotServer:
    def __init__(self):
        self.tasks = [(i, i + CHUNK_SIZE) for i in range(0, HEIGHT, CHUNK_SIZE)]
        self.pending_tasks = {}  
        self.results = {}
        self.workers = {} 
        self.completed_rows = 0
        self.lock = threading.Lock()
        self.running = True
        self.worker_counter = 0

    def start_socket_server(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        print(f"Socket server listening on {HOST}:{PORT}")

        # Start cleanup thread for fault tolerance
        threading.Thread(target=self.cleanup_workers, daemon=True).start()

        while self.completed_rows < HEIGHT:
            try:
                client_socket, addr = server_socket.accept()
                self.worker_counter += 1
                worker_id = f"worker_{self.worker_counter}"
                with self.lock:
                    self.workers[worker_id] = {
                        'address': addr,
                        'status': 'connected',
                        'last_seen': time.time(),
                        'tasks_done': 0
                    }
                threading.Thread(target=self.handle_worker, args=(client_socket, worker_id), daemon=True).start()
            except Exception as e:
                if self.running: print(f"Accept error: {e}")
                break
        
        server_socket.close()

    def handle_worker(self, client_socket, worker_id):
        try:
            while self.completed_rows < HEIGHT:
                with self.lock:
                    if not self.tasks:
                        if not self.pending_tasks:
                            break  
                        else:
                            time.sleep(1)
                            continue
                    
                    task_range = self.tasks.pop(0)
                    self.pending_tasks[task_range] = (worker_id, time.time())
                
                # Send task
                task_data = {
                    'range': task_range,
                    'width': WIDTH,
                    'height': HEIGHT,
                    'max_iter': MAX_ITER
                }
                client_socket.sendall(pickle.dumps(task_data) + b"END_TASK")

                # Receive result
                data = b""
                while True:
                    packet = client_socket.recv(16384)
                    if not packet: break
                    data += packet
                    if data.endswith(b"DONE_RESULT"):
                        data = data[:-11]
                        break
                
                if not data:
                    break

                result_data = pickle.loads(data) # List of (index, row_pixels)
                
                with self.lock:
                    for idx, pixels in result_data:
                        if idx not in self.results:
                            self.results[idx] = pixels
                            self.completed_rows += 1
                    
                    if task_range in self.pending_tasks:
                        del self.pending_tasks[task_range]
                    
                    self.workers[worker_id]['last_seen'] = time.time()
                    self.workers[worker_id]['tasks_done'] += 1

        except Exception as e:
            print(f"Worker {worker_id} error: {e}")
        finally:
            with self.lock:
                if worker_id in self.workers:
                    self.workers[worker_id]['status'] = 'disconnected'
            client_socket.close()

    def cleanup_workers(self):
        """Fault tolerance: reassignment of tasks from stalled or dead workers."""
        while self.completed_rows < HEIGHT:
            time.sleep(5)
            now = time.time()
            with self.lock:
                to_reassign = []
                for task_range, (worker_id, timestamp) in list(self.pending_tasks.items()):
                    if now - timestamp > 30: 
                        print(f"Task {task_range} timed out from {worker_id}. Reassigning.")
                        to_reassign.append(task_range)
                        del self.pending_tasks[task_range]
                
                for task in to_reassign:
                    self.tasks.append(task)
                
                for w_id, info in self.workers.items():
                    if info['status'] == 'connected' and now - info['last_seen'] > 35:
                        info['status'] = 'stale'

    def save_image(self):
        print("Saving final image...")
        img = Image.new('RGB', (WIDTH, HEIGHT))
        pixels = img.load()
        for y in range(HEIGHT):
            row = self.results.get(y)
            if row:
                for x, color in enumerate(row):
                    pixels[x, y] = (color, int(color*0.5), 255-color)
        img.save('mandelbrot_advanced.png')
        print("Saved as mandelbrot_advanced.png")

server = MandelbrotServer()

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/stats')
def stats():
    with server.lock:
        return jsonify({
            'progress': (server.completed_rows / HEIGHT) * 100,
            'workers': server.workers,
            'tasks_total': len(range(0, HEIGHT, CHUNK_SIZE)),
            'tasks_pending': len(server.pending_tasks),
            'tasks_queued': len(server.tasks),
            'completed_rows': server.completed_rows
        })

def run_flask():
    app.run(host='0.0.0.0', port=WEB_PORT, debug=False, use_reloader=False)

if __name__ == "__main__":
    # Start Flask
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Start Socket Server
    server.start_socket_server()
    
    while server.completed_rows < HEIGHT:
        time.sleep(1)
    
    server.save_image()
    print("All tasks completed. Server shutting down.")
