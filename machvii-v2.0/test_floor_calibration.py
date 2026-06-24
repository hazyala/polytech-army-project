
import logging
import time
import sys
import os

# 프로젝트 루트 경로 설정
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sensor.implementations.realsense_vision import RealSenseVision

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_floor_calibration():
    logging.info("=== RealSense 바닥 평면 보정 테스트 ===")
    
    try:
        # 비전 시스템 초기화
        vision = RealSenseVision()
        
        # 워밍업 (카메라 안정화)
        logging.info("카메라 워밍업 중 (2초)...")
        time.sleep(2.0)
        
        # 초기 상태 확인
        logging.info(f"초기 Z 보정값: {vision.z_offset_correction} cm")
        
        # 바닥 보정 실행
        logging.info("바닥 보정(recalibrate_floor) 실행 중...")
        correction = vision.recalibrate_floor(samples=20)
        
        logging.info(f"보정 완료! 계산된 바닥 높이: {correction:.2f} cm")
        logging.info(f"적용된 Z 보정값: {vision.z_offset_correction} cm")
        
        if correction > 0:
            logging.info("SUCCESS: 바닥 평면을 성공적으로 찾았습니다.")
        else:
            logging.warning("FAIL: 바닥 평면을 찾지 못했거나 유효하지 않은 값입니다.")
            
    except Exception as e:
        logging.error(f"테스트 중 오류 발생: {e}")
    finally:
        # 리소스 정리 (필요 시)
        pass

if __name__ == "__main__":
    test_floor_calibration()
