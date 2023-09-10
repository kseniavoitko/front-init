from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import mimetypes
import pathlib
import socket
import logging
from threading import Thread
import json
from datetime import datetime

BASE_DIR = pathlib.Path()
DATA_JSON = BASE_DIR.joinpath('storage/data.json')
SERVER_IP = '127.0.0.1'
SERVER_PORT = 5000
BUFFER = 1024

def send_data_to_socket(data):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_socket:
        client_socket.sendto(data, (SERVER_IP, SERVER_PORT))

class HttpHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        data = self.rfile.read(int(self.headers["Content-Length"]))
        send_data_to_socket(data)
        self.send_response(302)
        self.send_header("Location", "/")
        self.end_headers()

    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)
        if pr_url.path == "/":
            self.send_html_file("index.html")
        elif pr_url.path == "/message":
            self.send_html_file("message.html")
        else:
            if pathlib.Path().joinpath(pr_url.path[1:]).exists():
                self.send_static()
            else:
                self.send_html_file("error.html", 404)

    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        with open(filename, "rb") as fd:
            self.wfile.write(fd.read())

    def send_static(self):
        self.send_response(200)
        mt = mimetypes.guess_type(self.path)
        if mt:
            self.send_header("Content-type", mt[0])
        else:
            self.send_header("Content-type", "text/plain")
        self.end_headers()
        with open(f".{self.path}", "rb") as file:
            self.wfile.write(file.read())


def run(server_class=HTTPServer, handler_class=HttpHandler):
    server_address = ("", 3000)
    http = server_class(server_address, handler_class)
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        http.server_close()


def save_data(data):
    data_parse = urllib.parse.unquote_plus(data.decode())
    with open(DATA_JSON, "r") as fd:
        unpacked_dict = json.load(fd)
    try:       
        data_dict = {
            key: value for key, value in [el.split("=") for el in data_parse.split("&")]
        }
        unpacked_dict[str(datetime.now())] = data_dict
        with open(DATA_JSON, 'w', encoding='utf-8') as fd:
            json.dump(unpacked_dict, fd, ensure_ascii=False)
    except ValueError as err:
        logging.error(f'Field parse data {data_parse} with error {err}')
    except OSError as err:
        logging.error(f'Field write data {data_parse} with error {err}')


def run_socket_server(ip, port):
    server = ip, port
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
        server_socket.bind(server)
        try:
            while True:
                data, address = server_socket.recvfrom(BUFFER)
                save_data(data)
        except KeyboardInterrupt:
            logging.info("Socket server stopped")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(threadName)s %(message)s")
    thread_server = Thread(target=run)
    thread_server.start()

    thread_socket = Thread(target=run_socket_server(SERVER_IP, SERVER_PORT))
    thread_socket.start()
