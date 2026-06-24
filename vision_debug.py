import cv2
import asyncio
import websockets
import json
import base64
import numpy as np
import time

# WebSocket 서버 주소
URI = "ws://localhost:8000/ws"

def decode_base64_image(b64_string):
    """Base64 문자열을 OpenCV 이미지로 디코딩"""
    if not b64_string:
        return None
    try:
        img_data = base64.b64decode(b64_string)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        print(f"이미지 디코딩 오류: {e}")
        return None

def draw_overlay(image, detections, title=""):
    """탐지된 객체 정보(BBox, 좌표)를 이미지에 오버레이"""
    if image is None: return None
    
    vis_img = image.copy()
    h, w = vis_img.shape[:2]
    
    # 제목 표시
    cv2.putText(vis_img, title, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
    
    if not detections:
        return vis_img

    # [Debug] 수신된 데이터 구조 확인
    if detections and 'pixel_center' not in detections[0]:
         print(f"[WARN] 'pixel_center' missing in detection data! Keys: {list(detections[0].keys())}")
    elif detections:
         # 정상적인 경우 너무 많은 로그를 방지하기 위해 100번에 1번만 출력하거나 생각
         pass 

    for det in detections:
        # BBox (YOLO) - 파란색 사각형
        # VisionBridge에서 pixel_center(u, v)와 bbox(w, h)를 모두 제공함
        center = det.get('pixel_center')
        bbox = det.get('bbox')
        
        if center and bbox:
            u, v = int(center[0]), int(center[1])
            w, h = int(bbox[0]), int(bbox[1])
            
            x1 = int(u - w / 2)
            y1 = int(v - h / 2)
            x2 = int(u + w / 2)
            y2 = int(v + h / 2)
            
            # 파란색 박스 그리기
            cv2.rectangle(vis_img, (x1, y1), (x2, y2), (255, 0, 0), 2)
            
            # 십자선 그리기 (중심)
            cv2.drawMarker(vis_img, (u, v), (0, 0, 255), markerType=cv2.MARKER_CROSS, markerSize=10, thickness=2)

        # 3D 좌표 텍스트 표시
        pos = det.get('position', {})
        # x, y, z 좌표를 각각 가져와서 명확하게 포맷팅
        x, y, z = pos.get('x', 0), pos.get('y', 0), pos.get('z', 0)
        text = f"{det['name']} : x={x}, y={y}, z={z} (cm)"
        
        # 텍스트 배경 박스
        text_size, _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        text_w, text_h = text_size
        
        # 박스 위에 텍스트 표시
        if center:
             tx, ty = u - w//2, v - h//2 - 10
             if ty < 20: ty = v + h//2 + 20 # 위쪽 공간 부족 시 아래로
             
             # 배경 박스 (검정색, 투명도 없음)
             cv2.rectangle(vis_img, (tx, ty - text_h - 5), (tx + text_w + 10, ty + 5), (0, 0, 0), -1)
             # 글자 (라임색, 가독성 확보)
             cv2.putText(vis_img, text, (tx + 5, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 128), 1)

    return vis_img

async def listen_and_show():
    print(f"Connecting to {URI} ...")
    
    # WebSocket 연결 옵션: keepalive ping 에러 방지
    # ping_interval: None으로 설정하여 자동 ping 비활성화
    # ping_timeout: None으로 설정하여 ping 응답 대기 시간 무제한
    async with websockets.connect(
        URI,
        ping_interval=None,  # keepalive ping 비활성화
        ping_timeout=None,   # ping timeout 비활성화
        close_timeout=10     # 연결 종료 대기 시간
    ) as websocket:
        print("Connected! Waiting for stream...")
        
        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)
                
                # 데이터 파싱
                # 1. World Camera
                frame_metrics = data.get('perception', {})
                detections = frame_metrics.get('detected_objects', [])
                
                img_main = decode_base64_image(data.get('last_frame'))
                img_depth = decode_base64_image(data.get('last_depth'))
                
                # 2. Gripper Camera
                img_ee = decode_base64_image(data.get('last_ee_frame'))
                img_ee_depth = decode_base64_image(data.get('last_ee_depth'))

                # 빈 이미지 처리 (검은색 캔버스)
                dummy = np.zeros((480, 640, 3), dtype=np.uint8)
                
                if img_main is None: img_main = dummy.copy()
                if img_depth is None: img_depth = dummy.copy() # Depth도 컬러맵 적용되어 3채널임
                if img_ee is None: img_ee = dummy.copy()
                if img_ee_depth is None: img_ee_depth = dummy.copy()
                
                # 오버레이 그리기
                # pixel 좌표가 없어서 정확한 BBox는 못 그리지만, 정보 표시는 가능
                # 추후 VisionBridge에서 pixel_center도 같이 보내주도록 수정하면 좋음
                img_main = draw_overlay(img_main, detections, "World RGB")
                cv2.putText(img_depth, "World Depth", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                
                cv2.putText(img_ee, "Gripper RGB", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                cv2.putText(img_ee_depth, "Gripper Depth", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

                # 4분할 화면 병합 (2x2 Grid)
                # Resize if needed to match sizes
                h1, w1 = img_main.shape[:2]
                img_depth = cv2.resize(img_depth, (w1, h1))
                img_ee = cv2.resize(img_ee, (w1, h1))
                img_ee_depth = cv2.resize(img_ee_depth, (w1, h1))
                
                top_row = np.hstack((img_main, img_depth))
                bottom_row = np.hstack((img_ee, img_ee_depth))
                combined = np.vstack((top_row, bottom_row))
                
                # 화면 크기 조정 (너무 크면 줄임)
                display_img = cv2.resize(combined, (0, 0), fx=0.8, fy=0.8)

                cv2.imshow("MACH-VII Vision Debugger (Quad View)", display_img)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
            except websockets.exceptions.ConnectionClosed:
                print("Connection closed. Exiting...")
                break
            except json.JSONDecodeError as e:
                print(f"JSON Decode Error: {e}")
                continue
            except Exception as e:
                print(f"Error: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(0.1)

    cv2.destroyAllWindows()

if __name__ == "__main__":
    try:
        asyncio.run(listen_and_show())
    except KeyboardInterrupt:
        print("Disconnected.")
