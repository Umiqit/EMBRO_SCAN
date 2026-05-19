import airsim
import numpy as np
import cv2
import time
from typing import Tuple, Optional
from dataclasses import dataclass

from ai.road_detector import RoadDetector, RoadDetection
from utils.logger import setup_logger


@dataclass
class CameraData:
    detection: Optional[RoadDetection]
    frame: Optional[np.ndarray]


class SingleCameraSystem:
    def __init__(self, client: airsim.MultirotorClient, config: dict, drone_name: str = ""):
        self.logger = setup_logger("SingleCameraSystem")
        self.client = client
        self.drone_name = drone_name
        
        from config.settings import SETTINGS
        ai_config = SETTINGS['ai']
        
        self.detector = RoadDetector(
            model_path=ai_config['model_path'],
            conf_threshold=ai_config['conf_threshold']
        )
        
        self.current_pitch = -75.0
        
        self.logger.info("Камера готова")
        
    def set_pitch(self, pitch: float):
        """Установить угол один раз"""
        if abs(pitch - self.current_pitch) < 2.0:
            return  # Уже примерно тот же угол
        
        try:
            pose = airsim.Pose(
                airsim.Vector3r(0, 0, 0),
                airsim.to_quaternion(np.radians(pitch), 0, 0)
            )
            self.client.simSetCameraPose("0", pose, self.drone_name)
            self.current_pitch = pitch
            time.sleep(0.3)
        except Exception as e:
            self.logger.warning(f"Камера: {e}")
    
    def get_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        try:
            responses = self.client.simGetImages([
                airsim.ImageRequest("0", airsim.ImageType.Scene, False, False)
            ], self.drone_name)
            
            if not responses or not responses[0].image_data_uint8:
                return False, None
            
            img1d = np.frombuffer(responses[0].image_data_uint8, dtype=np.uint8)
            h, w = responses[0].height, responses[0].width
            frame = img1d.reshape(h, w, 3)
            
            return True, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
        except Exception as e:
            self.logger.error(f"Ошибка камеры: {e}")
            return False, None
    
    def capture(self) -> CameraData:
        """Просто захват кадра"""
        success, frame = self.get_frame()
        
        if not success:
            return CameraData(None, None)
        
        detection = self.detector.detect(frame)
        
        return CameraData(detection, frame)
    
    def create_display(self, data: CameraData, check_mode: bool = False) -> Optional[np.ndarray]:
        """Визуализация"""
        if data.frame is None:
            return None
        
        vis = self.detector.visualize(data.frame, data.detection)
        vis = cv2.cvtColor(vis, cv2.COLOR_RGB2BGR)
        
        return vis