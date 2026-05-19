#!/usr/bin/env python3

import sys


def main():
    while True:
        print("\n" + "=" * 70)
        print("  EMBRO_SCAN — ДВЕ КАМЕРЫ")
        print("=" * 70)
        print("  [1] Ручной режим")
        print("  [2] Автопилот (100м, 2 камеры, 7м высота)")
        print("  [3] Тест 2 камер (без полёта)")
        print("  [0] Выход")
        print("=" * 70)
        
        choice = input("\nВыбор: ").strip()
        
        if choice == "0":
            sys.exit(0)
        elif choice == "1":
            import manual_mode
            manual_mode.run()
        elif choice == "2":
            import os
            from config.settings import SETTINGS
            
            model_path = SETTINGS['ai']['model_path']
            if not os.path.exists(model_path):
                print(f"\n[!] Модель не найдена: {model_path}")
                continue
            
            import autopilot_mode
            autopilot_mode.run()
        elif choice == "3":
            import test_cameras
            test_cameras.run()
        else:
            print("Неверный выбор")


if __name__ == "__main__":
    main()