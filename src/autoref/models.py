from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProposedPoint:
    """Otomatik tespit edilen ve kalibrasyona öneri olarak sunulan kontrol noktası."""

    pixel: tuple[float, float]
    world_m: tuple[float, float]          # standart varsayıma dayalı dünya koordinatı
    detection_confidence: float           # 0.0–1.0
    description: str = ""                 # "left_lane_near", "right_lane_far", vb.

    def to_control_point(self, point_id: str):
        """ControlPoint(source='auto') döndür — kalibrasyona doğrudan beslenebilir."""
        from src.calibration.models import ControlPoint
        return ControlPoint(
            id=point_id,
            pixel=self.pixel,
            world_m=self.world_m,
            source="auto",
        )
