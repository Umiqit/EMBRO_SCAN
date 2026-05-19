import numpy as np
import cv2
from typing import List
from dataclasses import dataclass


@dataclass
class RoadDirection:
    angle: float
    confidence: float
    is_intersection: bool
    available_directions: List[str]


class RoadAnalyzer:
    def __init__(self):
        self.intersection_threshold = 0.25
        
    def analyze(self, mask: np.ndarray) -> RoadDirection:
        h, w = mask.shape
        
        road_area = np.sum(mask > 0) / (w * h)
        is_intersection = road_area > self.intersection_threshold
        
        directions = self._find_directions(mask)
        
        roi = mask[h//2:, :]
        moments = cv2.moments(roi)
        
        if moments["m00"] > 0:
            cx = moments["m10"] / moments["m00"]
            angle = (cx - w/2) / (w/2) * 45
        else:
            angle = 0
        
        return RoadDirection(
            angle=angle,
            confidence=min(road_area * 3, 1.0),
            is_intersection=is_intersection,
            available_directions=directions
        )
    
    def _find_directions(self, mask: np.ndarray) -> List[str]:
        h, w = mask.shape
        directions = []
        
        top = mask[:h//2, :]
        if np.sum(top) > 1000:
            directions.append('forward')
        
        left = mask[:, :w//3]
        right = mask[:, 2*w//3:]
        
        if np.sum(left) > 500:
            directions.append('left')
        if np.sum(right) > 500:
            directions.append('right')
        
        return directions if directions else ['forward']