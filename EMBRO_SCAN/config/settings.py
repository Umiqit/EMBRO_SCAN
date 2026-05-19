SETTINGS = {
    "airsim": {
        "host": "127.0.0.1",
        "port": 41451
    },
    "drone": {
        "name": "SimpleFlight",
        "speed": 3.0,           # Скорость вперёд
        "altitude": -7.0,
        "rotation_speed": 30.0,
        "lateral_speed": 0.0  # Скорость вбок для коррекции
    },
    "cameras": {
        "main": {
            "name": "0",
            "pitch": -75.0,  # Смотрим вниз на дорогу
            "width": 1920,
            "height": 1080,
            "fov": 60
        }
    },
    "camera": {
        "capture_mode": "stop_and_shoot",
        "width": 1920,
        "height": 1080,
        "fov": 30
    },
    "ai": {
        "model_path": "./ai/models/yolo11m-road-seg.pt",
        "conf_threshold": 0.25,
        "correction_gain": 2.5
    },
    "mission": {
        "target_distance": 100.0,
        "altitude": -7.0,
        "speed": 3.0,
        "max_time": 300.0
    },
    "paths": {
        "data_dir": "./data",
        "raw_dir": "./data/raw",
        "poses_dir": "./data/poses",
        "debug_dir": "./data/debug"
    }
}