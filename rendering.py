from pathlib import Path
import math
import re
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont
from gpx import METRICS, sample

ROOT = Path(__file__).resolve().parent
CANVASES = {'4k': (3840,2160), 'strip': (3840,540), 'hd': (1920,1080)}

def validate(activity, data):
    cfg = dict(data)
    for key, allowed, default in [('canvas',CANVASES,'4k'),('layout',['row','stack'],'row'),('size',['small','medium','large'],'medium'),('anchor',['bottom-left','bottom-right','top-left','top-right','center'],'bottom-left'),('format',['prores','webm'],'prores')]:
        cfg[key] = data.get(key,default)
        if cfg[key] not in allowed: raise ValueError('Ogiltigt val: '+key)
    cfg['fps'] = int(data.get('fps',2))
    if cfg['fps'] not in [1,2,3,5]: raise ValueError('Välj 1, 2, 3 eller 5 fps.')
    cfg['metrics'] = list(dict.fromkeys(data.get('metrics',[])))
    if not cfg['metrics'] or any(k not in METRICS or not activity['metrics'][k]['available'] for k in cfg['metrics']): raise ValueError('Välj minst ett tillgängligt mätvärde.')
    cfg['accent'] = data.get('accent','#c3f85c')
    if not isinstance(cfg['accent'],str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',cfg['accent']): raise ValueError('Ogiltig färg.')
    for key in ['icons','outline']: cfg[key] = bool(data.get(key,True))
    cfg['start'], cfg['end'] = float(data.get('start',0)), float(data.get('end',activity['duration']))
    if not all(math.isfinite(cfg[k]) for k in ['start','end']) or not 0 <= cfg['start'] < cfg['end'] <= activity['duration']: raise ValueError('Utsnittet måste ligga inom aktiviteten och slutet efter starten.')
    return cfg

def clock(t):
    t = int(t)
    return f'{t//3600:02}:{t//60%60:02}:{t%60:02}'

@lru_cache(maxsize=128)
def font(size, mono=False):
    return ImageFont.truetype(str(ROOT/'assets'/('DejaVuSansMono-Bold.ttf' if mono else 'DejaVuSans.ttf')),max(8,int(size)))

def icon(draw,key,x,y,s,color):
    def line(points): draw.line([(x+a*s,y+b*s) for a,b in points],fill=color,width=max(1,round(s*.08)),joint='curve')
    if key=='power': draw.polygon([(x+s*.6,y),(x+s*.13,y+s*.57),(x+s*.48,y+s*.57),(x+s*.35,y+s),(x+s*.9,y+s*.36),(x+s*.55,y+s*.36)],fill=color)
    elif key=='hr': line([(0,.4),(.2,.4),(.32,.1),(.5,.85),(.65,.3),(.8,.4),(1,.4)])
    elif key=='ele': line([(0,.85),(.4,.1),(.7,.65),(.82,.4),(1,.85),(0,.85)])
    elif key=='temp':
        draw.ellipse((x+s*.3,y+s*.55,x+s*.7,y+s*.95),fill=color); line([(.5,.7),(.5,.1)])
    elif key=='distance': line([(0,.7),(.3,.25),(.65,.75),(1,.2)])
    else:
        draw.ellipse((x+s*.08,y+s*.08,x+s*.92,y+s*.92),outline=color,width=max(1,round(s*.08)))
        line([(.5,.18),(.5,.5),(.76,.6)] if key=='elapsed' else [(.2,.8),(.5,.5),(.75,.22)])

def render(activity,cfg,elapsed,preview=False):
    width,height = CANVASES[cfg['canvas']]
    scale = min(1,1280/width) if preview else 1
    w,h = round(width*scale), round(height*scale)
    image = Image.new('RGBA',(w,h),(0,0,0,0)); d = ImageDraw.Draw(image)
    keys=cfg['metrics']; values=sample(activity,elapsed)
    fs={'small':64,'medium':88,'large':116}[cfg['size']]*width/3840*scale
    weights=[8.1 if k=='elapsed' else 5.2 for k in keys]
    margin=round(60*width/3840*scale)
    if cfg['layout']=='row': fs=min(fs,(w-2*margin)/sum(weights))
    else: fs=min(fs,(h-2*margin)/(len(keys)*1.85))
    fs=max(8,fs); cell_h=fs*1.85
    block_w=fs*(sum(weights) if cfg['layout']=='row' else max(weights))
    block_h=cell_h*(1 if cfg['layout']=='row' else len(keys))
    anchor=cfg['anchor']
    x=(w-block_w)/2 if anchor=='center' else w-margin-block_w if 'right' in anchor else margin
    y=(h-block_h)/2 if anchor=='center' else margin if 'top' in anchor else h-margin-block_h
    stroke=max(1,round(fs*.025)) if cfg['outline'] else 0
    for key,weight in zip(keys,weights):
        val=values[key]
        text='—' if val is None else clock(val) if key=='elapsed' else f'{val:.1f}' if key in ['speed','distance','temp'] else str(round(val))
        ix=fs*.38 if cfg['icons'] else 0
        if cfg['icons']: icon(d,key,x,y+fs*.08,fs*.28,cfg['accent'])
        label=METRICS[key]['label'].upper()
        d.text((x+ix,y),label,font=font(fs*.21),fill=cfg['accent'],stroke_width=stroke,stroke_fill='black')
        d.text((x,y+fs*.38),text,font=font(fs,True),fill='white',stroke_width=stroke,stroke_fill='black')
        d.text((x,y+fs*1.55),METRICS[key]['unit'],font=font(fs*.23),fill='white',stroke_width=stroke,stroke_fill='black')
        if cfg['layout']=='row': x+=weight*fs
        else: y+=cell_h
    return image
