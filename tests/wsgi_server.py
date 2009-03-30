#!/usr/bin/env python
"""
A WSGI wrapper for Quixote applications, and a standalone interface to two HTTP
servers.

To run the Quixote demos or your own application using the built-in
synchronous HTTP server:

    wsgi_server.py
    wsgi_server.py --factory=quixote.demo.altdemo.create_publisher
    wsgi_server.py --factory=quixote.demo.mini_demo.create_publisher
    wsgi_server.py --help              # Shows all options and defaults.

and point your browser to http://localhost:8080/ .  The --factory option names
a function that returns a Publisher object configured for the desired
application.  

To use a multi-threaded HTTP server instead, add the --thread option.  The
threaded server is from the 'wsgiutils' package, which is available at 
%s .

To use your Quixote application with any WSGI server or middleware:

    from quixote.server.wsgi_server import QWIP
    wsgi_application = QWIP(publisher)
    # 'publisher' is a quixote.publish.Publisher instance or compatible.

MULTITHREADING ISSUES:
- The default Quixote Publisher is not thread safe.
- To make a thread safe publisher, use ThreadedPublisher or
  make_publisher_thread_safe() below.  See doc/multi-threaded.txt .
- QWIP will refuse to connect a multi-threaded server to an unsafe publisher.
  It assumes safe publishers have an .is_thread_safe attribute that is true.
  The default Quixote Publisher does not have this attribute, so is presumed
  unsafe.  
- Even if the publisher is thread safe, your application code or its dependent
  modules may not be.  
- Your create_publisher function has the best knowledge of whether the
  publisher-application combination it's returning is thread safe.  So please
  set the publisher.is_thread_safe instance variable to the correct value
  before returning, because the default value may be wrong.
- ALL MULTITHREADING SUPPORT IN THIS MODULE IS EXPERIMENTAL AND SHOULD NOT BE
  USED IN A PRODUCTION ENVIRONMENT WITHOUT THOROUGH TESTING!!!

The synchronous server (WSGI_HTTPRequestHandler) is also experimental.

Author: Mike Orr <mso@oz.net>.  
Based on an earlier version of QWIP by Titus Brown <titus@caltech.edu>.
Last updated 2005-05-18.
"""
import BaseHTTPServer, sys, thread, traceback, urlparse
from quixote.http_request import HTTPRequest
from quixote.publish import Publisher
from quixote.server.util import get_server_parser
from quixote.util import import_object

WSGIUTILS_URL = "http://www.owlfish.com/software/wsgiutils/"
__doc__ %= WSGIUTILS_URL

MAIN_DOC = """\
Publish a Quixote application using QWIP/WSGI and a synchronous or 
multi-threaded HTTP server."""

THREAD_HELP = """\
Use a multi-threaded server and hack the Publisher to make it thread safe.
Depends on 'wsgiutils' package from %s .""" % WSGIUTILS_URL

###### QWIP: WSGI COMPATIBILITY WRAPPER FOR QUIXOTE #####################
class QWIP:
    """I make a Quixote Publisher object look like a WSGI application."""
    request_class = HTTPRequest

    def __init__(self, publisher):
        self.publisher = publisher
    
    def __call__(self, env, start_response):
        """I am called for each request."""
        if env.get('wsgi.multithread') and not \
            getattr(self.publisher, 'is_thread_safe', False):
            reason =  "%r is not thread safe" % self.publisher
            raise AssertionError(reason)
        if not env.has_key('REQUEST_URI'):
            env['REQUEST_URI'] = env['SCRIPT_NAME'] + env['PATH_INFO']
        input = env['wsgi.input']
        request = self.request_class(input, env)
        response = self.publisher.process_request(request)
        status = "%03d %s" % (response.status_code, response.reason_phrase)
        headers = response.generate_headers()
        start_response(status, headers)
        return response.generate_body_chunks()  # Iterable object.

###### WSGI REQUEST HANDLER FOR BaseHTTPServer ##########################
class WSGI_RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """Based on PEP 333 and Colin Stewart's WSGIHandler in WSGI Utils.

       Assumes self.server.application is a WSGI application.

       Doesn't catch all possible exceptions; e.g., misformed headers.
    """
    def do_GET(self):
        protocol, host, path, parameters, query, fragment = \
            urlparse.urlparse("http://DUMMY" + self.path)
        env = {
            'wsgi.version': (1,0),
            'wsgi.url_scheme': 'http',
            'wsgi.input': self.rfile,
            'wsgi.errors': sys.stderr,
            'wsgi.multithread': False,
            'wsgi.multiprocess': False,
            'wsgi.run_once': False,
            'REQUEST_METHOD': self.command,
            'SCRIPT_NAME': '',
            'PATH_INFO': path,
            'QUERY_STRING': query,
            'CONTENT_TYPE': self.headers.get('Content-Type', ''),
            'CONTENT_LENGTH': self.headers.get('Content-Length', ''),
            'REMOTE_ADDR': self.client_address[0],
            'SERVER_NAME': self.server.server_address [0],
            'SERVER_PORT': str(self.server.server_address [1]),
            'SERVER_PROTOCOL': self.request_version,
            }
        for header, value in self.headers.items():
            header = 'HTTP_%s' % header.replace('-', '_').upper()
            env[header] = value

        self.status_code = None
        self.status_message = None
        self.headers = []
        self.headers_sent = False

        try:
            result = self.server.application(env, self.start_response)
            try:
                for data in result:
                    if data:               # Delay sending headers until first
                        self.write(data)   # non-empty body element appears.
                if not self.headers_sent:
                    self.write('')         # If no body, send headers now.
            finally:
                if hasattr(result, 'close'):
                    result.close()
        except:
            self.log_exception(sys.exc_info())

    do_POST = do_GET

    def write(self, data):
        assert self.headers, "write() before start_response()!"
        if not self.headers_sent:
            self.send_response(self.status_code, self.status_message)
            for header, value in self.headers:
                self.send_header(header, value)
            self.end_headers()
            self.headers_sent = True
        self.wfile.write(data)
            
    def start_response(self, status, headers_received, exc_info=None):
        if exc_info:
            self.log_exception(exc_info)
            exc_info = None  # Avoid dangling circular reference.
        assert not self.headers, "Headers already set!"
        status_code, status_message = status.split(' ', 1)
        self.status_code = int(status_code)  
        self.status_message = status_message
        self.headers = headers_received
        return self.write

    def log_exception(self, exc_info):
        lines = traceback.format_exception(*exc_info)
        message = ''.join(lines)
        self.log_error(message)

###### THREAD SUPPORT ###################################################
# Internal functions that will be used as methods.
def _set_request(self, request):
    self._request_dict[thread.get_ident()] = request

def _clear_request(self):
    import thread
    try:
        del self._request_dict[thread.get_ident()]
    except KeyError:
        pass

def get_request(self):
    return self._request_dict.get(thread.get_ident())

# Public classes and functions.
class ThreadedPublisher(Publisher):
    """A thread-safe version of Quixote's Publisher."""
    is_thread_safe = True
    _set_request = _set_request
    _clear_request = _clear_request
    get_request = get_request

    def __init__(self, *args, **kw):
        Publisher.__init__(self, *args, **kw)
        self._request_dict = {}

def make_publisher_thread_safe(publisher):
    """Modify an existing Publisher instance to make it compatible with
       multithreaded servers.
       Side effects: replaces several methods in the instance's class.
    """
    if getattr(publisher, 'is_thread_safe', False):
        return
    publisher._request_dict = {}
    publisher.__class__._set_request = _set_request
    publisher.__class__._clear_request = _clear_request
    publisher.__class__.get_request = get_request
    publisher.__class__.is_thread_safe = True
    publisher.__class__._modified_by__make_publisher_web_safe = True

###### LAUNCH A SERVER ##################################################
def run(create_publisher, host='', port=80):
    """Launch the synchronous HTTP server."""
    publisher = create_publisher()
    httpd = BaseHTTPServer.HTTPServer((host, port), WSGI_RequestHandler)
    httpd.application = QWIP(publisher)
    httpd.serve_forever()

def run_multithreaded(create_publisher, host='', port=80):
    """Launch a multithreaded HTTP server."""
    from wsgiutils.wsgiServer import WSGIServer
    publisher = create_publisher()
    make_publisher_thread_safe(publisher)
    app_map = {'': QWIP(publisher)}
    httpd = WSGIServer((host, port), app_map, serveFiles=False)
    httpd.serve_forever()

###### MAIN ROUTINE #####################################################
def main():
    parser = get_server_parser(MAIN_DOC)
    parser.add_option('--thread', dest='thread', action='store_true',
        help=THREAD_HELP)
    options = parser.parse_args()[0]
    factory = import_object(options.factory)
    if options.thread:
        run_multithreaded(factory, host=options.host, port=options.port)
    else:
        run(factory, host=options.host, port=options.port)

if __name__ == '__main__':  main()
