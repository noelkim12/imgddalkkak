#!/usr/bin/env python3
"""
간단한 시작 스크립트
필요한 패키지 확인 후 메인 프로그램 실행
"""

import sys
import subprocess
import importlib.util

def check_and_install_package(package_name, pip_name=None):
    """패키지가 설치되어 있는지 확인하고 없으면 설치"""
    if pip_name is None:
        pip_name = package_name
    
    spec = importlib.util.find_spec(package_name)
    if spec is None:
        print(f"{package_name} 패키지를 설치하는 중...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])
            print(f"{package_name} 설치 완료!")
        except subprocess.CalledProcessError:
            print(f"오류: {package_name} 패키지 설치에 실패했습니다.")
            return False
    else:
        print(f"{package_name}: OK")
    return True

def main():
    print("=" * 40)
    print("   이미지 배경 제거 도구 v1.0")
    print("=" * 40)
    print()
    
    print("Python 버전:", sys.version)
    print()
    
    print("필요한 패키지 확인 중...")
    
    # 필요한 패키지들 확인 및 설치
    packages = [
        ("rembg", "rembg"),
        ("PIL", "Pillow"),
        ("tkinterdnd2", "tkinterdnd2")
    ]
    
    # Alpha Matting 의존성 (선택적)
    alpha_packages = [
        ("pymatting", "pymatting"),
        ("cv2", "opencv-python"),
        ("scipy", "scipy")
    ]
    
    all_ok = True
    for package_name, pip_name in packages:
        if not check_and_install_package(package_name, pip_name):
            all_ok = False
    
    if not all_ok:
        print("\n패키지 설치에 실패했습니다. 수동으로 설치해주세요:")
        print("pip install rembg pillow tkinterdnd2")
        input("\nEnter 키를 누르면 종료됩니다...")
        return
    
    # Alpha Matting 의존성 확인 (선택적)
    print("\n선택적 Alpha Matting 의존성 확인 중...")
    alpha_ok = True
    for package_name, pip_name in alpha_packages:
        spec = importlib.util.find_spec(package_name)
        if spec is None:
            print(f"{package_name}: 없음")
            alpha_ok = False
        else:
            print(f"{package_name}: OK")
    
    if not alpha_ok:
        print("\n💡 Alpha Matting 기능을 사용하려면 추가 라이브러리가 필요합니다.")
        print("앱에서 해당 기능 사용 시 자동으로 설치됩니다.")
    
    print("\n프로그램을 시작합니다...")
    print()
    
    # 메인 프로그램 실행
    try:
        from remove_bg import main as run_main
        run_main()
    except ImportError as e:
        print(f"오류: remove_bg.py 파일을 찾을 수 없습니다: {e}")
        input("\nEnter 키를 누르면 종료됩니다...")
    except Exception as e:
        print(f"프로그램 실행 중 오류 발생: {e}")
        input("\nEnter 키를 누르면 종료됩니다...")

if __name__ == "__main__":
    main()