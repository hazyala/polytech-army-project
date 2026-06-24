import time
import logging

logging.basicConfig(level=logging.INFO)

# 1. RealSense Driver Test
try:
    import pyrealsense2 as rs
    print("=== RealSense Test ===")
    ctx = rs.context()
    devices = ctx.query_devices()
    print(f"Connected devices: {len(devices)}")
    for d in devices:
        print(f"- {d.get_info(rs.camera_info.name)} (S/N: {d.get_info(rs.camera_info.serial_number)})")
except Exception as e:
    print(f"RealSense error: {e}")

# 2. DOFBOT Connection Test
print("\n=== DOFBOT Test ===")
try:
    import requests
    url = "http://192.168.25.100:5000/api/status"
    print(f"Pinging DOFBOT at {url} ...")
    response = requests.get(url, timeout=3)
    if response.status_code == 200:
        print(f"DOFBOT Status: {response.json()}")
    else:
        print(f"DOFBOT returned code {response.status_code}")
except Exception as e:
    print(f"DOFBOT ping failed: {e}")
