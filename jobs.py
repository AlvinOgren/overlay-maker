import math
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path
from rendering import ROOT, CANVASES, render

def ffmpeg_path():
    found=shutil.which('ffmpeg')
    if found: return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except (ImportError,RuntimeError): return None

def formats():
    exe=ffmpeg_path()
    if not exe: return []
    result=subprocess.run([exe,'-hide_banner','-encoders'],capture_output=True,text=True,timeout=15)
    return [key for key,encoder in [('prores','prores_ks'),('webm','libvpx-vp9')] if encoder in result.stdout]

class Job:
    def __init__(self,activity,cfg,directory=None):
        self.id=uuid.uuid4().hex; self.activity=activity; self.cfg=cfg
        self.state='running'; self.progress=0; self.error=''; self.cancelled=threading.Event(); self.process=None
        self.directory=Path(directory or ROOT/'exports'); self.directory.mkdir(parents=True,exist_ok=True)
        self.path=self.directory/('overlay-'+self.id[:10]+('.mov' if cfg['format']=='prores' else '.webm'))
        self.total=math.ceil((cfg['end']-cfg['start'])*cfg['fps']); self.started=time.time()
    def public(self):
        return {'id':self.id,'state':self.state,'progress':self.progress,'error':self.error,'frames':self.total,'seconds':round(time.time()-self.started),'download':'/download/'+self.id if self.state=='done' else None}
    def cancel(self):
        self.cancelled.set()
        if self.process and self.process.poll() is None:
            try: self.process.terminate()
            except OSError: pass
    def run(self):
        partial=self.path.with_name(self.path.stem+'.partial'+self.path.suffix)
        log=self.path.with_suffix('.log')
        try:
            w,h=CANVASES[self.cfg['canvas']]
            args=[ffmpeg_path(),'-hide_banner','-loglevel','error','-y','-f','rawvideo','-pixel_format','rgba','-video_size',f'{w}x{h}','-framerate',str(self.cfg['fps']),'-i','pipe:0','-an','-filter_threads','1','-threads','2']
            if self.cfg['format']=='prores': args+=['-c:v','prores_ks','-profile:v','4','-pix_fmt','yuva444p10le','-alpha_bits','16']
            else: args+=['-c:v','libvpx-vp9','-pix_fmt','yuva420p','-auto-alt-ref','0','-lossless','1','-b:v','0','-row-mt','1','-cpu-used','4']
            args += [str(partial)]
            with log.open('wb') as errors:
                self.process=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=errors)
                for i in range(self.total):
                    if self.cancelled.is_set(): break
                    frame=render(self.activity,self.cfg,self.cfg['start']+i/self.cfg['fps'])
                    self.process.stdin.write(frame.tobytes())
                    self.progress=min(99,(i+1)*100/self.total)
                self.process.stdin.close()
                code=self.process.wait()
            if self.cancelled.is_set(): self.state='cancelled'
            elif code: raise RuntimeError(log.read_text(errors='replace')[-1500:] or 'Videokodningen misslyckades.')
            else:
                partial.replace(self.path); self.progress=100; self.state='done'; log.unlink(missing_ok=True)
        except Exception as error:
            self.state='cancelled' if self.cancelled.is_set() else 'failed'; self.error=str(error)
        finally:
            if self.process and self.process.poll() is None:
                self.process.kill(); self.process.wait()
            partial.unlink(missing_ok=True)
            self.activity=None
