import airsim
import time
import numpy as np
from typing import Tuple

from utils.logger import setup_logger


class DroneController:
    def __init__(self, host: str = "127.0.0.1", port: int = 41451, 
                 drone_name: str = "", timeout: int = 30):
        self.logger = setup_logger("DroneController")
        self.drone_name = drone_name
        
        self.logger.info(f"Подключение к AirSim: {host}:{port}")
        
        self.client = airsim.MultirotorClient(ip=host, port=port, timeout_value=timeout)
        
        try:
            self.logger.info("Сброс симуляции...")
            self.client.reset()
            time.sleep(2)
        except Exception as e:
            self.logger.warning(f"Сброс не удался: {e}")
        
        connected = False
        attempts = 0
        
        while not connected and attempts < 5:
            try:
                attempts += 1
                self.logger.info(f"Попытка {attempts}/5...")
                self.client.confirmConnection()
                connected = True
            except Exception as e:
                self.logger.warning(f"Ошибка: {e}")
                if attempts < 5:
                    time.sleep(3)
        
        if not connected:
            raise ConnectionError("Не удалось подключиться к AirSim")
        
        self.logger.info("Подключение установлено!")
        
        try:
            self.client.enableApiControl(True, self.drone_name)
            self.client.armDisarm(True, self.drone_name)
            time.sleep(0.5)
        except Exception as e:
            self.logger.warning(f"Армирование: {e}")
        
    def arm_and_takeoff(self, altitude: float = -7.0) -> bool:
        self.logger.info("=== ВЗЛЁТ ===")
        
        try:
            for _ in range(3):
                try:
                    self.client.enableApiControl(True, self.drone_name)
                    self.client.armDisarm(True, self.drone_name)
                    break
                except:
                    time.sleep(0.5)
            
            time.sleep(1)
            
            self.logger.info(f"Набор высоты {abs(altitude)}м...")
            
            time.sleep(1)
            
            self.client.moveToZAsync(-3, 2, vehicle_name=self.drone_name).join()
            time.sleep(1)
            self.client.moveToZAsync(altitude, 2, vehicle_name=self.drone_name).join()
            time.sleep(2)
            
            pos = self.get_position()
            actual_alt = abs(pos[2])
            self.logger.info(f"Высота: {actual_alt:.1f}м")
            
            if actual_alt < 5.0:
                self.logger.warning("Повтор взлёта...")
                self.client.moveToZAsync(altitude, 5, vehicle_name=self.drone_name).join()
                time.sleep(3)
                pos = self.get_position()
                actual_alt = abs(pos[2])
            
            if actual_alt > 5.0:
                self.logger.info("✓ Взлёт успешен!")
                return True
            else:
                self.logger.error("✗ Взлёт не удался")
                return False
                
        except Exception as e:
            self.logger.error(f"Ошибка взлёта: {e}")
            return False
    
    def set_camera_pitch(self, cam_name: str, pitch: float):
        try:
            pose = airsim.Pose(
                airsim.Vector3r(0, 0, 0),
                airsim.to_quaternion(np.radians(pitch), 0, 0)
            )
            self.client.simSetCameraPose(cam_name, pose, self.drone_name)
            time.sleep(0.3)
        except Exception as e:
            self.logger.warning(f"Камера {cam_name}: {e}")
    
    def get_position(self) -> Tuple[float, float, float]:
        try:
            state = self.client.getMultirotorState(self.drone_name)
            p = state.kinematics_estimated.position
            return (p.x_val, p.y_val, p.z_val)
        except:
            return (0, 0, 0)
    
    def get_yaw(self) -> float:
        try:
            state = self.client.getMultirotorState(self.drone_name)
            q = state.kinematics_estimated.orientation
            siny = 2.0 * (q.w_val * q.z_val + q.x_val * q.y_val)
            cosy = 1.0 - 2.0 * (q.y_val * q.y_val + q.z_val * q.z_val)
            return np.degrees(np.arctan2(siny, cosy))
        except:
            return 0.0
    
    def move_by_velocity(self, vx: float, vy: float, vz: float, 
                        yaw_rate: float, duration: float = 0.1):
        try:
            self.client.moveByVelocityAsync(
                vx, vy, vz, duration,
                airsim.DrivetrainType.MaxDegreeOfFreedom,
                airsim.YawMode(is_rate=True, yaw_or_rate=yaw_rate),
                self.drone_name
            )
        except Exception as e:
            self.logger.error(f"Движение: {e}")
    
    def hover(self, duration: float = 0.5):
        try:
            self.client.hoverAsync(self.drone_name).join()
            time.sleep(duration)
        except:
            pass
    
    def land(self):
        self.logger.info("=== ПОСАДКА ===")
        try:
            pos = self.get_position()
            self.client.moveToZAsync(-3, 2, vehicle_name=self.drone_name).join()
            time.sleep(1)
            self.client.moveToZAsync(0, 1, vehicle_name=self.drone_name).join()
            self.client.landAsync(self.drone_name).join()
            time.sleep(2)
            self.client.armDisarm(False, self.drone_name)
            self.client.enableApiControl(False, self.drone_name)
            self.logger.info("✓ Посадка завершена")
        except Exception as e:
            self.logger.error(f"Посадка: {e}")