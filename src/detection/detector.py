from __future__ import annotations

import numpy as np

from .models import Detection, VEHICLE_CLASSES, VEHICLE_CLASS_IDS


def _resolve_device(device: str) -> str:
    if device != "auto":
        return device
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


class YOLODetector:
    def __init__(
        self,
        model_name: str = "yolo11n.pt",
        device: str = "auto",
        conf_threshold: float = 0.25,
    ) -> None:
        from ultralytics import YOLO
        self._device = _resolve_device(device)
        self._conf = conf_threshold
        self._model = YOLO(model_name)

    def detect_frame(self, frame: np.ndarray, frame_idx: int) -> list[Detection]:
        """Run YOLO on a single frame, return vehicle detections only."""
        results = self._model(
            frame,
            device=self._device,
            conf=self._conf,
            classes=list(VEHICLE_CLASS_IDS),
            verbose=False,
        )
        detections: list[Detection] = []
        for r in results:
            boxes = r.boxes
            if boxes is None or len(boxes) == 0:
                continue
            for box in boxes:
                cls_id = int(box.cls[0])
                cls_name = r.names.get(cls_id, "")
                if cls_name not in VEHICLE_CLASSES:
                    continue
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                detections.append(Detection(
                    frame=frame_idx,
                    bbox=(x1, y1, x2, y2),
                    cls=cls_name,
                    confidence=conf,
                ))
        return detections
