"""Behavior checks for timing, actual movement, fixed background and guardrails."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image, ImageDraw, ImageSequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from smooth_loop import build


class SmoothLoopTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for i, x in enumerate((22, 28, 34)):
            image = Image.new('RGB', (80, 80), '#23384a')
            draw = ImageDraw.Draw(image)
            draw.rectangle((x, 26, x + 15, 49), fill='#edcc57')
            draw.line((x + 3, 28, x + 12, 46), fill='#bd703b', width=2)
            image.save(self.root / f'pose{i}.png')
        mask = Image.new('L', (80, 80), 255)
        ImageDraw.Draw(mask).rectangle((12, 16, 62, 60), fill=0)
        mask.save(self.root / 'fixed.png')
        self.config = {'sources': ['pose0.png', 'pose1.png', 'pose2.png'], 'mode': 'pingpong',
                       'frames': 12, 'duration_ms': 360, 'static_mask': 'fixed.png', 'colors': 64}

    def run_build(self, name='result.gif'):
        manifest = self.root / 'motion.json'
        manifest.write_text(json.dumps(self.config), encoding='utf-8')
        return build(manifest, self.root / name)

    def decoded(self, name):
        with Image.open(self.root / name) as gif:
            return [np.array(f.convert('RGB')) for f in ImageSequence.Iterator(gif)]

    def test_movement_return_and_background(self):
        report = self.run_build()
        frames = self.decoded('result.gif')
        self.assertTrue(report['checks_passed'])
        self.assertEqual(report['frames'], 12)
        self.assertGreater(report['unique_decoded_frames'], 3)
        self.assertEqual(report['duration_ms'], 360)
        self.assertEqual(report['loop'], 0)
        self.assertEqual(report['static_background_max_channel_change'], 0)
        centers = [np.where((a[:, :, 0] > 180) & (a[:, :, 1] > 150))[1].mean() for a in frames]
        self.assertGreater(centers[6] - centers[0], 9)
        self.assertLess(abs(centers[-1] - centers[0]), 2)

    def test_speed_variants_keep_pixels_and_exact_total(self):
        self.run_build('normal.gif')
        self.config['duration_ms'] = 490
        report = self.run_build('slow.gif')
        self.assertEqual(report['duration_ms'], 490)
        self.assertTrue(all(t >= 20 and t % 10 == 0 for t in report['frame_durations_ms']))
        self.assertEqual([a.tobytes() for a in self.decoded('normal.gif')],
                         [a.tobytes() for a in self.decoded('slow.gif')])

    def test_closed_cycle_and_gif_input(self):
        pictures = [Image.open(self.root / f'pose{i}.png').convert('RGB') for i in range(3)]
        pictures[0].save(self.root / 'source.gif', save_all=True, append_images=pictures[1:], duration=100, loop=0)
        self.config.pop('sources')
        self.config.update(source='source.gif', indices=[0, 1, 2], mode='cycle')
        self.assertTrue(self.run_build()['checks_passed'])

    def test_rejects_sub20ms_and_overwrites(self):
        self.config['duration_ms'] = 120
        with self.assertRaisesRegex(ValueError, '20 ms'):
            self.run_build()
        self.assertFalse((self.root / 'result.gif').exists())
        self.config['duration_ms'] = 360
        self.run_build()
        original = (self.root / 'result.gif').read_bytes()
        with self.assertRaises(FileExistsError):
            self.run_build()
        self.assertEqual(original, (self.root / 'result.gif').read_bytes())

    def test_rejects_transparency_and_ambiguous_mask(self):
        image = Image.open(self.root / 'pose0.png').convert('RGBA')
        image.putalpha(128)
        image.save(self.root / 'pose0.png')
        with self.assertRaisesRegex(ValueError, 'transparent'):
            self.run_build()
        image.convert('RGB').save(self.root / 'pose0.png')
        Image.new('L', (80, 80), 128).save(self.root / 'fixed.png')
        with self.assertRaisesRegex(ValueError, 'binary'):
            self.run_build()


if __name__ == '__main__':
    unittest.main()
