"""Deterministic sprite-sheet/GIF assembly and decoded-file verification."""
import argparse
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps, ImageSequence, ImageStat


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def resolve(base, value):
    path = Path(value).expanduser()
    return path if path.is_absolute() else base / path


def crop_checked(image, box):
    if len(box) != 4 or any(not isinstance(x, int) for x in box):
        raise ValueError('Crop boxes require four integer pixel coordinates')
    left, top, right, bottom = box
    if not (0 <= left < right <= image.width and 0 <= top < bottom <= image.height):
        raise ValueError(f'Invalid or out-of-bounds crop: {box}, image={image.size}')
    return image.crop(tuple(box))


def read_source(base, spec):
    with Image.open(resolve(base, spec['path'])) as opened:
        if 'boxes' in spec and 'grid' in spec:
            raise ValueError('Choose boxes OR grid for each source')
        if 'boxes' not in spec and 'grid' not in spec:
            return [f.convert('RGBA') for f in ImageSequence.Iterator(opened)]
        image = opened.convert('RGBA')
    if 'boxes' in spec:
        return [crop_checked(image, box) for box in spec['boxes']]
    grid = spec['grid']
    cols, rows = grid['columns'], grid['rows']
    if not all(isinstance(n, int) and n > 0 for n in (cols, rows)):
        raise ValueError('Grid rows and columns must be positive integers')
    bounds = grid.get('bounds', [0, 0, image.width, image.height])
    crop_checked(image, bounds)
    left, top, right, bottom = bounds
    gap_x, gap_y = grid.get('gap', [0, 0])
    inset = grid.get('inset', 0)
    if any(not isinstance(n, int) or n < 0 for n in (gap_x, gap_y, inset)):
        raise ValueError('Grid gaps and inset must be nonnegative integer pixels')
    cell_w = (right - left - (cols - 1) * gap_x) / cols
    cell_h = (bottom - top - (rows - 1) * gap_y) / rows
    frames = []
    for row in range(rows):
        for col in range(cols):
            x = left + col * (cell_w + gap_x)
            y = top + row * (cell_h + gap_y)
            box = [round(x) + inset, round(y) + inset,
                   round(x + cell_w) - inset, round(y + cell_h) - inset]
            frames.append(crop_checked(image, box))
    return frames


def verify(path, contact=None):
    with Image.open(path) as gif:
        if gif.format != 'GIF':
            raise ValueError('Expected a GIF file')
        loop = gif.info.get('loop')
        dimensions = list(gif.size)
        durations, frames = [], []
        for frame in ImageSequence.Iterator(gif):
            durations.append(frame.info.get('duration', 0))
            frames.append(frame.convert('RGB'))
    hashes = [hashlib.sha256(f.tobytes()).hexdigest() for f in frames]
    scores = []
    for index, frame in enumerate(frames):
        following = (index + 1) % len(frames)
        diff = ImageChops.difference(frame, frames[following])
        scores.append({'from_index': index, 'to_index': following,
                       'pixel_mae': round(sum(ImageStat.Stat(diff).mean) / 3, 3)})
    if contact:
        columns = min(8, len(frames))
        thumb = 160
        label_h = 20
        sheet = Image.new('RGB', (columns * thumb,
                          math.ceil(len(frames) / columns) * (thumb + label_h)), '#333333')
        draw = ImageDraw.Draw(sheet)
        for index, frame in enumerate(frames):
            x = index % columns * thumb
            y = index // columns * (thumb + label_h)
            tile = ImageOps.pad(frame, (thumb, thumb), color='#333333')
            sheet.paste(tile, (x, y))
            draw.text((x + 4, y + thumb + 2), f'{index}: {durations[index]} ms', fill='white')
        sheet.save(contact)
    return {'file': str(Path(path).resolve()), 'dimensions': dimensions,
            'frames': len(frames), 'unique_decoded_frames': len(set(hashes)),
            'is_multiframe': len(frames) > 1, 'loop': loop, 'infinite_loop': loop == 0,
            'duration_ms': sum(durations), 'frame_durations_ms': durations,
            'bytes': Path(path).stat().st_size,
            'largest_changes': sorted(scores, key=lambda item: item['pixel_mae'], reverse=True)[:12],
            'seam_pixel_mae': scores[-1]['pixel_mae']}


def build(manifest, output):
    manifest, output = Path(manifest).resolve(), Path(output).resolve()
    if output.suffix.lower() != '.gif':
        raise ValueError('Output filename must end in .gif')
    report_path = output.with_suffix('.report.json')
    contact_path = output.with_suffix('.frames.png')
    for path in (output, report_path, contact_path):
        if path.exists():
            raise FileExistsError(f'Choose a new version; file already exists: {path}')
    config = json.loads(manifest.read_text(encoding='utf-8-sig'))
    size = config.get('size', [240, 240])
    if len(size) != 2 or any(not isinstance(n, int) or not 1 <= n <= 4096 for n in size):
        raise ValueError('size requires two positive integers up to 4096')
    colors = config.get('colors', 128)
    if not isinstance(colors, int) or not 2 <= colors <= 256:
        raise ValueError('colors must be an integer between 2 and 256')
    sources = {key: read_source(manifest.parent, spec)
               for key, spec in config['sources'].items()}
    caption = config.get('caption')
    font = None
    if caption:
        font = ImageFont.truetype(str(resolve(manifest.parent, caption['font'])),
                                  caption.get('font_size', 25))
    frames, durations = [], []
    background = config.get('background', '#ffffff')
    for entry in config['sequence']:
        index = entry['index']
        pool = sources[entry['source']]
        if not isinstance(index, int) or not 0 <= index < len(pool):
            raise ValueError(f'Invalid source frame index: {entry}')
        duration = entry.get('duration_ms', config.get('default_duration_ms', 70))
        if not isinstance(duration, int) or duration < 20 or duration % 10:
            raise ValueError('Durations must be integer multiples of 10 ms and at least 20 ms')
        rgba = pool[index]
        flat = Image.new('RGBA', rgba.size, background)
        flat.alpha_composite(rgba)
        frame = ImageOps.pad(flat.convert('RGB'), tuple(size),
                             method=Image.Resampling.LANCZOS, color=background)
        if caption:
            ImageDraw.Draw(frame).text(tuple(caption.get('xy', [15, 15])),
                caption['text'], font=font, fill=caption.get('fill', 'white'),
                stroke_width=caption.get('stroke_width', 0),
                stroke_fill=caption.get('stroke_fill', 'black'))
        frames.append(frame)
        durations.append(duration)
    if len(frames) < 2:
        raise ValueError('Animated stickers need at least two timeline entries')
    # Sample every frame equally, without adding blank atlas cells to the palette.
    strip = Image.new('RGB', (64, 64 * len(frames)))
    for index, frame in enumerate(frames):
        strip.paste(frame.resize((64, 64), Image.Resampling.LANCZOS), (0, index * 64))
    palette = strip.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
    indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    if len({hashlib.sha256(f.tobytes()).hexdigest() for f in indexed}) < 2:
        raise ValueError('Quantized sequence has no visible frame changes')
    output.parent.mkdir(parents=True, exist_ok=True)
    indexed[0].save(output, save_all=True, append_images=indexed[1:],
                    duration=durations, loop=0, disposal=1, optimize=True)
    report = verify(output, contact_path)
    report['requested_timeline_frames'] = len(frames)
    report['encoder_merged_frames'] = len(frames) - report['frames']
    report['max_bytes'] = config.get('max_bytes')
    report['size_target_met'] = (report['bytes'] <= config['max_bytes']
                                  if config.get('max_bytes') is not None else None)
    report['contact_sheet'] = str(contact_path)
    report['checks_passed'] = (report['is_multiframe'] and report['infinite_loop']
                                and report['duration_ms'] == sum(durations)
                                and report['unique_decoded_frames'] >= 2)
    write_json(report_path, report)
    if not report['checks_passed']:
        raise ValueError(f'Encoded GIF failed validation; see {report_path}')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    create = commands.add_parser('build')
    create.add_argument('manifest')
    create.add_argument('--output', required=True)
    check = commands.add_parser('verify')
    check.add_argument('gif')
    check.add_argument('--report')
    args = parser.parse_args()
    if args.command == 'build':
        result = build(args.manifest, args.output)
    else:
        if args.report and Path(args.report).exists():
            raise FileExistsError('Verification report exists; choose a new path')
        result = verify(args.gif)
        if args.report:
            Path(args.report).parent.mkdir(parents=True, exist_ok=True)
            write_json(args.report, result)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
