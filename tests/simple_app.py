"""
A very simple WSGI app for testing purposes.
"""

import cgi

_app_was_hit = False

def success():
    return _app_was_hit

def reset():
    global _app_was_hit
    _app_was_hit = False

def iter_app(environ, start_response):
    """Simplest possible application object"""
    status = '200 OK'
    response_headers = [('Content-type','text/plain')]
    start_response(status, response_headers)

    global _app_was_hit
    _app_was_hit = True
    
    return ['WSGI intercept successful!\n']

def write_app(environ, start_response):
    """Test the 'write_fn' legacy stuff."""
    status = '200 OK'
    response_headers = [('Content-type','text/plain')]
    write_fn = start_response(status, response_headers)

    global _app_was_hit
    _app_was_hit = True
    
    write_fn('WSGI intercept successful!\n')
    return []

def post_app(environ, start_response):
    """POST app."""
    status = '200 OK'
    response_headers = [('Content-type','text/html')]
    start_response(status, response_headers)

    global _app_was_hit
    _app_was_hit = True

    form = cgi.FieldStorage(fp=environ['wsgi.input'], environ=environ)

    if not form:
        return ["""\
<form method='POST'>
<input type='text' name='test'>
<input type='submit'>
</form>
"""]
    else:
        return [ 'VALUE WAS: ', form['test'].value ]
