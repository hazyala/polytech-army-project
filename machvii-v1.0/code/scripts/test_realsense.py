import pyrealsense2 as rs
import numpy as np
import cv2

# RealSense 파이프라인 및 설정 개체 생성
pipeline = rs.pipeline()
config = rs.config()

# 컬러 및 깊이 스트림 설정 (해상도 640x480, 프레임 속도 15fps)
# 가상 환경의 대역폭 제한을 고려하여 최적화된 설정을 사용함
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 15)
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 15)

# 설정된 구성을 바탕으로 스트리밍 시작
pipeline.start(config)

# 깊이(Depth) 데이터를 시각적으로 확인하기 위한 컬러 맵 변환 도구 생성
colorizer = rs.colorizer()

print("Streaming started. Press 'q' to exit.")

try:
    while True:
        # 데이터 수신을 위해 최대 10초(10000ms) 대기
        frames = pipeline.wait_for_frames(10000)
        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()
        
        # 프레임이 유효하지 않을 경우 다음 루프로 이동
        if not depth_frame or not color_frame:
            continue

        # 프레임 데이터를 Numpy 배열(행렬) 형태로 변환
        color_image = np.asanyarray(color_frame.get_data())
        
        # 깊이 프레임에 컬러 맵(Rainbow) 적용 후 Numpy 배열로 변환
        depth_colormap = np.asanyarray(colorizer.colorize(depth_frame).get_data())

        # 두 이미지를 가로 방향(Horizontal)으로 결합
        images = np.hstack((color_image, depth_colormap))

        # 결합된 이미지를 화면에 출력
        cv2.imshow('RealSense (Color & Depth)', images)

        # 'q' 키 입력 시 반복문 종료
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
finally:
    # 파이프라인 중지 및 생성된 모든 윈도우 창 닫기
    pipeline.stop()
    cv2.destroyAllWindows()
