from pathlib import Path
import math
import re
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont
from gpx import METRICS, sample

ROOT = Path(__file__).resolve().parent

def validate(activity, data):
    cfg = dict(data)
    for key, allowed, default in [('layout',['row','stack'],'row'),('size',['small','medium','large'],'medium'),('format',['mp4','prores','webm'],'mp4')]:
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

def display_value(key,value):
    if value is None: return '—'
    if key=='elapsed': return clock(value)
    if key in ['speed','distance','temp']: return f'{value:.1f}'
    return str(round(value))

def text_limits(activity):
    """Stable widths for the entire activity, including rounding and missing values."""
    if '_text_limits' not in activity:
        activity['_text_limits']={
            key:max([1]+[len(display_value(key,p.get(key))) for p in activity['points']])
            for key in METRICS if key!='elapsed'
        }
        activity['_text_limits']['elapsed']=len(clock(activity['duration']))
    return activity['_text_limits']

class OverlayRenderer:
    """Allocate only the compact output. Reuse labels, units and icons every frame."""
    def __init__(self,activity,cfg):
        self.activity,self.cfg=activity,cfg
        fs={'small':64,'medium':88,'large':116}[cfg['size']]
        self.value_font=font(fs,True)
        label_font,unit_font=font(fs*.21),font(fs*.23)
        self.stroke=max(1,round(fs*.025)) if cfg['outline'] else 0
        margin=max(8,round(fs*.22)); gap=round(fs*.55)
        ix=round(fs*.38) if cfg['icons'] else 0
        limits=text_limits(activity)
        widths=[]
        for key in cfg['metrics']:
            widths.append(math.ceil(max(
                self.value_font.getlength('0'*limits[key]),
                label_font.getlength(METRICS[key]['label'].upper())+ix,
                unit_font.getlength(METRICS[key]['unit'])
            ))+2*self.stroke)
        cell_height=math.ceil(fs*1.64)
        if cfg['layout']=='row':
            w=sum(widths)+gap*(len(widths)-1)+2*margin; h=cell_height+2*margin
        else:
            w=max(widths)+2*margin; h=cell_height*len(widths)+gap*(len(widths)-1)+2*margin
        # H.264 yuv420p requires even dimensions. Keep these fixed for the clip.
        self.size=(2*math.ceil(w/2),2*math.ceil(h/2))
        self.base=Image.new('RGBA',self.size,(0,0,0,255 if cfg['format']=='mp4' else 0))
        d=ImageDraw.Draw(self.base); x=y=margin; self.positions=[]
        for key,width in zip(cfg['metrics'],widths):
            if cfg['icons']: icon(d,key,x,y,fs*.28,cfg['accent'])
            d.text((x+ix,y),METRICS[key]['label'].upper(),font=label_font,fill=cfg['accent'],anchor='lt',stroke_width=self.stroke,stroke_fill='black')
            d.text((x,y+fs*1.36),METRICS[key]['unit'],font=unit_font,fill='white',anchor='lt',stroke_width=self.stroke,stroke_fill='black')
            self.positions.append((key,x,y+fs*.38))
            if cfg['layout']=='row': x+=width+gap
            else: y+=cell_height+gap

    def frame(self,elapsed,preview=False):
        image=self.base.copy(); d=ImageDraw.Draw(image); values=sample(self.activity,elapsed)
        for key,x,y in self.positions:
            d.text((x,y),display_value(key,values[key]),font=self.value_font,fill='white',anchor='lt',stroke_width=self.stroke,stroke_fill='black')
        if preview: image.thumbnail((1280,900),Image.Resampling.LANCZOS)
        return image

def render(activity,cfg,elapsed,preview=False):
    return OverlayRenderer(activity,cfg).frame(elapsed,preview)
