import time
import cv2
import numpy as np
from typing import List

from core.drone_controller import DroneController
from core.single_camera_system import SingleCameraSystem, CameraData
from core.autopilot_v3 import AutopilotV3
from utils.logger import setup_logger


class MissionController:
    def __init__(self, drone: DroneController, camera: SingleCameraSystem, config: dict):
        self.logger = setup_logger("MissionController")
        self.drone = drone
        self.camera = camera
        self.config = config
        
        self.autopilot = AutopilotV3(config)
        
        self.total_distance = 0.0
        self.last_pos = None
        self.check_count = 0
        self.start_time = time.time()
        
    def run_mission(self, save_dir: str) -> List[dict]:
        target = self.config.get('target_distance', 100.0)
        altitude = self.config.get('altitude', -7.0)
        max_time = self.config.get('max_time', 300.0)
        
        self.logger.info("=" * 70)
        self.logger.info(f"МИССИЯ: {target}м | Высота: {abs(altitude)}м")
        self.logger.info("Просто летим по дороге, корректируя вбок")
        self.logger.info("=" * 70)
        self.logger.info("'Q' — прервать")
        
        # Взлёт
        if not self.drone.arm_and_takeoff(altitude):
            self.logger.error("Взлёт не удался!")
            return []
        
        # Настройка камеры вниз
        self.camera.set_pitch(-75.0)
        time.sleep(0.5)
        self.autopilot.reset()
        
        # Проверка дороги
        test_data = self.camera.capture()
        if test_data.detection:
            self.logger.info(f"✓ Дорога найдена, offset={test_data.detection.offset:+.2f}")
        else:
            self.logger.warning("✗ Дорога не видна, но пробуем лететь")
        
        self.logger.info("СТАРТ ПОЛЁТА")
        
        metadata = []
        dt = 0.05  # 20 Гц
        next_check = 5.0  # Первый отчёт на 5м
        
        try:
            while self.total_distance < target:
                if time.time() - self.start_time > max_time:
                    break
                
                # Захват кадра
                data = self.camera.capture()
                
                # Отображение
                self._show_display(data, target, next_check)
                
                # Выход по 'q'
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    self.logger.info("Прервано")
                    break
                
                # Автопилот: просто летим с коррекцией
                vx, vy, yaw_rate, status = self.autopilot.update(data.detection)
                self.drone.move_by_velocity(vx, vy, 0, yaw_rate, dt)
                
                # Обновление расстояния
                self._update_distance()
                
                # Проверка каждые 5м — просто лог
                if self.total_distance >= next_check:
                    self.check_count += 1
                    offset = data.detection.offset if data.detection else 999
                    self.logger.info(f"Пройдено {self.total_distance:.1f}м | offset={offset:+.3f} | {status}")
                    next_check += 5.0
                
                # Поддержание высоты
                pos = self.drone.get_position()
                if abs(pos[2]) < altitude * 0.7:
                    self.drone.client.moveToZAsync(altitude, 2, vehicle_name=self.drone.drone_name)
                
                time.sleep(dt)
                
        except KeyboardInterrupt:
            self.logger.info("Ctrl+C")
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
        finally:
            cv2.destroyAllWindows()
            self.drone.land()
        
        # Итоги
        elapsed = time.time() - self.start_time
        self.logger.info("=" * 70)
        self.logger.info("МИССИЯ ЗАВЕРШЕНА")
        self.logger.info(f"Пройдено: {self.total_distance:.1f}м / {target}м")
        self.logger.info(f"Время: {elapsed:.1f}с")
        self.logger.info("=" * 70)
        
        return metadata
    
    def _update_distance(self):
        pos = self.drone.get_position()
        if self.last_pos is not None:
            delta = np.sqrt(sum((a-b)**2 for a, b in zip(pos, self.last_pos)))
            self.total_distance += delta
        self.last_pos = pos
    
    def _show_display(self, data: CameraData, target: float, next_check: float):
        """Простое отображение"""
        display = self.camera.create_display(data, check_mode=False)
        if display is None:
            return
        
        h, w = display.shape[:2]
        
        # Прогресс
        progress = min(100, int(self.total_distance / target * 100))
        
        texts = [
            f"DIST: {self.total_distance:.1f}m / {target}m ({progress}%)",
            f"NEXT LOG: {next_check:.1f}m | CHECKS: {self.check_count}",
            f"ALT: {abs(self.drone.get_position()[2]):.1f}m"
        ]
        
        y = 30
        for text in texts:
            cv2.putText(display, text, (12, y+2), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,0), 2)
            cv2.putText(display, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
            y += 28
        
        cv2.imshow("EMBRO_SCAN — FLY STRAIGHT", cv2.resize(display, (960, 720)))