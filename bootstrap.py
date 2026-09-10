"""Create a private Python environment once, then run the local application."""
from pathlib import Path
import subprocess
import sys
import venv

def main():
    if sys.version_info < (3,10): raise RuntimeError('Installera Python 3.10 eller senare från python.org.')
    root=Path(__file__).resolve().parent
    executable=root/'.venv'/('Scripts/python.exe' if sys.platform=='win32' else 'bin/python')
    if not executable.exists():
        print('Första starten: skapar Python-miljö...',flush=True)
        venv.EnvBuilder(with_pip=True).create(root/'.venv')
    check=subprocess.run([str(executable),'-c','import PIL, imageio_ffmpeg'],capture_output=True)
    if check.returncode:
        print('Installerar bild- och videoverktyg. Internet behövs vid första starten.',flush=True)
        subprocess.run([str(executable),'-m','pip','install','-r',str(root/'requirements.txt')],check=True)
    subprocess.run([str(executable),str(root/'server.py')],cwd=root,check=True)

if __name__=='__main__':
    try: main()
    except KeyboardInterrupt: pass
    except Exception as error:
        print('Kunde inte starta: '+str(error),file=sys.stderr)
        sys.exit(1)
