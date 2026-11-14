"""Decode dequantized NCHW outputs from prepare_yolov8_rknn.py.

Returns standard YOLOv8 [1, 4+classes, anchors] (xywh + class probabilities).
Apply the deployment application's confidence filtering, class-aware NMS and
inverse letterbox transform afterwards. Inputs MUST already be dequantized.
"""
import numpy as np


def decode(outputs, strides=(8, 16, 32)):
    if len(outputs) != 9 or len(strides) != 3:
        raise ValueError("Expected 9 outputs ordered boxes, scores, score_sum for each scale")
    decoded = []
    classes = None
    for scale, stride in enumerate(strides):
        boxes, scores, score_sum = [np.asarray(x) for x in outputs[scale * 3:scale * 3 + 3]]
        if any(x.dtype.kind != "f" or not np.isfinite(x).all() for x in (boxes, scores, score_sum)):
            raise ValueError("Outputs must be finite dequantized floating-point tensors")
        if (boxes.ndim != 4 or scores.ndim != 4 or boxes.shape[0] != 1 or scores.shape[0] != 1
                or boxes.shape[1] % 4 or boxes.shape[2:] != scores.shape[2:]
                or score_sum.shape != (1, 1, *boxes.shape[2:])):
            raise ValueError("Unexpected NCHW head shape")
        if classes is not None and scores.shape[1] != classes:
            raise ValueError("Class counts differ between scales")
        classes = scores.shape[1]
        height, width = boxes.shape[2:]
        bins = boxes.shape[1] // 4
        logits = boxes.astype(np.float32).reshape(1, 4, bins, height, width)
        probs = np.exp(logits - logits.max(axis=2, keepdims=True))
        probs /= probs.sum(axis=2, keepdims=True)
        distances = (probs * np.arange(bins, dtype=np.float32)[None, None, :, None, None]).sum(axis=2)
        y, x = np.meshgrid(np.arange(height, dtype=np.float32), np.arange(width, dtype=np.float32), indexing="ij")
        centers = np.stack((x + 0.5, y + 0.5))[None]
        left_top, right_bottom = centers - distances[:, :2], centers + distances[:, 2:]
        xywh = np.concatenate(((left_top + right_bottom) * 0.5, right_bottom - left_top), axis=1) * stride
        decoded.append(np.concatenate((xywh.reshape(1, 4, -1), scores.reshape(1, classes, -1)), axis=1))
    return np.concatenate(decoded, axis=2)
