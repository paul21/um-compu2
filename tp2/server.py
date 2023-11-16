import argparse
import http.server
import os
import cgi
from PIL import Image
import requests
import socket


class MyHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST'}
        )

        file_item = form['file']

        if not file_item.file:
            self.send_error(400, "Missing file")
            return

        file_path = self.write_file(file_item)
        if file_path:
            self.handle_image_conversion(file_path, file_item.filename)

    def write_file(self, file_item):
        file_path = os.path.join(os.getcwd(), file_item.filename)
        try:
            with open(file_path, 'wb') as output_file:
                output_file.write(file_item.file.read())
            return file_path
        except Exception as e:
            self.send_error(500, f"Error writing file: {str(e)}")
            return None

    def handle_image_conversion(self, image_path, filename):
        parent_conn, child_conn = os.pipe()

        pid = os.fork()
        if pid == 0:
            os.close(parent_conn)
            self.convert_to_grayscale(image_path, child_conn)
            os._exit(0)

        os.close(child_conn)
        self.wait_for_child_process(parent_conn, filename)

    def convert_to_grayscale(self, image_path, conn):
        try:
            with Image.open(image_path) as img:
                grayscale_img = img.convert('L')
                grayscale_path = f"{os.path.splitext(image_path)[0]}_grayscale.jpg"
                grayscale_img.save(grayscale_path)

            os.write(conn, grayscale_path.encode())
        except Exception as e:
            os.write(conn, b'Error')
        finally:
            os.close(conn)

    def wait_for_child_process(self, conn, filename):
        grayscale_path = os.read(conn, 1024).decode()
        os.close(conn)

        if grayscale_path == 'Error':
            self.send_error(500, "Error in image processing")
        else:
            self.send_to_resizing_server(grayscale_path, filename)

    def send_to_resizing_server(self, grayscale_path, filename):
        url = 'http://localhost:9000'
        scale_factor = 0.5

        try:
            with open(grayscale_path, 'rb') as file:
                files = {'file': file}
                data = {'scale_factor': str(scale_factor)}
                response = requests.post(url, files=files, data=data)

            self.send_response(200)
            self.send_header('Content-type', 'image/jpeg')
            self.end_headers()
            self.wfile.write(response.content)
        except IOError as e:
            self.send_error(500, f"Error opening file: {str(e)}")
        except requests.exceptions.RequestException as e:
            self.send_error(500, f"Error sending to resizing server: {str(e)}")
        finally:
            if os.path.exists(grayscale_path):
                os.remove(grayscale_path)
            if os.path.exists(os.path.join(os.getcwd(), filename)):
                os.remove(os.path.join(os.getcwd(), filename))

def run(server_class=http.server.HTTPServer, handler_class=MyHttpRequestHandler, addr='::', port=8000):
    server_address = (addr, port)
    httpd = server_class(server_address, handler_class)

    # Check if the address family is compatible with IPv6
    if addr and ':' in addr:
        httpd.socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        httpd.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        httpd.socket.bind(server_address)

    httpd.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Tp2 - procesa imagenes')
    parser.add_argument('-i', '--ip', type=str, required=True, help='Direccion de escucha')
    parser.add_argument('-p', '--port', type=int, required=True, help='Puerto de escucha')
    args = parser.parse_args()
    run(addr=args.ip, port=args.port)
