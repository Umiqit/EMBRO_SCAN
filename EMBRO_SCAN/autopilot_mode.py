#!/usr/bin/env python3

import os
import time
from pathlib import Path

from config.settings import SETTINGS
from core.drone_controller import DroneController
from core.single_camera_system import SingleCameraSystem
from core.mission_controller import MissionController


def run():
    print("\n" + "=" * 70)
    print("АВТОПИЛОТ — ЛЕТИМ ПО ДОРОГЕ")
    print("=" * 70)
    
    print(f"Цель: {SETTINGS['mission']['target_distance']}м")
    print(f"Высота: {abs(SETTINGS['mission']['altitude'])}м")
    print(f"Скорость: {SETTINGS['mission']['speed']} м/с")
    print()
    print("Просто летим прямо, корректируя вбок")

    if input("\nНачать? [y/n]: ").strip().lower() != 'y':
        return
    
    for path in [SETTINGS['paths']['data_dir'], SETTINGS['paths']['raw_dir'],
                 SETTINGS['paths']['poses_dir']]:
        Path(path).mkdir(parents=True, exist_ok=True)
    
    try:
        drone = DroneController(
            SETTINGS['airsim']['host'],
            SETTINGS['airsim']['port'],
            "SimpleFlight"
        )
    except Exception as e:
        print(f"Ошибка подключения: {e}")
        return
    
    camera = SingleCameraSystem(drone.client, SETTINGS, "SimpleFlight")
    
    config = {**SETTINGS['drone'], **SETTINGS['ai'], **SETTINGS['mission']}
    controller = MissionController(drone, camera, config)
    
    save_dir = os.path.join(SETTINGS['paths']['raw_dir'],
                           f"fly_{time.strftime('%Y%m%d_%H%M%S')}")
    Path(save_dir).mkdir(parents=True, exist_ok=True)
    
    try:
        controller.run_mission(save_dir)
    except Exception as e:
        print(f"Ошибка: {e}")
        drone.land()
    
    input("\nEnter...")


if __name__ == "__main__":
    run()