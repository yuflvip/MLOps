import json
import tempfile
import unittest
from pathlib import Path
from app.domain.common.experiment_metadata import read_experiment_metadata, normalize_framework


class MetadataTests(unittest.TestCase):
    def test_framework_normalization(self):
        self.assertEqual(normalize_framework("/weights/hgnetv2_b5.ssld_stage2_ft_in1k.pth"), "hgnetv2b5")
        self.assertEqual(normalize_framework("C:\\weights\\yolo26n.pt"), "yolo26n")
        self.assertEqual(normalize_framework("yolov8x.pt"), "yolov8x")
        self.assertIsNone(normalize_framework(True))
        self.assertIsNone(normalize_framework("unknown.pt"))

    def test_nested_hgnet_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "args.json").write_text(json.dumps({"config": {"model": {"name": "hgnetv2_b5.ssld_stage2_ft_in1k", "pretrained": True}, "data": {"img_size": [224, 224]}}}), encoding="utf-8")
            self.assertEqual(read_experiment_metadata(root), {"model_framework": "hgnetv2b5", "model_size": "224×224"})

    def test_yaml_config_and_invalid_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "args.yaml").write_text("model: yolo26m.pt\nimgsz: 640\n", encoding="utf-8")
            self.assertEqual(read_experiment_metadata(root), {"model_framework": "yolo26m", "model_size": "640×640"})
            (root / "args.yaml").write_text("[broken", encoding="utf-8")
            self.assertEqual(read_experiment_metadata(root), {"model_framework": None, "model_size": None})


if __name__ == "__main__":
    unittest.main()
