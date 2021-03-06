#!/usr/local/bin/python

__doc__ = """

	HTTP Debugging Proxy
	Modified by Xavier Defrang (http://defrang.com/)

	This small HTTP proxy prints the headers of all HTTP requests 
	and responses.  As it was useful for me, It may be useful for you
	as well...

	Built on the TinyHTTPProxy code base written by UZUKI Hisao.

	'This module implements GET, HEAD, POST, PUT and DELETE methods
	on BaseHTTPServer, and behaves as an HTTP proxy.  The CONNECT
	method is also implemented experimentally, but has not been
	tested yet.'

"""

__version__ = "0.1"


import BaseHTTPServer, select, signal, socket, SocketServer, urlparse
import re


class TimeoutError(Exception):
	pass

def SIGALRM_handler(sig, stack):
	raise TimeoutError()

signal.signal(signal.SIGALRM, SIGALRM_handler)


def connect_to(netloc, sock):		   # throws TimeoutError
	i = netloc.find(':')
	if i >= 0:
		host, port = netloc[:i], int(netloc[i+1:])
	else:
		host, port = netloc, 80
	#print "connect to", host, port
	signal.alarm(10)
	try:
		sock.connect((host, port))
	finally:
		signal.alarm(0)

class ProxyHandler (BaseHTTPServer.BaseHTTPRequestHandler):

	server_version = "TinyHTTPProxy/" + __version__

	def do_CONNECT(self):
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			try:
				connect_to(self.path, sock)
			except TimeoutError:
				self.send_error(504, "proxy has timed out")
				return
			self.log_request(200)
			self.wfile.write("%s %s %s\r\n" % (self.protocol_version, 200,
											   "Connection established"))
			self.wfile.write("Proxy-agent: %s\r\n" % self.version_string())
			self.wfile.write("\r\n")
			self._read_write(sock, 300)
		finally:
			#print "bye"
			sock.close()
			self.connection.close()

	def do_GET(self):
		(scm, netloc, path, params, query, fragment) = urlparse.urlparse(
			self.path, 'http')
		if scm != 'http' or fragment or not netloc:
			self.send_error(400, 'bad url %s' % self.path)
			return
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			try:
				connect_to(netloc, sock)
			except TimeoutError:
				self.send_error(504, "proxy has timed out")
				return
			self.log_request()
			str = '%s %s %s\r\n' % (
				self.command,
				urlparse.urlunparse(('', '', path, params, query, '')),
				self.request_version)
			sock.send(str)
			self.headers['Connection'] = 'close'
			del self.headers['Proxy-Connection']

			headers = self.headers.items()
			headers = [ (a.lower(), "%s" % (b,)) for (a, b) in headers ]
			headers.sort()
			
			for (h, v) in headers:
				str = '%s: %s\r\n' % (h, v)
				print ">>", str.strip()
				sock.send(str)
			sock.send('\r\n')
			self._read_write(sock)
		finally:
			#print "bye"
			sock.close()
			self.connection.close()

	def _read_write(self, sock, max_idling=20):
		rfile = self.rfile
		if hasattr(rfile, '_rbuf'):	 # on BeOS?
			data = rfile._rbuf
		else:
			if self.headers.has_key('Content-Length'):
				n = int(self.headers['Content-Length'])
				data = rfile.read(n)
			else:
				self.connection.setblocking(0)
				try: data = rfile.read()
				except IOError: data = ''
				self.connection.setblocking(1)
		rfile.close()
		if data:
			sock.send(data)
		iw = [self.connection, sock]
		count = 0
		self.headers_done = 0
		while 1:
			count += 1
			(ins, _, exs) = select.select(iw, [], iw, 3)
			if exs: break
			if ins:
				for i in ins:
					if i is sock:
						out = self.connection
					else:
						out = sock
					data = i.recv(8192)
					if data:
						self.dump_headers(data)
						out.send(data)
						count = 0
			else:
				print "idle", count
			if count == max_idling: break

	rx_hdr = re.compile("^([a-zA-Z\-0-9]+):\W+(.*)$")

	def dump_headers(self, data):

		if self.headers_done:
			return

		headers = []
		for line in data.split("\n"):

			line = line.strip()


			if not line:
				self.headers_done = 1
				break


			m = self.rx_hdr.match(line)
			
			if m:
				k, v = m.groups()
				headers.append((k.lower(), v))

		headers.sort()
		for k, v in headers:
			print "<< %s: %s" % (k, v)
		print ''


	do_HEAD = do_GET
	do_POST = do_GET
	do_PUT  = do_GET
	do_DELETE=do_GET

class ThreadingHTTPServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer): 
	pass

if __name__ == '__main__':
	BaseHTTPServer.test(ProxyHandler, ThreadingHTTPServer)
