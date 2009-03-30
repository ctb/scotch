"""
HTTP forwarding proxy code, written as a WSGI application.

To start an actual proxy, mount this WSGI app as '/' on some port, e.g.

>> app = ProxyApp(verbosity=0)

>> from wsgiref.simple_server import WSGIServer, WSGIRequestHandler
>> server = WSGIServer(('', 8000), WSGIRequestHandler)
>> server.set_app(app)
>> while 1:
..    server.handle_request()

and then set your browser's proxy to that address.

"""

import urlparse, socket, urllib

BE_TOLERANT_OF_BROKEN_SERVERS=True

class ProxyApp:
    """
    WSGI transparent proxy application.
    """
    
    def __init__(self, verbosity=0):
        self.verbosity = verbosity

    def __call__(self, environ, start_response):
        """
        The WSGI worker function.
        """

        #
        # build the proxy request.
        #

        try:
            proxy_request = _ProxyRequest(environ)
        except Exception, e:
            response_headers = [('Content-type', 'text/plain')]
            start_response("400 %s" % (str(e),), response_headers)

            return []

        if self.verbosity >= 1:
            print '++', environ.get('PATH_INFO')
            _display_header_list('>>', proxy_request.headers)

        #
        # build a connection, send & receive
        #
        
        server_response = []
        proxy_request.connect()
        
        try:
            proxy_request.send()
            
            # ...get entire response.
            server_response = proxy_request.receive()
        finally:
            proxy_request.close()

        #
        # deal with the server response by forwarding it back up to the client.
        #

        (status, headers, body) = _parse_server_response(server_response)

        if self.verbosity >= 1:
            print '**', status
            _display_header_list('<<', headers)
            print ''
            
        start_response(status, headers)

        return [body]

class _ProxyRequest:
    """
    A class to take care of all of the ugliness of extracting information
    from the client that will then be passed on to the server.
    """
    TIMEOUT=10
    BLOCKSIZE=4096

    def __init__(self, environ):
        (path_info, protocol, method, query_string, body) = \
                    _extract_wsgi_in_headers(environ)
        
        client_headers = _extract_client_headers(environ)
        
        if body:
            client_headers.append(('CONTENT-LENGTH', len(body),))
        if environ.get('CONTENT_TYPE') and method == 'POST':
            client_headers.append(('CONTENT-TYPE', environ['CONTENT_TYPE']))

        # decompose PATH_INFO into a scheme, location, and path.  Note
        # that 'query' and 'fragment', the last two arguments, are not
        # included in the WSGI 'PATH_INFO' parameter, so we should ignore
        # them and use 'QUERY_STRING' from the environment instad.
        
        (scm, netloc, path, params, _, _) = urlparse.urlparse(path_info,'http')

        path = urllib.quote(path)       # treat e.g. spaces properly
        url = urlparse.urlunparse(('', '', path, params, query_string, ''))

        # error out if it's not 'http'.
        if scm != 'http' or not netloc:
            raise Exception("bad url %s" % (path_info,))

        self.method = method
        self.body = body
        self.headers = client_headers
        self.netloc = netloc
        self.url = url
        self.protocol = protocol

    def connect(self):
        """
        Connect to the given network location ('host:port')
        """
        netloc = self.netloc
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        i = netloc.find(':')

        if i >= 0:
            host, port = netloc[:i], int(netloc[i+1:])
        else:
            host, port = netloc, 80

        sock.settimeout(float(self.TIMEOUT))
        sock.connect((host, port))

        self.sock = sock

    def send(self):
        """
        Send an HTTP request on via the given socket.
        """
        sock = self.sock

        # build the request line
        request = '%s %s %s\r\n' % (self.method,
                                    self.url,
                                    self.protocol,)

        # build the header list
        for k, v in self.headers:
            request += "%s: %s\r\n" % (k, v,)

        # put together the rest of the request data
        request += "\r\n"
        if self.body is not None:
            request += self.body

        # send
        sock.send(request)

    def receive(self):
        """
        Get the entirety of an HTTP response from the given socket.

        Note: 'Connection: close' must have have been sent for this to work...
        """
        sock = self.sock
        response = []

        while 1:
            data = sock.recv(self.BLOCKSIZE)
            response.append(data)

            if len(data) == 0:
                break

        return "".join(response)

    def close(self):
        self.sock.close()

###

_client_omit = { 'proxy-connection' : 1 }

def _extract_client_headers(env):
    """
    Return a list of all of the client headers in the environment,
    as signalled by 'HTTP_' prefix.  Transform or omit appropriately.
    """
    headers = []
    for k, v in env.items():
        if k.upper().startswith('HTTP_'):
            k = k[5:]
            k = k.replace('_', '-')

            if _client_omit.has_key(k.lower()):
                continue
            
            headers.append((k, v))

    return headers

_hoppish = {
    'connection':1, 'keep-alive':1, 'proxy-authenticate':1,
    'proxy-authorization':1, 'te':1, 'trailers':1, 'transfer-encoding':1,
    'upgrade':1
    }

def _parse_server_response(response):
    """
    Parse the HTTP response into a status line, headers, and body.

    Remove "hoppish" headers that WSGI can't/won't handle.
    """
    try:
        status_line, response = response.split("\r\n", 1)
        headers, body = response.split("\r\n\r\n", 1)
    except ValueError:
        # some servers occasionally use '\n' instead of \r\n', the bastards.
        if BE_TOLERANT_OF_BROKEN_SERVERS:
            status_line, response = response.split("\n", 1)
            headers, body = response.split("\n\n", 1)
        else:
            raise

    status = status_line.split(' ', 1)[1]
    headers = headers.split("\r\n")
    headers = [ h.split(':', 1) for h in headers ]

    # remove hoppy headers
    new_headers = []
    for (a, b) in headers:
        if not _hoppish.has_key(a.lower()):
            new_headers.append((a, b[1:]))
    

    return status, new_headers, body

def _extract_wsgi_in_headers(environ):
    """
    Pull out & munge all of the interesting headers in the WSGI environment.
    """
    # URL
    path_info = environ['PATH_INFO']

    # downgrade the protocol to HTTP/1.0
    protocol = environ['SERVER_PROTOCOL']
    if protocol == 'HTTP/1.1':
        protocol = 'HTTP/1.0'

    # method (GET/POST/etc.)
    method = environ['REQUEST_METHOD']
    query_string = environ.get('QUERY_STRING', "")

    # read the input
    content_len = environ.get('CONTENT_LENGTH', 0)
    body = None
    if content_len:
        content_len = int(content_len)
        body = environ['wsgi.input'].read(content_len)

    return (path_info, protocol, method, query_string, body)

def _display_header_list(prefix, headers):
    """
    Display a list of headers in a canonical (lower case, sorted) format.
    """
    display_headers = [ (a.lower(),  b) for (a, b) in headers ]
    display_headers.sort()

    for k, v in display_headers:
        print '%s %s: %s' % (prefix, k, v)


