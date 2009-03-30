---

http_debugging_proxy.py.old is from Xavier Defrang,

    http://defrang.com/python

I've modified it to display headers in a more consistent way, for
my own debugging purposes.

---

UnchunkStream.py is from Webcleaner,

    http://sourceforge.net/projects/webcleaner

It deals with Transfer-encoding: chunked, which is HTTP/1.1-speak.  I
include it only for future reference; at some point I may need to deal
with chunked content and this is the nicest code I've seen.
