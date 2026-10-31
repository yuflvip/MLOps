"""Read experiment metadata from training configuration without loading weights."""
import json
import re
from pathlib import Path
import yaml

MODEL_FRAMEWORKS = tuple(["hgnetv2b" + str(i) for i in range(7)] +
    [prefix + suffix for prefix in ("yolo26", "yolov8") for suffix in ("n", "s", "m", "x", "l")])


def normalize_framework(value):
    if not isinstance(value, str):
        return None
    name = value.replace("\\", "/").rsplit("/", 1)[-1].split(".", 1)[0].lower()
    if name.startswith("hgnetv2"):
        name = name.replace("_", "")
    return name if name in MODEL_FRAMEWORKS else None


def normalize_size(value):
    if isinstance(value, str):
        value = re.findall(r"\d+", value)
    if isinstance(value, int) and not isinstance(value, bool):
        value = [value, value]
    if isinstance(value, (list, tuple)) and len(value) in (1, 2):
        try:
            numbers = [int(v) for v in value]
        except (ValueError, TypeError):
            return None
        if any(v <= 0 for v in numbers):
            return None
        if len(numbers) == 1:
            numbers *= 2
        return "%d×%d" % tuple(numbers)
    return None


def read_experiment_metadata(root):
    result = {"model_framework": None, "model_size": None}
    for filename in ("args.json", "args.yaml", "args.yml"):
        path = Path(root) / filename
        if not path.is_file() or path.stat().st_size > 1024 * 1024:
            continue
        try:
            content = path.read_text(encoding="utf-8-sig")
            data = json.loads(content) if filename.endswith("json") else yaml.safe_load(content)
        except (OSError, ValueError, yaml.YAMLError):
            continue
        if not isinstance(data, dict):
            continue
        def lookup(*keys):
            value = data
            for key in keys:
                if not isinstance(value, dict):
                    return None
                value = value.get(key)
            return value
        framework_values = [lookup("pretrained"), lookup("weights"), lookup("model"),
            lookup("config", "model", "weights"), lookup("config", "model", "pretrained"),
            lookup("config", "model", "name"), lookup("model", "name")]
        sizes = [lookup("imgsz"), lookup("img_size"), lookup("input_size"),
            lookup("config", "data", "img_size"), lookup("data", "img_size")]
        result["model_framework"] = result["model_framework"] or next((v for raw in framework_values if (v := normalize_framework(raw))), None)
        result["model_size"] = result["model_size"] or next((v for raw in sizes if (v := normalize_size(raw))), None)
    return result
