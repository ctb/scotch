#__all__ = ['load_recording']

import scotch.utils

record_holder = None
record_index = None

def load_recording(filename):
    global record_holder
    global record_index
    
    from cPickle import load
    record_holder = load(open(filename))

    print 'loaded %d records' % (len(record_holder),)
    record_index = 0

def record(n):
    global record_index
    assert record_holder is not None

    record_index = int(n - 1)
    record_holder[record_index]         # will throw an error if out of bounds

def next_record(condition='only_primary_pages'):
    fn = None
    if condition:
        fn = 'filter_%s' % (condition,)
        fn = getattr(scotch.utils, fn)

    global record_index
    i = record_index + 1
    while i < len(record_holder) and not fn(record_holder[i]):
        i += 1

    if i == len(record_holder):
        print 'no more (significant) records'
    else:
        print 'at record', i
        
    record_index = i

def prev_record(condition='only_primary_pages'):
    fn = None
    if condition:
        fn = 'filter_%s' % (condition,)
        fn = getattr(scotch.utils, fn)

    global record_index
    i = record_index - 1
    while i >= 0 and not fn(record_holder[i]):
        i -= 1

    if i == 0:
        print 'no previous (significant) records'
    else:
        print 'at record', i
        
    record_index = i

def show_record(*what):
    record = record_holder[record_index]

    show_default = False
    if not what or '+' in what:
        show_default = True

    print '\n** Displaying record %d:' % (record_index,)
    if show_default or 'url' in what:
        print '   URL:', record.environ.get('PATH_INFO')
    if show_default or 'status' in what:
        print '   Status:', record.response.status
    if 'headers' in what:
        print '   Headers:'
        scotch.utils._display_headers(record.environ)
    if show_default or 'formdata' in what:
        query_string = record.environ.get('QUERY_STRING', '')
        if query_string:
            print '   Query string:'
            print scotch.utils
            scotch.utils._display_query_string(query_string)

        if record.inp:
            print '   POST data:'
            scotch.utils._display_post_data(record.inp, record.environ)
    if 'content_type' in what:
        content = record.response.get_output()
        typ = record.response.get_content_type()
        print '   Returned content: %d bytes of %s' % (len(content), typ)
    if 'content' in what:
        content = record.response.get_output()
        typ = record.response.get_content_type()
        print '   Returned content (%d bytes, %s)' % (len(content), typ)
        print '==='
        print content
        print '==='

    print ''
