import cv2
import numpy as np
import torch
from typing import Optional, Tuple
from dataclasses import dataclass
from ultralytics import YOLO

from utils.logger import setup_logger


@dataclass
class RoadDetection:
    mask: np.ndarray
    offset: float
    width: float
    confidence: float
    center_point: Tuple[int, int]


class RoadDetector:
    def __init__(self, model_path: str, conf_threshold: float = 0.25):
        self.logger = setup_logger("RoadDetector")
        self.conf_threshold = conf_threshold
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        self.logger.info(f"Загрузка: {model_path}")
        self.model = YOLO(model_path)
        self.model.to(self.device)
        
        self.road_class_id = self._find_road_class()
        self.logger.info(f"Класс дороги: {self.road_class_id}")
        
        self.center_history = []
        self.max_history = 5
        
    def _find_road_class(self) -> int:
        for idx, name in self.model.names.items():
            if name.lower() in ['road', 'street', 'highway', 'lane']:
                return idx
        return 0
    
    def detect(self, frame: np.ndarray) -> Optional[RoadDetection]:
        if frame is None or frame.size == 0:
            return None
        
        h, w = frame.shape[:2]
        
        results = self.model(frame, conf=self.conf_threshold, verbose=False)
        
        if len(results) == 0 or results[0].masks is None:
            return None
        
        masks = results[0].masks.data.cpu().numpy()
        boxes = results[0].boxes
        
        best_mask = None
        best_conf = 0
        
        for mask, box in zip(masks, boxes):
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            
            if cls_id != self.road_class_id or conf < self.conf_threshold:
                continue
            
            mask_resized = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
            mask_binary = (mask_resized > 0.5).astype(np.uint8)
            
            if conf > best_conf:
                best_conf = conf
                best_mask = mask_binary
        
        if best_mask is None:
            return None
        
        center_x = self._find_center_line(best_mask, w, h)
        
        self.center_history.append(center_x)
        if len(self.center_history) > self.max_history:
            self.center_history.pop(0)
        
        smooth_center = int(np.mean(self.center_history))
        
        offset = (smooth_center - w / 2) / (w / 2)
        width = np.sum(best_mask) / (w * h)
        
        return RoadDetection(
            mask=best_mask,
            offset=offset,
            width=width,
            confidence=best_conf,
            center_point=(smooth_center, h // 2)
        )
    
    def _find_center_line(self, mask: np.ndarray, w: int, h: int) -> int:
        y_start = int(h * 0.4)
        roi_mask = mask[y_start:, :]
        
        center_x_list = []
        
        for y in range(0, roi_mask.shape[0], 5):
            row = roi_mask[y, :]
            road_pixels = np.where(row > 0)[0]
            
            if len(road_pixels) > 10:
                center_x = int(np.mean(road_pixels))
                weight = 1.0 + (y / roi_mask.shape[0])
                center_x_list.extend([center_x] * int(weight * 3))
        
        if not center_x_list:
            moments = cv2.moments(mask)
            if moments["m00"] > 0:
                return int(moments["m10"] / moments["m00"])
            return w // 2
        
        return int(np.median(center_x_list))
    
    def visualize(self, frame: np.ndarray, detection: Optional[RoadDetection]) -> np.ndarray:
        h, w = frame.shape[:2]
        vis = frame.copy()
        
        if detection is None:
            overlay = np.full_like(vis, (0, 0, 80))
            vis = cv2.addWeighted(vis, 0.6, overlay, 0.4, 0)
            cv2.putText(vis, "ROAD LOST", (w//4, h//2),
                       cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 4)
            return vis
        
        purple = np.zeros_like(vis)
        purple[detection.mask > 0] = (255, 0, 255)
        vis = cv2.addWeighted(vis, 1.0, purple, 0.4, 0)
        
        contours, _ = cv2.findContours(detection.mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(vis, contours, -1, (200, 0, 200), 2)
        
        center_x = detection.center_point[0]
        for y in range(0, h, 20):
            cv2.line(vis, (center_x, y), (center_x, min(y+10, h)), (255, 255, 255), 2)
        
        cv2.circle(vis, detection.center_point, 12, (0, 255, 0), -1)
        cv2.circle(vis, detection.center_point, 16, (255, 255, 255), 2)
        
        cx, cy = w // 2, h // 2
        cv2.line(vis, (cx - 15, cy), (cx + 15, cy), (255, 0, 0), 3)
        cv2.line(vis, (cx, cy - 15), (cx, cy + 15), (255, 0, 0), 3)
        cv2.circle(vis, (cx, cy), 8, (255, 0, 0), -1)
        
        cv2.line(vis, (cx, cy), detection.center_point, (0, 255, 255), 3)
        
        texts = [
            f"YOLO-road-seg | CenterLine",
            f"OFFSET: {detection.offset:+.3f}",
            f"CONF: {detection.confidence:.2f}"
        ]
        
        y = 35
        for text in texts:
            cv2.putText(vis, text, (12, y+2), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,0), 3)
            cv2.putText(vis, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
            y += 30
        
        arrow_y = h - 60
        end_x = int(cx - detection.offset * 150)
        
        cv2.rectangle(vis, (cx - 160, arrow_y - 25), (cx + 160, arrow_y + 25), (0,0,0), -1)
        
        color = (0, 255, 0) if abs(detection.offset) < 0.1 else (0, 165, 255) if abs(detection.offset) < 0.3 else (0, 0, 255)
        cv2.arrowedLine(vis, (cx, arrow_y), (end_x, arrow_y), color, 5, tipLength=0.3)
        
        if abs(detection.offset) < 0.1:
            direction = "CENTER"
        elif detection.offset > 0:
            direction = "TURN RIGHT"
        else:
            direction = "TURN LEFT"
        
        cv2.putText(vis, direction, (cx - 50, arrow_y + 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
        
        bar_x = w - 30
        cv2.rectangle(vis, (bar_x - 10, 100), (bar_x + 10, h - 100), (50,50,50), -1)
        
        indicator_y = (h // 2) + int(detection.offset * (h // 2 - 120))
        indicator_y = np.clip(indicator_y, 120, h - 120)
        
        cv2.circle(vis, (bar_x, indicator_y), 8, color, -1)
        cv2.circle(vis, (bar_x, h // 2), 4, (255,255,255), -1)
        
        return vis