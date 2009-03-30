import _testlib
_testlib._add_scotchdir_to_path()

import sys, os
sys.path.insert(0, '/u/t/dev/twill')

import simple_app
import twill
import scotch.recorder
from cStringIO import StringIO

def execute_twill_script(filename, inp=None, initial_url=None):
    if inp:
        inp_fp = StringIO(inp)
        old, sys.stdin = sys.stdin, inp_fp

    try:
        twill.execute_file(filename, initial_url=initial_url)
    finally:
        if inp:
            sys.stdin = old

class TestRecorderSimply:
    def test_basic(self):
        """
        Test the basic setup (iter_app, twill, and wsgi_intercept).
        """
        
        twill.add_wsgi_intercept('localhost', 80, lambda:simple_app.iter_app)
        try:
            twill.commands.go('http://localhost:80/')
            twill.commands.find('WSGI intercept')
            assert simple_app.success()
        finally:
            simple_app.reset()
            twill.remove_wsgi_intercept('localhost', 80)

    def test_passthru(self):
        """
        Make sure that the recorder actually calls the app correctly, etc.
        """
        
        recorder = scotch.recorder.Recorder(simple_app.iter_app)

        twill.add_wsgi_intercept('localhost', 80, lambda: recorder)
        try:
            twill.commands.go('http://localhost:80/')
            twill.commands.find('WSGI intercept')
            assert simple_app.success()
        finally:
            simple_app.reset()
            twill.remove_wsgi_intercept('localhost', 80)

    def test_refeed(self):
        """
        Try refeeding the content into the app.
        """
        
        recorder = scotch.recorder.Recorder(simple_app.iter_app)

        # first, record.
        twill.add_wsgi_intercept('localhost', 80, lambda: recorder)
        try:
            twill.commands.go('http://localhost:80/')
            output1 = twill.commands.show()
            assert simple_app.success()
        finally:
            simple_app.reset()
            twill.remove_wsgi_intercept('localhost', 80)

        # get the recorded bit.
        assert len(recorder.record_holder) == 1
        record = recorder.record_holder[0]

        try:
            response = record.refeed(simple_app.iter_app)
            assert simple_app.success()
            output2 = response.get_output()
            assert output1 == output2
        finally:
            simple_app.reset()

    def test_multirecord(self):
        """
        Test recording of multiple requests.
        """
        recorder = scotch.recorder.Recorder(simple_app.iter_app)

        # first, record.
        twill.add_wsgi_intercept('localhost', 80, lambda: recorder)
        try:
            twill.commands.go('http://localhost:80/')
            assert simple_app.success()
            simple_app.reset()
            
            twill.commands.go('./')
            assert simple_app.success()
        finally:
            simple_app.reset()
            twill.remove_wsgi_intercept('localhost', 80)

        # check the length of recorded bit.
        assert len(recorder.record_holder) == 2

    def test_multirefeed(self):
        """
        Test playback of multiple requests.
        """
        recorder = scotch.recorder.Recorder(simple_app.iter_app)

        # first, record.
        twill.add_wsgi_intercept('localhost', 80, lambda: recorder)
        try:
            twill.commands.go('http://localhost:80/')
            assert simple_app.success()
            simple_app.reset()
            
            twill.commands.go('./')
            assert simple_app.success()
        finally:
            simple_app.reset()
            twill.remove_wsgi_intercept('localhost', 80)

        # check the length of the recorded bit.
        assert len(recorder.record_holder) == 2

        # play it all back.
        try:
            assert not simple_app.success()
            for record in recorder.record_holder:
                record.refeed(simple_app.iter_app)
            assert simple_app.success()
        finally:
            simple_app.reset()

class TestRecorderWithWriteApp:
    def test_basic(self):
        """
        Test the basic setup (write_app, twill, and wsgi_intercept).
        """
        
        twill.add_wsgi_intercept('localhost', 80, lambda:simple_app.write_app)
        try:
            twill.commands.go('http://localhost:80/')
            twill.commands.find('WSGI intercept')
            assert simple_app.success()
        finally:
            simple_app.reset()
            twill.remove_wsgi_intercept('localhost', 80)

    def test_passthru(self):
        """
        Make sure that the recorder actually calls the app correctly, etc.
        """
        
        recorder = scotch.recorder.Recorder(simple_app.write_app)

        twill.add_wsgi_intercept('localhost', 80, lambda: recorder)
        try:
            twill.commands.go('http://localhost:80/')
            twill.commands.find('WSGI intercept')
            assert simple_app.success()
        finally:
            simple_app.reset()
            twill.remove_wsgi_intercept('localhost', 80)

    def test_refeed(self):
        """
        Try refeeding the content into the app.
        """
        
        recorder = scotch.recorder.Recorder(simple_app.write_app)

        # first, record.
        twill.add_wsgi_intercept('localhost', 80, lambda: recorder)
        try:
            twill.commands.go('http://localhost:80/')
            output1 = twill.commands.show()
            assert simple_app.success()
        finally:
            simple_app.reset()
            twill.remove_wsgi_intercept('localhost', 80)

        # get the recorded bit.
        assert len(recorder.record_holder) == 1
        record = recorder.record_holder[0]

        try:
            response = record.refeed(simple_app.write_app)
            assert simple_app.success()

            output2 = response.get_output()
            assert output1 == output2
        finally:
            simple_app.reset()

    def test_multirecord(self):
        """
        Test recording of multiple requests.
        """
        recorder = scotch.recorder.Recorder(simple_app.write_app)

        # first, record.
        twill.add_wsgi_intercept('localhost', 80, lambda: recorder)
        try:
            twill.commands.go('http://localhost:80/')
            assert simple_app.success()
            simple_app.reset()
            
            twill.commands.go('./')
            assert simple_app.success()
        finally:
            simple_app.reset()
            twill.remove_wsgi_intercept('localhost', 80)

        # check the length of the recorded bit.
        assert len(recorder.record_holder) == 2

    def test_multirefeed(self):
        """
        Test playback of multiple requests.
        """
        recorder = scotch.recorder.Recorder(simple_app.iter_app)

        # first, record.
        twill.add_wsgi_intercept('localhost', 80, lambda: recorder)
        try:
            twill.commands.go('http://localhost:80/')
            assert simple_app.success()
            simple_app.reset()
            
            twill.commands.go('./')
            assert simple_app.success()
        finally:
            simple_app.reset()
            twill.remove_wsgi_intercept('localhost', 80)

        # check the length of the recorded bit.
        assert len(recorder.record_holder) == 2

        # play it all back.
        try:
            assert not simple_app.success()
            for record in recorder.record_holder:
                record.refeed(simple_app.iter_app)
            assert simple_app.success()
        finally:
            simple_app.reset()

class TestPostRecording:
    def test_basic(self):
        """
        Test the basic setup (post_app, twill, and wsgi_intercept).
        """
        
        twill.add_wsgi_intercept('localhost', 80, lambda:simple_app.post_app)
        try:
            twill.commands.go('http://localhost:80/')
            assert simple_app.success()
            
            twill.commands.fv('1', 'test', 'howdy world')
            twill.commands.submit()
            twill.commands.find("VALUE WAS: howdy world")
        finally:
            simple_app.reset()
            twill.remove_wsgi_intercept('localhost', 80)
    

    def test_passthru(self):
        """
        Make sure that the recorder actually calls the app correctly, etc.
        """
        
        recorder = scotch.recorder.Recorder(simple_app.post_app)

        twill.add_wsgi_intercept('localhost', 80, lambda: recorder)
        try:
            twill.commands.go('http://localhost:80/')
            assert simple_app.success()
            
            twill.commands.fv('1', 'test', 'howdy world')
            twill.commands.submit()
            twill.commands.find("VALUE WAS: howdy world")
        finally:
            simple_app.reset()
            twill.remove_wsgi_intercept('localhost', 80)

    def test_multirecord(self):
        """
        Test recording of multiple requests.
        """
        recorder = scotch.recorder.Recorder(simple_app.post_app)

        # first, record.
        twill.add_wsgi_intercept('localhost', 80, lambda: recorder)
        try:
            twill.commands.go('http://localhost:80/')
            assert simple_app.success()
            simple_app.reset()
            
            twill.commands.fv('1', 'test', 'howdy world')
            twill.commands.submit()
            twill.commands.find("VALUE WAS: howdy world")
            assert simple_app.success()
        finally:
            simple_app.reset()
            twill.remove_wsgi_intercept('localhost', 80)

        # check the length of the recorded bit.
        assert len(recorder.record_holder) == 2

    def test_multirefeed(self):
        """
        Test playback of multiple requests.
        """
        recorder = scotch.recorder.Recorder(simple_app.post_app)

        # first, record.
        twill.add_wsgi_intercept('localhost', 80, lambda: recorder)
        try:
            twill.commands.go('http://localhost:80/')
            assert simple_app.success()
            simple_app.reset()
            
            twill.commands.fv('1', 'test', 'howdy world')
            twill.commands.submit()
            twill.commands.find("VALUE WAS: howdy world")
            assert simple_app.success()
        finally:
            simple_app.reset()
            twill.remove_wsgi_intercept('localhost', 80)

        # check the length of the recorded bit.
        assert len(recorder.record_holder) == 2

        # play it all back.
        try:
            assert not simple_app.success()
            for record in recorder.record_holder:
                record.refeed(simple_app.post_app)
            assert simple_app.success()
        finally:
            simple_app.reset()
