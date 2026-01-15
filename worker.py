import socket
import pickle
import multiprocessing
import time
import os

# Configuration
SERVER_HOST = os.getenv('MASTER_HOST', '127.0.0.1')
SERVER_PORT = int(os.getenv('MASTER_PORT', 65433))

def calculate_mandelbrot(c, max_iter):
    z = complex(0, 0)
    for i in range(max_iter):
        if abs(z) > 2:
            return i
        z = z*z + c
    return max_iter

def calculate_julia(z, c_constant, max_iter):
    for i in range(max_iter):
        if abs(z) > 2:
            return i
        z = z*z + c_constant
    return max_iter

def worker_calculation(row_index, width, height, max_iter):
    row_pixels = []
    y_coord = (row_index / height) * 2 - 1
    
    # Example Julia constant
    julia_c = complex(-0.7, 0.27015)
    
    for x in range(width):
        x_coord = (x / width) * 3 - 2
        
        # Toggle between Mandelbrot and Julia for demo (alternating rows or similar)
        # Here we'll stick to Mandelbrot but include logic for switchability
        c = complex(x_coord, y_coord)
        val = calculate_mandelbrot(c, max_iter)
        
        row_pixels.append(int(255 * val / max_iter))
        
    return row_index, row_pixels

def process_pool_worker(task_queue, result_queue):
    while True:
        task = task_queue.get()
        if task is None: break
        idx, w, h, mi = task
        res = worker_calculation(idx, w, h, mi)
        result_queue.put(res)

def start_worker():
    num_cores = multiprocessing.cpu_count()
    print(f"Worker starting with {num_cores} cores...")
    
    task_queue = multiprocessing.Queue()
    result_queue = multiprocessing.Queue()
    
    processes = [multiprocessing.Process(target=process_pool_worker, args=(task_queue, result_queue)) for _ in range(num_cores)]
    for p in processes: p.start()

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((SERVER_HOST, SERVER_PORT))
        print("Connected to server.")

        while True:
            # Receive task chunk
            data = b""
            while True:
                packet = client_socket.recv(4096)
                if not packet: break
                data += packet
                if data.endswith(b"END_TASK"):
                    data = data[:-8]
                    break
            
            if not data: break
            
            task_info = pickle.loads(data)
            start, end = task_info['range']
            w, h, mi = task_info['width'], task_info['height'], task_info['max_iter']
            
            # Feed tasks to local pool
            num_tasks = end - start
            for i in range(start, min(end, h)):
                task_queue.put((i, w, h, mi))
            
            # Collect results for this chunk
            chunk_results = []
            for _ in range(num_tasks):
                chunk_results.append(result_queue.get())
            
            # Send results back
            client_socket.sendall(pickle.dumps(chunk_results) + b"DONE_RESULT")

    except Exception as e:
        print(f"Worker error: {e}")
    finally:
        for _ in range(num_cores): task_queue.put(None)
        for p in processes: p.join()
        client_socket.close()

if __name__ == "__main__":
    start_worker()
