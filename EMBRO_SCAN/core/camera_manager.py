import airsim
import numpy as np
import cv2
import time
import os
from typing import Optional, Dict

from utils.logger import setup_logger


class CameraManager:
    def __init__(self, client: airsim.MultirotorClient, drone_name: str, config: dict):
        self.logger = setup_logger("CameraManager")
        self.client = client
        self.drone_name = drone_name
        self.config = config
        self.capture_count = 0
        self.video_writer = None
        self.video_path = None

    def capture_scene(self, save_dir: str) -> Optional[Dict]:
        try:
            responses = self.client.simGetImages([
                airsim.ImageRequest("0", airsim.ImageType.Scene, False, False)
            ], self.drone_name)

            if not responses:
                return None

            response = responses[0]
            img1d = np.frombuffer(response.image_data_uint8, dtype=np.uint8)
            img_rgb = img1d.reshape(response.height, response.width, 3)

            filename = f"frame_{self.capture_count:04d}.png"
            filepath = os.path.join(save_dir, filename)
            frame_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
            cv2.imwrite(filepath, frame_bgr, [cv2.IMWRITE_PNG_COMPRESSION, 0])

            self.capture_count += 1

            state = self.client.getMultirotorState(self.drone_name)
            pos = state.kinematics_estimated.position
            ori = state.kinematics_estimated.orientation

            return {
                "filename": filename,
                "filepath": filepath,
                "timestamp": time.time(),
                "position": [pos.x_val, pos.y_val, pos.z_val],
                "orientation": [ori.w_val, ori.x_val, ori.y_val, ori.z_val],
                "width": response.width,
                "height": response.height,
                "frame_bgr": frame_bgr
            }

        except Exception as e:
            self.logger.error(f"Ошибка съёмки: {e}")
            return None

    def start_video_recording(self, save_dir: str, fps: float = 10.0) -> bool:
        try:
            responses = self.client.simGetImages([
                airsim.ImageRequest("0", airsim.ImageType.Scene, False, False)
            ], self.drone_name)

            if not responses or not responses[0].image_data_uint8:
                return False

            h, w = responses[0].height, responses[0].width
            self.video_path = os.path.join(save_dir, "flight_camera.avi")
            fourcc = cv2.VideoWriter_fourcc(*"MJPG")
            self.video_writer = cv2.VideoWriter(self.video_path, fourcc, fps, (w, h))
            if self.video_writer.isOpened():
                self.video_writer.set(cv2.VIDEOWRITER_PROP_QUALITY, 100)
            return self.video_writer.isOpened()
        except Exception as e:
            self.logger.error(f"Ошибка запуска записи: {e}")
            self.video_writer = None
            return False

    def write_video_frame(self, frame_bgr: np.ndarray):
        if self.video_writer is None:
            return
        try:
            self.video_writer.write(frame_bgr)
        except Exception as e:
            self.logger.warning(f"Ошибка записи кадра: {e}")

    def stop_video_recording(self) -> Optional[str]:
        if self.video_writer is None:
            return None
        try:
            self.video_writer.release()
            self.video_writer = None
            return self.video_path
        except Exception as e:
            self.logger.warning(f"Ошибка остановки записи: {e}")
            return None

    def capture_panorama(self, save_dir: str, panorama_fov: float = 120.0) -> Optional[str]:
        camera_name = "0"
        default_fov = float(self.config.get("fov", 90))
        try:
            self.client.simSetCameraFov(camera_name, panorama_fov, self.drone_name)
            time.sleep(0.2)

            responses = self.client.simGetImages([
                airsim.ImageRequest(camera_name, airsim.ImageType.Scene, False, False)
            ], self.drone_name)

            if not responses or not responses[0].image_data_uint8:
                return None

            response = responses[0]
            img1d = np.frombuffer(response.image_data_uint8, dtype=np.uint8)
            img_rgb = img1d.reshape(response.height, response.width, 3)
            frame_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

            filename = f"panorama_{int(time.time())}.png"
            filepath = os.path.join(save_dir, filename)
            cv2.imwrite(filepath, frame_bgr, [cv2.IMWRITE_PNG_COMPRESSION, 0])
            return filepath
        except Exception as e:
            self.logger.error(f"Ошибка панорамы: {e}")
            return None
        finally:
            try:
                self.client.simSetCameraFov(camera_name, default_fov, self.drone_name)
            except Exception:
                pass
