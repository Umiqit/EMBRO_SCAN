import numpy as np
from typing import Tuple, Optional

from ai.road_detector import RoadDetection
from utils.logger import setup_logger


class AutopilotV3:
    def __init__(self, config: dict):
        self.logger = setup_logger("AutopilotV3")
        
        self.speed = config.get('speed', 3.0)
        self.max_lateral = config.get('lateral_speed', 2.0)
        
        # Простой пропорциональный регулятор
        self.kp = 2.5  # Усиление коррекции
        
        # Сглаживание
        self.smooth_offset = 0.0
        
    def update(self, detection: Optional[RoadDetection]) -> Tuple[float, float, float, str]:
        """
        Просто летим прямо, немного корректируя вбок
        """
        if detection is None:
            # Дорога не видна — летим медленно прямо
            return (self.speed * 0.5, 0, 0, "NO ROAD")
        
        # Сглаживаем отклонение (чтобы не дёргаться)
        self.smooth_offset += (detection.offset - self.smooth_offset) * 0.3
        
        # Коррекция: если смещены вправо (offset > 0) — летим влево (vy < 0)
        vy = -self.smooth_offset * self.kp * self.max_lateral
        vy = np.clip(vy, -self.max_lateral, self.max_lateral)
        
        # Скорость вперёд: замедляемся если сильно смещены
        if abs(self.smooth_offset) > 0.3:
            vx = self.speed * 0.6  # Сильное смещение — тормозим
        elif abs(self.smooth_offset) > 0.15:
            vx = self.speed * 0.8  # Небольшое смещение — чуть медленнее
        else:
            vx = self.speed  # По центру — полный газ
        
        # Поворот к дороге
        yaw_rate = -self.smooth_offset * 10
        
        status = "OK" if abs(self.smooth_offset) < 0.1 else "CORRECT"
        
        return (vx, vy, yaw_rate, status)
    
    def reset(self):
        self.smooth_offset = 0.0