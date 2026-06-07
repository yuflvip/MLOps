from enum import Enum


class TaskGroup(str, Enum):
    TRAINING = "training"
    EXPORT = "export"


class TaskType(str, Enum):
    TRAINING = "training"
    EXPORT_ONNX = "export_onnx"
