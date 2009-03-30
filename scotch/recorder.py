"""
A general-purpose WSGI middleware object for recording WSGI I/O.

Briefly,

>>   recorder_app = Recorder(wsgi_app)

will instantiate a recorder for all I/O from 'wsgi_app', and

>>   records = recorder_app.record_holder
..   for record in records:
..      utils.display_record(record)

will pretty-print all of the I/O.

You can also do:

>>   for record in records:
..      record.refeed(wsgi_app)

to replay the recorded session.
"""

from cStringIO import StringIO
from cPickle import load, dump

from scotch import utils

class Response:
    """
    Keep track of a WSGI response: status, headers, content, and error output.
    """
    
    def __init__(self):
        self.status = self.headers = self.content_list = self.errout = None

    def get_output(self):
        return "".join(self.content_list)

    def get_content_type(self):
        for (h, v) in self.headers:
            if h.lower() == 'content-type':
                return v

        return None

    def get_status_code(self):
        status_code = self.status.split()[0]
        return int(status_code)

    def is_ok(self):
        status_code = self.get_status_code()
        return (status_code == 200)

    def is_redirect(self):
        status_code = self.get_status_code()
        return (status_code >= 301 and status_code <= 303)

    def is_failed(self):
        status_code = self.get_status_code()
        return (status_code >= 400)

class Record:
    """
    Keep track of a WSGI transaction: environment & input data, + response
    object.
    """
    
    def __init__(self, environ, inp, response):
        """
        Create a record object, with the WSGI environment, any POST-ed
        input, and the response object (of type Response).
        """
        self.environ = environ
        self.inp = str(inp)
        
        assert isinstance(response, Response)
        self.response = response

    def is_post(self):
        method = self.environ.get('REQUEST_METHOD', '')
        if method.lower() is 'post':
            return True

    def is_get(self):
        method = self.environ.get('REQUEST_METHOD', '')
        if method.lower() is 'get':
            return True

    def has_input(self):
        return len(self.inp)

    def refeed(self, app):
        """
        Feed this response back into the application; return a new
        response object.
        """

        # first, construct a new environ dictionary.
        new_environ = _build_new_environ(self.inp, self.environ)

        # now, build the 'start_response' function that will record
        # the status, headers, and 'write'-based output.
        
        write_fp = StringIO()
        response = Response()
        
        def start_response(status, headers):
            assert response.status is None
            response.status = status
            response.headers = headers
            
            return write_fp.write

        # gather the results from the generator returned by the app
        results = []
        for data in app(new_environ, start_response):
            results.append(data)

        # stick the results in the response...
        response.content_list = results

        # ...and add back in any output from the 'write' fn, which
        # goes *before* the rest of the response.
        
        write_str = write_fp.getvalue()
        if write_str:
            response.content_list.insert(0, write_str)

        # return a Response object containing the entire response.
        return response

class RecordHolder:
    """
    Keep track of multiple records.

    This class keeps an in-memory list of records, but it can be subclassed
    to provide disk-based persistence easily.
    """
    def __init__(self):
        self.records = []
        
    def add_record(self, r):
        assert isinstance(r, Record)
        self.records.append(r)

    def __len__(self):
        return len(self.records)

    def __getitem__(self, i):
        return self.records[i]
        
class Recorder:
    """
    Record WSGI transactions.
    """
    
    def __init__(self, app, record_holder=None, verbosity=0):
        """
        Create a WSGI recorder middleware object.
        """
        
        self.app = app
        if record_holder is None:
            record_holder = RecordHolder()
        self.record_holder = record_holder
        self.verbosity = verbosity

    def load(self, fp):
        assert len(self.record_holder) == 0
        
        record_holder = load(fp)
        assert isinstance(record_holder, RecordHolder)
        
        self.record_holder = record_holder

    def save(self, fp):
        dump(self.record_holder, fp)

    def __call__(self, orig_environ, orig_start_response):
        """
        The WSGI worker function, run for each WSGI transaction.
        """

        #
        # first, deal with the input environment by grabbing all of the
        # input data & the original error fp; then, duplicate the environment.
        #
        
        orig_inp = _extract_input(orig_environ)
        orig_errfp = orig_environ['wsgi.errors']
        
        environ = _build_new_environ(orig_inp, orig_environ)

        #
        # build a Response object, and a 'results' list, to hold the response.
        # Also build a wrapper 'start_response' function that records the
        # input/output given to this function.
        #
        
        response = Response()
        results = []

        def start_response(status, headers):
            assert response.status is None
            response.status = status
            response.headers = headers

            write_fn = orig_start_response(status, headers)
            def my_write_fn(s):
                results.append(s)
                write_fn(s)
            return my_write_fn

        #
        # run the application, & grab the iterator/generator output.
        #

        generator = self.app(environ, start_response)

        for data in generator:
            results.append(data)
            yield data
            
        response.content_list = results

        # grab the errors, too, and pass them back up the chain.
        errout = environ['wsgi.errors'].getvalue()
        orig_errfp.write(errout)

        # save the error output
        response.errout = errout

        # save this record.
        record = Record(_cleanse_environ(orig_environ), orig_inp, response)
        self.record_holder.add_record(record)

        if self.verbosity >= 1:
            if utils.display_record(record):
                print '(# %d)' % (len(self.record_holder),)

def _build_new_environ(inp, orig_environ):
    """
    Build a new 'environ' dictionary with given input & a clean error fp.
    'orig_environ' is not modified.
    """
    env = dict(orig_environ)
    env['wsgi.input'] = StringIO(inp)
    env['wsgi.errors'] = StringIO()

    return env

def _cleanse_environ(environ):
    """
    Build a copy of the given WSGI environment, and cleanse it of
    the tricky-to-pickle members.
    """
    env = dict(environ)
    if env.has_key('wsgi.input'):
        del env['wsgi.input']

    if env.has_key('wsgi.errors'):
        del env['wsgi.errors']
        
    return env

def _extract_input(environ):
    """
    Return the input, read from environ['wsgi.input'].
    """
    content_len = environ.get('CONTENT_LENGTH', 0)
    orig_inp = ""
    if content_len:
        content_len = int(content_len)
        orig_inp = environ['wsgi.input'].read(content_len)

    return orig_inp
