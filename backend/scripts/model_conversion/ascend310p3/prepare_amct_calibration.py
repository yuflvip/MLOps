#!/usr/bin/env python3
"""Prepare single-input FP32 NCHW calibration bins, optionally run AMCT PTQ.

Requires numpy and Pillow. --quantize additionally requires amct_onnx.
All mean/std/scale values use pixel units 0..255:
    tensor = (pixels - mean) / std * scale
Channel order is selected BEFORE normalization. No AIPP is run in this script.
"""
import argparse
import json
import math
from pathlib import Path
import random
import shutil
import subprocess
import sys


def arguments():
    p = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--images', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True,
                   help='New output directory; existing directories are rejected.')
    p.add_argument('--imgsz', type=int, nargs='+', required=True,
                   help='SIZE or HEIGHT WIDTH, e.g. 224 or 224 320')
    p.add_argument('--preprocess', choices=['stretch', 'letterbox', 'crop'], required=True)
    p.add_argument('--color', choices=['rgb', 'bgr'], default='rgb')
    p.add_argument('--mean', type=float, nargs=3, default=[0, 0, 0])
    p.add_argument('--std', type=float, nargs=3, default=[1, 1, 1])
    p.add_argument('--scale', type=float, default=1.0)
    p.add_argument('--pad-value', type=int, default=114)
    p.add_argument('--interpolation', choices=['nearest', 'bilinear', 'bicubic'], default='bilinear')
    p.add_argument('--limit', type=int, default=0, help='0: use all images')
    p.add_argument('--shuffle', action='store_true')
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--model', type=Path)
    p.add_argument('--input-name', default='images')
    p.add_argument('--quantize', action='store_true', help='Run amct_onnx calibration after preparing bins')
    a = p.parse_args()
    if len(a.imgsz) not in (1, 2) or any(x <= 0 for x in a.imgsz):
        p.error('--imgsz requires one or two positive integers')
    if not all(math.isfinite(x) for x in [*a.mean, *a.std, a.scale]) or any(x == 0 for x in a.std):
        p.error('normalization parameters must be finite; std must be nonzero')
    if not 0 <= a.pad_value <= 255 or a.limit < 0:
        p.error('--pad-value must be 0..255; --limit must be >=0')
    if a.quantize and a.model is None:
        p.error('--quantize requires --model')
    return a


def resize_image(im, height, width, mode, interpolation, pad_value):
    from PIL import Image
    resample = {'nearest': Image.Resampling.NEAREST,
                'bilinear': Image.Resampling.BILINEAR,
                'bicubic': Image.Resampling.BICUBIC}[interpolation]
    iw, ih = im.size
    if mode == 'stretch':
        return im.resize((width, height), resample)
    if mode == 'letterbox':
        ratio = min(width / iw, height / ih)
        nw = max(1, min(width, round(iw * ratio)))
        nh = max(1, min(height, round(ih * ratio)))
        canvas = Image.new('RGB', (width, height), (pad_value,) * 3)
        canvas.paste(im.resize((nw, nh), resample), ((width - nw) // 2, (height - nh) // 2))
        return canvas
    # Resize to cover target, then center crop. No crop_pct is implied.
    ratio = max(width / iw, height / ih)
    nw, nh = max(width, math.ceil(iw * ratio)), max(height, math.ceil(ih * ratio))
    im = im.resize((nw, nh), resample)
    left, top = (nw - width) // 2, (nh - height) // 2
    return im.crop((left, top, left + width, top + height))


def check_model(path, input_name, height, width):
    import onnx
    m = onnx.load(str(path), load_external_data=False)
    initializers = {x.name for x in m.graph.initializer}
    inputs = [x for x in m.graph.input if x.name not in initializers]
    if len(inputs) != 1:
        raise ValueError('This script supports single-input models only')
    inp = inputs[0]
    if inp.name != input_name or inp.type.tensor_type.elem_type != onnx.TensorProto.FLOAT:
        raise ValueError(f'Expected FP32 input {input_name!r}; actual: {inp.name!r}, '
                         f'type={inp.type.tensor_type.elem_type}')
    dims = inp.type.tensor_type.shape.dim
    expected = [1, 3, height, width]
    if len(dims) != 4 or any(d.HasField('dim_value') and d.dim_value > 0 and d.dim_value != e
                             for d, e in zip(dims, expected)):
        raise ValueError(f'Model shape does not match {expected}: {inp.type}')
    return [{'domain': x.domain, 'version': x.version} for x in m.opset_import]


def main():
    a = arguments()
    import numpy as np
    from PIL import Image, ImageOps
    height, width = (a.imgsz[0], a.imgsz[0]) if len(a.imgsz) == 1 else a.imgsz
    source, output = a.images.resolve(), a.output.resolve()
    if not source.is_dir():
        raise ValueError(f'Image directory does not exist: {source}')
    if output.exists():
        raise ValueError(f'Output already exists; choose a new directory: {output}')
    if source == output or source in output.parents:
        raise ValueError('Output must be outside the source image directory')
    opsets = None
    if a.model:
        if not a.model.is_file():
            raise ValueError(f'Model does not exist: {a.model}')
        opsets = check_model(a.model, a.input_name, height, width)
    amct = shutil.which('amct_onnx') if a.quantize else None
    if a.quantize and not amct:
        raise ValueError('amct_onnx command is not available in PATH')
    exts = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tif', '.tiff'}
    files = sorted(p for p in source.rglob('*') if p.is_file() and p.suffix.lower() in exts)
    if a.shuffle:
        random.Random(a.seed).shuffle(files)
    if a.limit:
        files = files[:a.limit]
    if not files:
        raise ValueError('No supported images found')
    bins = output / 'calib_bin'
    bins.mkdir(parents=True, exist_ok=False)
    mean = np.asarray(a.mean, dtype=np.float32).reshape(1, 1, 3)
    std = np.asarray(a.std, dtype=np.float32).reshape(1, 1, 3)
    records, errors = [], []
    for path in files:
        try:
            with Image.open(path) as original:
                im = ImageOps.exif_transpose(original).convert('RGB')
                original_size = list(im.size)
                im = resize_image(im, height, width, a.preprocess, a.interpolation, a.pad_value)
                pixels = np.asarray(im, dtype=np.float32)
            if a.color == 'bgr':
                pixels = pixels[:, :, ::-1]
            tensor = ((pixels - mean) / std * np.float32(a.scale)).transpose(2, 0, 1)[None]
            tensor = np.ascontiguousarray(tensor, dtype='<f4')
        except Exception as exc:
            errors.append({'image': str(path), 'error': str(exc)})
            continue
        target = bins / f'{len(records):06d}.bin'
        tensor.tofile(target)
        records.append({'image': str(path), 'bin': target.name, 'original_wh': original_size,
                        'bytes': target.stat().st_size})
    report = {'arguments': {k: str(v) if isinstance(v, Path) else v for k, v in vars(a).items()},
              'shape': [1, 3, height, width], 'dtype': 'little-endian float32',
              'formula': '(pixels - mean) / std * scale', 'opsets': opsets,
              'count': len(records), 'images': records, 'errors': errors}
    command = [amct or 'amct_onnx', 'calibration', '--model', str(a.model.resolve()) if a.model else 'MODEL.onnx',
               '--input_shape', f'{a.input_name}:1,3,{height},{width}',
               '--data_types', 'float32', '--data_dir', str(bins),
               '--batch_num', str(len(records)), '--save_path', str(output / 'quantized' / 'model')]
    report['amct_command'] = command
    (output / 'manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Prepared {len(records)} images; errors={len(errors)}; shape={report["shape"]}', flush=True)
    print(f'Manifest: {output / "manifest.json"}', flush=True)
    print('AMCT command: ' + ' '.join(command), flush=True)
    if not records or errors:
        raise ValueError('Some images failed or none succeeded; inspect manifest. Quantization was not started.')
    if a.quantize:
        (output / 'quantized').mkdir()
        with (output / 'amct.log').open('w', encoding='utf-8') as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=False)
        print(f'AMCT exit={result.returncode}; log: {output / "amct.log"}', flush=True)
        return result.returncode
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        sys.exit(1)
