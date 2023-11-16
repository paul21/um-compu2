import os
import http.server
import cgi
from PIL import Image

class ResizeRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST'}
        )

        file_item = form.get('file')
        scale_factor = form.getvalue('scale_factor', None)

        if not file_item or not file_item.file or not scale_factor:
            self.send_error(400, "Missing file or scale factor")
            return

        try:
            scale_factor = float(scale_factor)
        except ValueError:
            self.send_error(400, "Invalid scale factor")
            return

        file_path = self.write_file(file_item)
        if file_path:
            self.resize_and_send_image(file_path, scale_factor)

    def write_file(self, file_item):
        file_path = os.path.join(os.getcwd(), file_item.filename)
        try:
            with open(file_path, 'wb') as output_file:
                output_file.write(file_item.file.read())
            return file_path
        except Exception as e:
            self.send_error(500, f"Error writing file: {str(e)}")
            return None

    def resize_and_send_image(self, image_path, scale_factor):
        try:
            with Image.open(image_path) as img:
                new_width = int(img.width * scale_factor)
                new_height = int(img.height * scale_factor)
                resized_img = img.resize((new_width, new_height))
                resized_path = f"{os.path.splitext(image_path)[0]}_resized.jpg"
                resized_img.save(resized_path)

            self.send_response(200)
            self.send_header('Content-type', 'image/jpeg')
            self.end_headers()
            with open(resized_path, 'rb') as file:
                self.wfile.write(file.read())
        except Exception as e:
            self.send_error(500, f"Error resizing image: {str(e)}")
        finally:
            if os.path.exists(resized_path):
                os.remove(resized_path)
            if os.path.exists(image_path):
                os.remove(image_path)

def run(addr="localhost", port=9000):
    server_address = (addr, port)
    httpd = http.server.HTTPServer(server_address, ResizeRequestHandler)
    httpd.serve_forever()

if __name__ == "__main__":
    run()
