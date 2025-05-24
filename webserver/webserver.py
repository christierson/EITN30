import http.server
import socketserver
import random
import time
import logging
from urllib.parse import urlparse, parse_qs

PORT = 8080

class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        start_time = time.time()
        
        # Parse the size from the URL
        parsed_path = urlparse(self.path)
        size_str = parsed_path.path.lstrip('/')
        if size_str.isdigit():
            size = int(size_str)
        else:
            self.send_error(400, "Bad Request: Size must be an integer")
            return
        
        # Generate random bytes
        response_data = random.randbytes(size)
        
        # Send response
        self.send_response(200)
        self.send_header('Content-type', 'application/octet-stream')
        self.send_header('Content-Length', str(size))
        self.end_headers()
        self.wfile.write(response_data)
        
        # Log the request details
        duration = time.time() - start_time
        client_ip = self.client_address[0]
        log_message = (f"Request: {self.path} | "
                       f"Duration: {duration:.6f} sec | "
                       f"Payload: {size} bytes | "
                       f"By: {client_ip}")
        print(log_message)
        
        # Also log using logging module
        logging.info(log_message)

def run(server_class=http.server.HTTPServer, handler_class=RequestHandler):
    logging.basicConfig(filename='server.log', level=logging.INFO)
    server_address = ('', PORT)
    httpd = server_class(server_address, handler_class)
    print(f"Starting server on port {PORT}")
    logging.info(f"Starting server on port {PORT}")
    httpd.serve_forever()

if __name__ == '__main__':
    run()
