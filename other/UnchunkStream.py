# -*- coding: iso-8859-1 -*-
"""encoding_chunked, amitp@cs.stanford.edu, March 2000
Deal with Transfer-encoding: chunked [HTTP/1.1]"""

__version__ = "$Revision: 1.29 $"[11:-2]
__date__    = "$Date: 2004/05/21 13:46:34 $"[7:-2]

import re
import wc


match_bytes = re.compile(r"^(?i)(?P<bytes>[0-9a-f]+)(;.+)?$").search


class UnchunkStream (object):
    """stream filter for chunked transfer encoding
    States:
     - bytes_remaining is None:
       we're in the "need chunk size" state
     - bytes_remaining is not None:
       we're reading up to bytes_remaining elements of data
    """
    def __init__ (self):
        """initialize internal buffers and flags"""
        self.buf = ''
        self.bytes_remaining = None
        self.closed = False


    def __repr__ (self):
        """representation of stream filter state"""
        return '<%s closed=%s buflen=%d bytes_remaining=%s>'%\
      ('unchunk', self.closed, len(self.buf), self.bytes_remaining)


    def decode (self, s):
        """unchunk given data s"""
        wc.log.debug(wc.LOG_PROXY, "chunked data %r", s)
        self.buf += s
        s = ''

        while self.buf and not self.closed:
            # Keep looking for alternating chunk lengths and chunk content
            if self.bytes_remaining is None:
                # We want to find a chunk length
                i = self.buf.find('\n')
                if i >= 0:
                    # We have a line; let's hope it's a chunk length
                    line = self.buf[:i].strip()
                    # Remove this line from the buffer
                    self.buf = self.buf[i+1:]
                    if line:
                        # NOTE: chunklen can be followed by ";.*"
                        mo = match_bytes(line)
                        if mo:
                            # chunklen is hex
                            self.bytes_remaining = int(mo.group('bytes'), 16)
                        else:
                            wc.log.warn(wc.LOG_PROXY, "invalid chunk size %r", line)
                            self.bytes_remaining = 0
                        #print 'chunk len:', self.bytes_remaining
                        if self.bytes_remaining == 0:
                            # End of stream
                            self.closed = True
                            # XXX: at this point, we should read
                            # footers until we get to a blank line
                else:
                    break
            if self.bytes_remaining is not None:
                # We know how many bytes we need
                data = self.buf[:self.bytes_remaining]
                s += data
                self.buf = self.buf[self.bytes_remaining:]
                self.bytes_remaining -= len(data)
                assert self.bytes_remaining >= 0
                if self.bytes_remaining == 0:
                    # We reached the end of the chunk
                    self.bytes_remaining = None
        wc.log.debug(wc.LOG_PROXY, "decoded chunk %r", s)
        return s


    def flush (self):
        """flush internal buffers and return flushed data"""
        s = self.buf.strip()
        self.buf = ''
        return s
