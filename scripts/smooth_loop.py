"""Motion-aligned interpolation for small pose changes, not new pose generation."""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageSequence

from sticker import resolve, verify, write_json


def positive_int(value, name, minimum=1):
    if type(value) is not int or value < minimum:
        raise ValueError(f'{name} must be an integer >= {minimum}')
    return value


def read_anchors(base, config):
    if ('source' in config) == ('sources' in config):
        raise ValueError('Provide source (a GIF) OR sources (ordered image paths)')
    if 'source' in config:
        with Image.open(resolve(base, config['source'])) as image:
            pool = [frame.convert('RGBA') for frame in ImageSequence.Iterator(image)]
        indices = config.get('indices', list(range(len(pool))))
        if not isinstance(indices, list) or any(type(i) is not int or not 0 <= i < len(pool) for i in indices):
            raise ValueError('indices must be valid zero-based source frame indices')
        frames = [pool[i] for i in indices]
    else:
        frames = []
        for filename in config['sources']:
            with Image.open(resolve(base, filename)) as image:
                if getattr(image, 'n_frames', 1) != 1:
                    raise ValueError('sources entries must each be a single image')
                frames.append(image.convert('RGBA'))
    if len(frames) < 2:
        raise ValueError('At least two ordered anchor poses are required')
    if len({frame.size for frame in frames}) != 1:
        raise ValueError('Align anchors to the same canvas size before interpolation')
    if any(frame.getchannel('A').getextrema() != (255, 255) for frame in frames):
        raise ValueError('Composite transparent inputs onto the chosen background first')
    return [np.array(frame.convert('RGB')) for frame in frames]


def build(manifest, output):
    manifest, output = Path(manifest).resolve(), Path(output).resolve()
    config = json.loads(manifest.read_text(encoding='utf-8-sig'))
    if output.suffix.lower() != '.gif':
        raise ValueError('Output must end in .gif')
    report_path, contact_path = output.with_suffix('.report.json'), output.with_suffix('.frames.png')
    for path in (output, report_path, contact_path):
        if path.exists():
            raise FileExistsError(f'Choose a new version; file already exists: {path}')
    count = positive_int(config['frames'], 'frames', 2)
    duration = positive_int(config['duration_ms'], 'duration_ms', 40)
    if duration % 10 or duration < 20 * count:
        raise ValueError('Total duration must be a multiple of 10 ms and allow >=20 ms per frame')
    colors = positive_int(config.get('colors', 128), 'colors', 2)
    if colors > 256:
        raise ValueError('colors must be <=256')
    mode = config.get('mode')
    if mode not in ('pingpong', 'cycle'):
        raise ValueError('Choose mode explicitly: pingpong or cycle')
    anchors = read_anchors(manifest.parent, config)
    height, width = anchors[0].shape[:2]
    static = None
    if config.get('static_mask'):
        with Image.open(resolve(manifest.parent, config['static_mask'])) as image:
            if image.size != (width, height):
                raise ValueError('static_mask must match anchor dimensions')
            mask = np.array(image.convert('L'))
        if not np.isin(mask, [0, 255]).all():
            raise ValueError('static_mask must be binary: white=fixed, black=may move')
        static = mask == 255
        if not static.any() or static.all():
            raise ValueError('static_mask must include both fixed and moving regions')
        # Frame zero supplies pixels ONLY in the explicitly certified fixed area.
        for anchor in anchors[1:]:
            anchor[static] = anchors[0][static]
    try:
        import cv2
    except ImportError as error:
        raise RuntimeError('Install requirements-motion.txt to use motion interpolation') from error
    xx, yy = np.meshgrid(np.arange(width, dtype=np.float32), np.arange(height, dtype=np.float32))

    def flow(a, b):
        engine = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
        engine.setFinestScale(0)
        field = engine.calc(cv2.cvtColor(a, cv2.COLOR_RGB2GRAY), cv2.cvtColor(b, cv2.COLOR_RGB2GRAY), None)
        return cv2.GaussianBlur(field, (0, 0), .7)

    def warp(a, field, amount):
        mx, my = xx.copy(), yy.copy()
        for _ in range(5):
            displacement = cv2.remap(field, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
            mx, my = xx - amount * displacement[:, :, 0], yy - amount * displacement[:, :, 1]
        return cv2.remap(a, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT_101).astype(np.float32)

    pairs = list(zip(anchors[:-1], anchors[1:]))
    if mode == 'cycle':
        pairs.append((anchors[-1], anchors[0]))
    fields = [(flow(a, b), flow(b, a)) for a, b in pairs]
    ticks = duration // 10
    durations = [10 * (((i + 1) * ticks // count) - (i * ticks // count)) for i in range(count)]
    frames = []
    for i in range(count):
        # Sampling is independent of playback speed, so speed comparisons share pixels.
        phase = i / count
        position = ((len(anchors) - 1) * .5 * (1 - math.cos(2 * math.pi * phase))
                    if mode == 'pingpong' else len(anchors) * phase)
        segment = min(len(pairs) - 1, int(position))
        t = position - segment
        a, b = pairs[segment]
        if t < 1e-8:
            frame = a.copy()
        elif t > 1 - 1e-8:
            frame = b.copy()
        else:
            forward, backward = fields[segment]
            frame = np.clip((1 - t) * warp(a, forward, t) + t * warp(b, backward, 1 - t), 0, 255).astype('uint8')
        if static is not None:
            frame[static] = anchors[0][static]
        frames.append(Image.fromarray(frame))
    # One shared palette; no per-frame quantization-induced background flicker.
    strip = Image.new('RGB', (64, 64 * count))
    for i, frame in enumerate(frames):
        strip.paste(frame.resize((64, 64), Image.Resampling.LANCZOS), (0, i * 64))
    palette = strip.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
    indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    if len({frame.tobytes() for frame in indexed}) < 2:
        raise ValueError('No visible movement survives palette encoding')
    output.parent.mkdir(parents=True, exist_ok=True)
    indexed[0].save(output, save_all=True, append_images=indexed[1:], duration=durations,
                    loop=0, disposal=1, optimize=False)
    report = verify(output, contact_path)
    report.update({'requested_timeline_frames': count, 'encoder_merged_frames': count - report['frames'],
                   'mode': mode, 'anchor_count': len(anchors), 'method': 'Bidirectional DIS optical-flow warping and aligned blending; no newly drawn poses',
                   'timing_curve': 'cosine out-and-back' if mode == 'pingpong' else 'linear cyclic progress',
                   'static_background_max_channel_change': None,
                   'static_background_pixels': 0 if static is None else int(static.sum()),
                   'max_bytes': config.get('max_bytes'),
                   'size_target_met': None if config.get('max_bytes') is None else report['bytes'] <= config['max_bytes'],
                   'visual_review': 'not performed by script', 'platform_send_test': 'not performed by script',
                   'contact_sheet': str(contact_path)})
    if static is not None:
        with Image.open(output) as gif:
            first = np.array(gif.convert('RGB')).astype(np.int16)
            change = max(int(np.abs(np.array(f.convert('RGB')).astype(np.int16) - first)[static].max())
                         for f in ImageSequence.Iterator(gif))
        report['static_background_max_channel_change'] = change
    report['checks_passed'] = (report['is_multiframe'] and report['infinite_loop']
        and report['duration_ms'] == duration and report['unique_decoded_frames'] >= 2
        and report['static_background_max_channel_change'] in (None, 0)
        and (not config.get('require_exact_frames', False) or report['frames'] == count))
    write_json(report_path, report)
    if not report['checks_passed']:
        raise ValueError(f'Encoded GIF failed validation; see {report_path}')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.manifest, args.output), ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
