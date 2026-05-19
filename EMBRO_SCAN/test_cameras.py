#!/usr/bin/env python3

import cv2
import airsim

from config.settings import SETTINGS
from core.dual_camera_system import DualCameraSystem


def run():
    print("=" * 70)
    print("ТЕСТ 2 КАМЕР (без полёта)")
    print("=" * 70)
    
    client = airsim.MultirotorClient()
    client.confirmConnection()
    
    cameras = DualCameraSystem(client, SETTINGS, "")
    
    print("\nКлавиши:")
    print("  q — выход")
    print("  r — сбросить камеры")
    print("  1 — стандартные углы (-75 / -45)")
    print("  2 — положение для проверки (-45 / -20)")
    
    while True:
        data = cameras.capture()
        display = cameras.create_display(data)
        
        if display is not None:
            cv2.imshow("2 CAMERAS TEST", cv2.resize(display, (1280, 480)))
        
        key = cv2.waitKey(50) & 0xFF
        
        if key == ord('q'):
            break
        elif key == ord('r'):
            cameras._setup_cameras()
            print("Камеры сброшены")
        elif key == ord('1'):
            cameras.set_camera_pitch("0", -75)
            cameras.set_camera_pitch("view_cam", -45)
            print("Углы: -75° / -45°")
        elif key == ord('2'):
            cameras.set_camera_pitch("0", -45)
            cameras.set_camera_pitch("view_cam", -20)
            print("Углы: -45° / -20°")
    
    cv2.destroyAllWindows()


if __name__ == "__main__":
    run()