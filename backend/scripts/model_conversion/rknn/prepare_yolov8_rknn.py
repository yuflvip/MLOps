#!/usr/bin/env python3
"""Extract the Rockchip nine-output YOLOv8 detection head from a standard ONNX.

Explicit preparation step: changes the output contract and requires the matching
DFL decoder in yolov8_postprocess.py. Never changes the source model.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tempfile


def prepare(source: Path, destination: Path):
    import numpy as np
    import onnx
    from onnx import helper, numpy_helper

    source = source.resolve(strict=True)
    destination = destination.resolve()
    if source.suffix.lower() != ".onnx" or destination.suffix.lower() != ".onnx":
        raise ValueError("源文件和目标文件必须使用 .onnx 扩展名")
    if destination.exists() or destination == source:
        raise ValueError("目标文件已存在，请使用新的 ONNX 文件名")
    model = onnx.load(str(source))
    if len(model.graph.input) != 1 or len(model.graph.output) != 1:
        raise ValueError("仅支持单输入、单标准检测输出的 YOLOv8 ONNX")
    shape = [x.dim_value for x in model.graph.input[0].type.tensor_type.shape.dim]
    if len(shape) != 4 or shape[:2] != [1, 3] or min(shape) <= 0:
        raise ValueError("需要固定 NCHW 三通道、batch=1 输入")
    heads = {}
    pattern = re.compile(r"^(.*)/(cv[23])\.([0-2])/\2\.\3\.2/Conv$")
    for node in model.graph.node:
        match = pattern.match(node.name)
        if node.op_type == "Conv" and match:
            key = (match[1], match[2], int(match[3]))
            if key in heads:
                raise ValueError("检测头匹配不唯一")
            heads[key] = node.output[0]
    prefixes = {key[0] for key in heads}
    if len(heads) != 6 or len(prefixes) != 1:
        raise ValueError("无法唯一识别 YOLOv8 cv2/cv3 三尺度检测头；不支持任意 ONNX 或其他 YOLO 架构")
    prefix = next(iter(prefixes))
    tensors = [heads[prefix, branch, scale] for scale in range(3) for branch in ("cv2", "cv3")]
    inferred = onnx.shape_inference.infer_shapes(model)
    shapes = {value.name: [x.dim_value for x in value.type.tensor_type.shape.dim]
              for value in [*inferred.graph.value_info, *inferred.graph.output]}
    strides = []
    classes = reg_max = None
    for scale in range(3):
        box, cls = (shapes.get(tensors[scale * 2 + i], []) for i in (0, 1))
        if (len(box) != 4 or len(cls) != 4 or box[0] != 1 or cls[0] != 1
                or box[2:] != cls[2:] or min(box + cls) <= 0 or box[1] % 4):
            raise ValueError("检测头尺寸不符合 DFL/分类输出约定")
        if scale == 0:
            classes, reg_max = cls[1], box[1] // 4
        if cls[1] != classes or box[1] != 4 * reg_max or reg_max <= 1:
            raise ValueError("各尺度的类别数或 DFL 分布维数不一致")
        if shape[2] % box[2] or shape[3] % box[3] or shape[2] // box[2] != shape[3] // box[3]:
            raise ValueError("无法推导检测头 stride")
        strides.append(shape[2] // box[2])
    if strides != [8, 16, 32]:
        raise ValueError("首版仅支持 stride 8/16/32 的 YOLOv8 检测模型")
    expected_count = sum(shapes[tensors[i]][2] * shapes[tensors[i]][3] for i in (0, 2, 4))
    original_shape = shapes[model.graph.output[0].name]
    if original_shape != [1, classes + 4, expected_count]:
        raise ValueError("源模型不是标准 YOLOv8 解码输出")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="yolov8-rknn-", dir=destination.parent) as temp:
        extracted = Path(temp) / "heads.onnx"
        onnx.utils.extract_model(str(source), str(extracted), [model.graph.input[0].name], tensors)
        result = onnx.load(str(extracted))
        opsets = [entry.version for entry in result.opset_import if entry.domain in ("", "ai.onnx")]
        if len(opsets) != 1 or opsets[0] < 13:
            raise ValueError("需要 opset >=13 的标准 ONNX")
        if opsets[0] > 19:
            # Apply official semantic adapters to the extracted graph, not a version-number edit.
            result = onnx.version_converter.convert_version(result, 19)
        del result.graph.output[:]
        for name, value in (("rknn_axes", np.array([1], dtype=np.int64)),
                            ("rknn_zero", np.array(0, dtype=np.float32)),
                            ("rknn_one", np.array(1, dtype=np.float32))):
            if any(x.name == name for x in result.graph.initializer):
                raise ValueError("输出适配名称与原模型冲突")
            result.graph.initializer.append(numpy_helper.from_array(value, name))
        for scale, stride in enumerate(strides):
            raw_boxes, raw_scores = tensors[2 * scale:2 * scale + 2]
            box_name, score_name, sum_name = [f"stride{stride}_{kind}" for kind in ("boxes", "scores", "score_sum")]
            result.graph.node.extend([
                helper.make_node("Identity", [raw_boxes], [box_name]),
                helper.make_node("Sigmoid", [raw_scores], [score_name]),
                helper.make_node("ReduceSum", [score_name, "rknn_axes"], [sum_name + "_raw"], keepdims=1),
                helper.make_node("Clip", [sum_name + "_raw", "rknn_zero", "rknn_one"], [sum_name]),
            ])
            for name, dims in ((box_name, shapes[raw_boxes]), (score_name, shapes[raw_scores]),
                               (sum_name, [1, 1, *shapes[raw_scores][2:]])):
                result.graph.output.append(helper.make_tensor_value_info(name, onnx.TensorProto.FLOAT, dims))
        metadata = {"output_schema": "rockchip_yolov8_9outputs", "classes": str(classes),
                    "reg_max": str(reg_max), "strides": json.dumps(strides),
                    "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
        existing = {entry.key: entry.value for entry in result.metadata_props}
        helper.set_model_props(result, {**existing, **metadata})
        onnx.checker.check_model(result)
        staged = Path(temp) / "prepared.onnx"
        onnx.save(result, str(staged))
        destination.hardlink_to(staged)
    print(json.dumps({"output": str(destination), "input_shape": shape, **metadata}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--onnx", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.onnx, args.output)
