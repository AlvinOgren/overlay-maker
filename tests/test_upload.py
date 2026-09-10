"""Exercise real HTTP handlers in memory, without starting a preview server."""
import io
import json
import mimetypes
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import quote
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import Handler,TOKEN,activities
from test_core import fixture

class Connection:
    def __init__(self,request): self.input=io.BytesIO(request); self.output=bytearray()
    def makefile(self,*args): return self.input
    def sendall(self,data): self.output.extend(data)

def request(path,body=None,filename='test.gpx'):
    raw=f'{"POST" if body is not None else "GET"} {path} HTTP/1.0\r\nHost: 127.0.0.1:8123\r\n'
    if body is not None: raw+=f'Content-Length: {len(body)}\r\nX-Overlay-Token: {TOKEN}\r\nX-Filename: {quote(filename)}\r\n'
    connection=Connection(raw.encode()+b'\r\n'+(body or b''))
    Handler(connection,('127.0.0.1',1),SimpleNamespace(server_port=8123))
    headers,payload=bytes(connection.output).split(b'\r\n\r\n',1)
    return headers.decode(),payload

class UploadTests(unittest.TestCase):
    def tearDown(self): activities.clear()
    def test_windows_mime_association_cannot_disable_javascript(self):
        previous=mimetypes.guess_type('app.js')[0]
        mimetypes.add_type('text/plain','.js')
        try:
            headers,body=request('/app.js')
            self.assertIn('200 OK',headers)
            self.assertIn('Content-Type: text/javascript; charset=utf-8',headers)
            self.assertIn(b'async function upload',body)
        finally:
            if previous: mimetypes.add_type(previous,'.js')
    def test_upload_unicode_filename_and_preview(self):
        headers,body=request('/api/activity',fixture(),'Björsäter_z2.gpx')
        self.assertIn('200 OK',headers)
        activity=json.loads(body)
        self.assertEqual(activity['name'],'Björsäter_z2.gpx')
        self.assertEqual(activity['count'],4)
        self.assertTrue(activity['metrics']['power']['available'])
        cfg={'activity':activity['id'],'metrics':['power','cad','elapsed'],'start':0,'end':10,'elapsed':.5}
        headers,png=request('/api/preview',json.dumps(cfg).encode())
        self.assertIn('200 OK',headers)
        self.assertTrue(png.startswith(b'\x89PNG'))
    def test_bad_file_reports_error_and_retry_works(self):
        headers,body=request('/api/activity',b'not xml')
        self.assertIn('400 Bad Request',headers)
        self.assertIn('GPX',json.loads(body)['error'])
        headers,body=request('/api/activity',fixture())
        self.assertIn('200 OK',headers)
    def test_actual_supplied_gpx_when_available(self):
        folder=Path('/workspace/scratch/3e73a603dcdd/upload')
        if not (folder/'Björsäter_z2.gpx').exists(): self.skipTest('User GPX files are intentionally not bundled.')
        for filename,count,power in [('Björsäter_z2.gpx',9561,True),('KvällsMTB.gpx',6451,False)]:
            headers,body=request('/api/activity',(folder/filename).read_bytes(),filename)
            self.assertIn('200 OK',headers)
            activity=json.loads(body)
            self.assertEqual(activity['count'],count)
            self.assertEqual(activity['metrics']['power']['available'],power)

if __name__=='__main__': unittest.main()
