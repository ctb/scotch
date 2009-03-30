"""
Utility functions.

 * display_record(r) -- pretty-print the given record.
"""

from cStringIO import StringIO
import cgi

def filter_not_redirect(record):
    status = record.response.status
    status = int(status.split()[0])
    if status >= 300 and status < 400:
        return False
    return True

def filter_not_redirect_unless_submit(record):
    status = record.response.status
    status = int(status.split()[0])
    if status >= 300 and status < 400:
        # was it after a submit?
        if record.environ.get('QUERY_STRING', "") or \
           record.environ.get('REQUEST_METHOD', "") == 'POST' or \
           record.inp:
            return True
        
        return False
    return True

def filter_html_only(record):
    content_type = record.response.get_content_type()
    if content_type.lower().split(';')[0] == 'text/html':
        return True
    return False

def filter_no_images(record):
    content_type = record.response.get_content_type()
    if content_type.startswith('image/'):
        return False
    return True

def filter_no_javascript(record):
    content_type = record.response.get_content_type()
    if content_type.lower() in ('application/x-javascript', 'text/javascript'):
        return False
    return True

def filter_no_css(record):
    content_type = record.response.get_content_type()
    if content_type.lower().startswith('text/css'):
        return False
    return True

def filter_no_application(record):
    content_type = record.response.get_content_type()
    if content_type.lower().startswith('application/'):
        return False
    return True

def filter_only_primary_pages(record):
    return filter_not_redirect_unless_submit(record) and \
           filter_no_images(record) and \
           filter_no_application(record) and \
           filter_no_javascript(record) and \
           filter_no_css(record)

def _display_query_string(query_string):
    query_dict = cgi.parse_qs(query_string)

    for key, value in query_dict.items():
        print '\t %s: %s' % (key, str(value))

def _display_post_data(inp, environ):
    fp = StringIO(inp)
    form = cgi.FieldStorage(fp=fp, environ=environ)

    for key in form:
        print '\t %s:' % (key,),

        value_list = form[key]
        if isinstance(value_list, cgi.MiniFieldStorage): # single item
            print ' "%s"' % (value_list.value,)
        else:
            value_list = [ i.value for i in value_list ]
            print str(value_list)

def _display_headers(env):
    for k, v in env.items():
        if k.upper().startswith('HTTP_'):
            k = k[5:].lower()
            k = k.replace('_', '-')

            print '\t %s : %s' % (k, v,)


def display_record(record, filters=[filter_only_primary_pages]):
    """
    Pretty-print the record.

    >> for record in recorder.record_holder:
    ..    display_record(record)
    """
    for f in filters:
        if not f(record):
            return False
    
    import cgi

    environ = record.environ
    inp = record.inp

    path = environ.get('PATH_INFO')
    print 'REQUEST ==> %s' % (path,)

    ### display GET variables
    
    query_string = environ.get('QUERY_STRING', "")
    if query_string:
        print '(query string)'
        _display_query_string(query_string)

    ### display POST variables

    if inp:
        print '(post form)'
        _display_post_data(record.inp, environ)

    print ''
    print '++ RESPONSE: %s' % (record.response.status,)
    print '++ (%d bytes of content returned)' % (len(record.response.get_output()))
    print '++ (response is %s)' % (record.response.get_content_type(),)

    return True
