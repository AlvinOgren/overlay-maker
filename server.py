"""Local-only HTTP application. Run through START.bat or bootstrap.py."""
import io
import json
import secrets
import threading
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, unquote
from gpx import MAX_BYTES, parse_gpx, public_activity
from rendering import ROOT, validate, render
from jobs import Job, formats

TOKEN=secrets.token_urlsafe(32)
activities={}; jobs={}; lock=threading.Lock(); available=[]
STATIC_TYPES={'.html':'text/html; charset=utf-8', '.js':'text/javascript; charset=utf-8',
              '.css':'text/css; charset=utf-8', '.svg':'image/svg+xml', '.png':'image/png'}

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def send(self,status,data,ctype='application/json',headers=None):
        if not isinstance(data,bytes): data=json.dumps(data,ensure_ascii=False).encode()
        self.send_response(status); self.send_header('Content-Type',ctype); self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; img-src 'self' blob:; style-src 'self' 'unsafe-inline'; object-src 'none'; frame-ancestors 'none'")
        for k,v in (headers or {}).items(): self.send_header(k,v)
        self.end_headers()
        try: self.wfile.write(data)
        except (BrokenPipeError,ConnectionResetError): pass
    def trusted(self,post=False):
        hosts={f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
        if self.headers.get('Host') not in hosts: return False
        origin=self.headers.get('Origin')
        if origin and origin not in {'http://'+host for host in hosts}: return False
        return not post or secrets.compare_digest(self.headers.get('X-Overlay-Token',''),TOKEN)
    def do_GET(self):
        if not self.trusted(): return self.send(403,{'error':'Endast lokal åtkomst.'})
        path=urlparse(self.path).path
        if path=='/api/health': return self.send(200,{'formats':available})
        if path.startswith('/api/jobs/'):
            job=jobs.get(path.rsplit('/',1)[-1]); return self.send(200,job.public()) if job else self.send(404,{'error':'Exporten finns inte.'})
        if path.startswith('/download/'):
            job=jobs.get(path.rsplit('/',1)[-1])
            if not job or job.state!='done': return self.send(404,{'error':'Videon är inte klar.'})
            self.send_response(200); self.send_header('Content-Type','video/quicktime' if job.path.suffix=='.mov' else 'video/webm'); self.send_header('Content-Length',str(job.path.stat().st_size)); self.send_header('Content-Disposition','attachment; filename="'+job.path.name+'"'); self.end_headers()
            try:
                with job.path.open('rb') as f:
                    while chunk:=f.read(1024*1024): self.wfile.write(chunk)
            except (BrokenPipeError,ConnectionResetError): pass
            return
        target=(ROOT/'dist'/('index.html' if path=='/' else unquote(path).lstrip('/'))).resolve()
        if not target.is_relative_to(ROOT/'dist') or not target.is_file(): return self.send(404,{'error':'Sidan finns inte.'})
        data=target.read_bytes()
        if target.name=='index.html': data=data.replace(b'__API_TOKEN__',TOKEN.encode())
        # Windows registry file associations must not decide executable web MIME types.
        self.send(200,data,STATIC_TYPES.get(target.suffix.lower(),'application/octet-stream'))
    def do_POST(self):
        if not self.trusted(True): return self.send(403,{'error':'Ladda om sidan för att ansluta lokalt.'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=MAX_BYTES: raise ValueError('Tom eller för stor förfrågan (max 20 MB).')
            data=self.rfile.read(length); path=urlparse(self.path).path
            if path=='/api/activity':
                activity=parse_gpx(data,unquote(self.headers.get('X-Filename','aktivitet.gpx'))); identifier=uuid.uuid4().hex
                with lock:
                    while len(activities)>=3: activities.pop(next(iter(activities)))
                    activities[identifier]=activity
                return self.send(200,{'id':identifier,**public_activity(activity)})
            body=json.loads(data)
            if path.endswith('/cancel'):
                job=jobs.get(path.split('/')[-2])
                if not job: raise ValueError('Exporten finns inte.')
                job.cancel(); return self.send(200,job.public())
            activity=activities.get(body.get('activity'))
            if not activity: raise ValueError('Ladda upp aktiviteten igen.')
            cfg=validate(activity,body)
            if path=='/api/preview':
                elapsed=float(body.get('elapsed',0))
                if not 0<=elapsed<=activity['duration']: raise ValueError('Ogiltig tid.')
                buffer=io.BytesIO(); render(activity,cfg,elapsed,True).save(buffer,format='PNG'); return self.send(200,buffer.getvalue(),'image/png')
            if path=='/api/export':
                if cfg['format'] not in available: raise ValueError('Videokodaren finns inte. Kör START.bat för att installera beroenden.')
                with lock:
                    if any(j.state=='running' for j in jobs.values()): raise ValueError('Vänta på eller avbryt pågående export.')
                    job=Job(activity,cfg); jobs[job.id]=job
                    threading.Thread(target=job.run,daemon=True).start()
                return self.send(200,job.public())
            self.send(404,{'error':'Okänd funktion.'})
        except (ValueError,TypeError,KeyError,OverflowError) as error: self.send(400,{'error':str(error)})
        except Exception: self.send(500,{'error':'Ett lokalt fel uppstod. Starta om appen och försök igen.'})

def main():
    global available
    available=formats()
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    address=f'http://127.0.0.1:{server.server_port}'
    print('Ride Overlay: '+address+'\nLåt detta fönster vara öppet. Ctrl+C avslutar.',flush=True)
    webbrowser.open(address)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally:
        for job in jobs.values():
            if job.state=='running': job.cancel()
        server.server_close()

if __name__=='__main__': main()
