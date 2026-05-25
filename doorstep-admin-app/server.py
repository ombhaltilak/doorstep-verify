import http.server, ssl, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

cert = os.path.join(os.path.dirname(__file__), '..', 'doorstep-driver-app', 'cert.pem')
key  = os.path.join(os.path.dirname(__file__), '..', 'doorstep-driver-app', 'key.pem')

server = http.server.HTTPServer(('0.0.0.0', 4000), http.server.SimpleHTTPRequestHandler)
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain(cert, key)
server.socket = ctx.wrap_socket(server.socket, server_side=True)
print("Admin HTTPS server running on https://0.0.0.0:4000")
server.serve_forever()
