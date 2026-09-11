import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from gpx import parse_gpx,sample
from rendering import validate,render,OverlayRenderer

def fixture():
    return b'''<gpx xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg>
    <trkpt lat="58" lon="15"><time>2026-01-01T00:00:00Z</time><extensions><power>0</power><cad>0</cad></extensions></trkpt>
    <trkpt lat="58.00001" lon="15"><time>2026-01-01T00:00:01Z</time><extensions><power>100</power><cad>80</cad></extensions></trkpt>
    <trkpt lat="58.00002" lon="15"><time>2026-01-01T00:00:20Z</time><extensions><power>200</power></extensions></trkpt>
    </trkseg><trkseg><trkpt lat="58.00003" lon="15"><time>2026-01-01T00:00:21Z</time></trkpt></trkseg></trk></gpx>'''

class CoreTests(unittest.TestCase):
    def setUp(self): self.a=parse_gpx(fixture())
    def test_zero_and_interpolation(self):
        self.assertEqual(sample(self.a,0)['power'],0)
        self.assertEqual(sample(self.a,.5)['power'],50)
        self.assertEqual(sample(self.a,0)['cad'],0)
    def test_gap_and_segment(self):
        self.assertIsNone(sample(self.a,10)['power'])
        self.assertEqual(sample(self.a,10)['elapsed'],10)
        self.assertIsNone(sample(self.a,20.5)['power'])
        self.assertEqual(self.a['duration'],21)
    def test_missing(self):
        self.assertFalse(self.a['metrics']['hr']['available'])
        self.assertIsNone(sample(self.a,20)['cad'])
    def test_invalid_inputs(self):
        for data in [b'<html/>',b'<!DOCTYPE gpx [<!ENTITY x "a">]><gpx/>',b'broken']:
            with self.assertRaises(ValueError): parse_gpx(data)
        for cfg in [{'metrics':['hr']},{'metrics':['power'],'fps':30},{'metrics':['power'],'start':5,'end':2},{'metrics':['power'],'end':float('nan')}]:
            with self.assertRaises(ValueError): validate(self.a,cfg)
    def test_alpha_all_layouts(self):
        for layout in ['row','stack']:
            for fmt in ['prores','webm']:
                cfg=validate(self.a,{'metrics':['power','cad','elapsed'],'layout':layout,'format':fmt})
                img=render(self.a,cfg,.5,True)
                self.assertEqual(img.getpixel((0,0))[3],0)
                self.assertEqual(img.getchannel('A').getextrema(),(0,255))
    def test_compact_dimensions_and_default_mp4(self):
        for layout in ['row','stack']:
            cfg=validate(self.a,{'metrics':['power','cad','elapsed'],'layout':layout})
            self.assertEqual(cfg['format'],'mp4')
            renderer=OverlayRenderer(self.a,cfg)
            self.assertLess(renderer.size[0]*renderer.size[1],3840*2160//4)
            self.assertTrue(all(n%2==0 for n in renderer.size))
            for t in [0,.5,1,10,20,21]:
                frame=renderer.frame(t)
                self.assertEqual(frame.size,renderer.size)
                self.assertEqual(frame.getpixel((0,0)),(0,0,0,255))
    def test_labels_and_values_fit_inside_margins(self):
        for layout in ['row','stack']:
            for size in ['small','medium','large']:
                cfg=validate(self.a,{'metrics':['speed','power','cad','elapsed','distance'],'layout':layout,'size':size,'format':'prores'})
                renderer=OverlayRenderer(self.a,cfg)
                for t in [0,1,20,21]:
                    box=renderer.frame(t).getchannel('A').getbbox()
                    self.assertGreater(box[0],0); self.assertGreater(box[1],0)
                    self.assertLess(box[2],renderer.size[0]); self.assertLess(box[3],renderer.size[1])

if __name__=='__main__': unittest.main()
