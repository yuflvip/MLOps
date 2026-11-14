#!/usr/bin/env python3
"""Standalone ONNX -> RK3588 converter; dependencies live in rknn-env only."""
from __future__ import annotations

import argparse
from contextlib import chdir
import hashlib
from importlib.metadata import version
import json
import math
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import traceback


def triplet(value: str) -> list[float]:
    try:
        result = [float(x) for x in value.split(",")]
        if len(result) != 3 or not all(math.isfinite(x) for x in result):
            raise ValueError()
        return result
    except ValueError:
        raise argparse.ArgumentTypeError("Expected three finite comma-separated numbers") from None


def input_metadata(source: Path, override: str):
    import onnx

    model = onnx.load(str(source), load_external_data=False)
    initializers = {x.name for x in model.graph.initializer}
    inputs = [x for x in model.graph.input if x.name not in initializers]
    if len(inputs) != 1:
        raise ValueError("首版仅支持单输入图像模型")
    item = inputs[0]
    if item.type.tensor_type.elem_type != onnx.TensorProto.FLOAT:
        raise ValueError("仅支持 float32 ONNX 输入")
    dims = [d.dim_value if d.HasField("dim_value") and d.dim_value > 0 else None
            for d in item.type.tensor_type.shape.dim]
    shape = dims
    if override:
        name, raw = override.rsplit(":", 1)
        shape = [int(x) for x in raw.split(",")]
        if name != item.name or len(shape) != len(dims):
            raise ValueError("input-shape 与 ONNX 输入名称或维数不一致")
        if any(old and old != new for old, new in zip(dims, shape)):
            raise ValueError("不能覆盖 ONNX 已固定的输入尺寸")
    if len(shape) != 4 or any(not x or x <= 0 for x in shape):
        raise ValueError("动态输入必须通过 --input-shape 明确指定 name:1,3,h,w")
    if shape[:2] != [1, 3]:
        raise ValueError("仅支持 NCHW、batch=1、三通道图像输入")
    return item.name, shape, [x.name for x in model.graph.output], any(x is None for x in dims)


def prepare_dataset(directory: Path, work: Path, shape, resize_mode: str,
                    color_order: str, max_samples: int) -> Path:
    import cv2
    import numpy as np

    root = directory.resolve(strict=True)
    extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    images = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in extensions)
    if max_samples:
        images = images[:max_samples]
    if not images:
        raise ValueError("量化目录中没有支持的图片")
    height, width = shape[2:]
    prepared = []
    for index, path in enumerate(images):
        if not path.resolve().is_relative_to(root):
            raise ValueError("量化图片路径超出数据集目录")
        pixels = cv2.imread(str(path))
        if pixels is None:
            raise ValueError("无法解码量化图片: %s" % path)
        if resize_mode == "letterbox":
            h, w = pixels.shape[:2]
            scale = min(height / h, width / w)
            new_w, new_h = max(1, round(w * scale)), max(1, round(h * scale))
            resized = cv2.resize(pixels, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            pixels = np.full((height, width, 3), 114, dtype=np.uint8)
            top, left = (height - new_h) // 2, (width - new_w) // 2
            pixels[top:top + new_h, left:left + new_w] = resized
        else:
            pixels = cv2.resize(pixels, (width, height), interpolation=cv2.INTER_LINEAR)
        # Toolkit decodes calibration PNGs as RGB. Swap stored channels for BGR models.
        if color_order == "bgr":
            pixels = pixels[:, :, ::-1]
        target = work / ("calibration_%06d.png" % index)
        if not cv2.imwrite(str(target), pixels):
            raise RuntimeError("写入校准图片失败")
        prepared.append(str(target))
        print(json.dumps({"calibration_source": str(path),
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}, ensure_ascii=False), flush=True)
    listing = work / "dataset.txt"
    listing.write_text("\n".join(prepared) + "\n", encoding="utf-8")
    print("Calibration samples: %d" % len(prepared), flush=True)
    return listing


def convert(args):
    if any(x <= 0 for x in args.std):
        raise ValueError("std 必须大于 0")
    if args.max_samples < 0:
        raise ValueError("max-samples 不能为负数")
    source = Path(args.onnx).resolve(strict=True)
    output = Path(args.output).resolve()
    if source.suffix.lower() != ".onnx" or output.suffix.lower() != ".rknn":
        raise ValueError("源文件必须为 .onnx，输出必须为 .rknn")
    if output.exists() and not args.overwrite:
        raise ValueError("输出已存在；如需覆盖请使用 --overwrite")
    if args.precision in ("int8", "hybrid") and not args.dataset_dir:
        raise ValueError("INT8 / 混合量化必须指定 --dataset-dir")
    dataset_dir = Path(args.dataset_dir).resolve(strict=True) if args.precision in ("int8", "hybrid") else None
    name, shape, outputs, dynamic = input_metadata(source, args.input_shape)
    from rknn.api import RKNN

    print(json.dumps({"toolkit_version": version("rknn-toolkit2"),
                      "onnx_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                      "input": name, "shape": shape, "outputs": outputs,
                      "parameters": vars(args)}, ensure_ascii=False), flush=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rknn-export-") as temp, chdir(temp):
        work = Path(temp)
        load_source = source
        if args.profile == "yolov8":
            from prepare_yolov8_rknn import prepare
            load_source = work / "yolov8_rknn.onnx"
            prepare(source, load_source)
            print("Output contract: rockchip_yolov8_9outputs; requires yolov8_postprocess.decode", flush=True)
        dataset = (prepare_dataset(dataset_dir, work, shape, args.resize_mode,
                                   args.color_order, args.max_samples)
                   if args.precision in ("int8", "hybrid") else None)
        rknn = RKNN(verbose=True)
        try:
            steps = [("config", lambda: rknn.config(target_platform=args.target_platform,
                      mean_values=[args.mean], std_values=[args.std])),
                     ("load_onnx", lambda: rknn.load_onnx(model=str(load_source),
                      **({"inputs": [name], "input_size_list": [shape]} if dynamic else {}))),
                     ("build", lambda: rknn.build(do_quantization=args.precision in ("int8", "hybrid"),
                      dataset=str(dataset) if dataset else None,
                      **({"auto_hybrid": True} if args.precision == "hybrid" else {})))]
            for label, action in steps:
                print("Stage: " + label, flush=True)
                code = action()
                if code != 0:
                    raise RuntimeError("%s failed: %s" % (label, code))
            # Same filesystem as destination; publish only a complete, nonempty model.
            with tempfile.TemporaryDirectory(prefix=".rknn-", dir=output.parent) as dest:
                staged = Path(dest) / "model.rknn"
                code = rknn.export_rknn(str(staged))
                if code != 0 or not staged.is_file() or staged.stat().st_size == 0:
                    raise RuntimeError("export_rknn 未生成有效文件: %s" % code)
                if args.overwrite:
                    staged.replace(output)
                else:
                    # Atomic no-clobber publication also protects concurrent CLI invocations.
                    output.hardlink_to(staged)
            print("Worker generated: %s (%d bytes)" % (output, output.stat().st_size), flush=True)
        finally:
            rknn.release()


def run_checked_worker(command: list[str]) -> None:
    """Native compiler errors can coexist with build() == 0; inspect native output too."""
    fatal = None
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding="utf-8", errors="replace") as process:
        try:
            for line in process.stdout:
                print(line, end="", flush=True)
                plain = re.sub(r"\x1b\[[0-9;]*m", "", line)
                if "REGTASK:" in plain and "exceeds the limit" in plain:
                    fatal = "RKNN 编译器寄存器参数溢出，拒绝发布模型；请使用匹配板端后处理的 RKNN 专用 ONNX"
                elif (re.search(r"(?:^|\s)E RKNN:", plain) and fatal is None
                      and not re.search(r"Unkown op target: 0\s*$", plain)):
                    # 2.5.0 also emits the default-target diagnostic above for the
                    # HGNet model verified against ONNX on both board runtimes.
                    fatal = "RKNN 原生编译器报告错误，拒绝发布模型，请检查转换日志"
            code = process.wait()
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait()
    if fatal:
        raise RuntimeError(fatal)
    if code != 0:
        raise RuntimeError("RKNN 转换子进程失败，退出码 %s" % code)


def publish(args, argv):
    output = Path(args.output).resolve()
    if output.suffix.lower() != ".rknn":
        raise ValueError("输出必须为 .rknn")
    if output.exists() and not args.overwrite:
        raise ValueError("输出已存在；如需覆盖请使用 --overwrite")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".rknn-checked-", dir=output.parent) as temp:
        staged = Path(temp) / "model.rknn"
        run_checked_worker([sys.executable, "-u", str(Path(__file__).resolve()),
                            *argv, "--output", str(staged), "--worker"])
        if not staged.is_file() or staged.stat().st_size == 0:
            raise RuntimeError("RKNN 未生成非空模型")
        if args.overwrite:
            staged.replace(output)
        else:
            output.hardlink_to(staged)
    print("Export succeeded: %s (%d bytes)" % (output, output.stat().st_size), flush=True)


def main():
    def terminate(_signum, _frame):
        raise SystemExit(143)

    signal.signal(signal.SIGTERM, terminate)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--onnx", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--target-platform", choices=["rk3588"], default="rk3588")
    parser.add_argument("--precision", choices=["fp16", "int8", "hybrid"], default="fp16")
    parser.add_argument("--profile", choices=["generic", "yolov8"], default="generic",
                        help="yolov8 explicitly changes outputs to Rockchip's nine-output detection head")
    parser.add_argument("--input-shape", default="", help="name:1,3,h,w; required for dynamic input")
    parser.add_argument("--mean", type=triplet, default=[0., 0., 0.])
    parser.add_argument("--std", type=triplet, default=[1., 1., 1.])
    parser.add_argument("--color-order", choices=["rgb", "bgr"], default="rgb")
    parser.add_argument("--resize-mode", choices=["resize", "letterbox"], default="resize")
    parser.add_argument("--dataset-dir", help="Directory containing calibration images")
    parser.add_argument("--max-samples", type=int, default=200, help="0 uses all images")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    try:
        args = parser.parse_args()
        if args.worker:
            convert(args)
        else:
            publish(args, sys.argv[1:])
        return 0
    except Exception:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
