#!/usr/bin/env python3

import os
import time
from pathlib import Path

from config.settings import SETTINGS
from core.drone_controller import DroneController
from core.camera_manager import CameraManager


def run():
    print("\n" + "=" * 60)
    print("РУЧНОЙ РЕЖИМ")
    print("=" * 60)
    
    for path in [SETTINGS['paths']['data_dir'], SETTINGS['paths']['raw_dir'],
                 SETTINGS['paths']['poses_dir']]:
        Path(path).mkdir(parents=True, exist_ok=True)
    
    try:
        drone = DroneController(
            SETTINGS['airsim']['host'],
            SETTINGS['airsim']['port'],
            SETTINGS['drone']['name']
        )
    except Exception as e:
        print(f"Ошибка: {e}")
        input("\nEnter...")
        return
    
    camera = CameraManager(drone.client, SETTINGS['drone']['name'], SETTINGS['camera'])
    
    waypoints = SETTINGS['mission'].get('waypoints', [[0,0,-7], [100,0,-7]])
    print(f"\nМаршрут: {waypoints[0]} → {waypoints[1]}")
    
    if input("Начать? [y/n]: ").strip().lower() != 'y':
        return
    
    mission_id = time.strftime("%Y%m%d_%H%M%S")
    raw_dir = os.path.join(SETTINGS['paths']['raw_dir'], f"manual_{mission_id}")
    Path(raw_dir).mkdir(parents=True, exist_ok=True)
    
    try:
        if not drone.arm_and_takeoff(SETTINGS['drone']['altitude']):
            print("Взлёт не удался!")
            return

        is_recording = camera.start_video_recording(raw_dir, fps=10.0)
        if is_recording:
            print("Запись с камеры запущена")
        else:
            print("[!] Не удалось запустить запись с камеры")
        
        start, end = waypoints[0], waypoints[1]
        move_task = drone.client.moveToPositionAsync(
            end[0], end[1], SETTINGS['drone']['altitude'],
            SETTINGS['drone']['speed'], vehicle_name=drone.drone_name
        )

        while True:
            frame_data = camera.capture_scene(raw_dir)
            if frame_data and frame_data.get("frame_bgr") is not None:
                camera.write_video_frame(frame_data["frame_bgr"])

            pos = drone.get_position()
            dist_to_target = ((pos[0] - end[0]) ** 2 + (pos[1] - end[1]) ** 2 + (pos[2] - SETTINGS['drone']['altitude']) ** 2) ** 0.5
            if dist_to_target < 1.0:
                break

            time.sleep(0.1)

        move_task.join()

        video_path = camera.stop_video_recording()
        if video_path:
            print(f"Видео сохранено: {video_path}")

        panorama_path = camera.capture_panorama(raw_dir)
        if panorama_path:
            print(f"Панорама сохранена: {panorama_path}")
        else:
            print("[!] Не удалось сохранить панораму")
        
        drone.land()
        print("Готово!")
        
    except Exception as e:
        print(f"Ошибка: {e}")
        camera.stop_video_recording()
        drone.land()
    
    input("\nEnter...")


if __name__ == "__main__":
    run()