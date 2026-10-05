# MACH-VII v2 API

기준: `interface/backend/api_server.py`, `shared/ui_dto.py`. 기본 서버는 8000이다. 인증 미들웨어나 token 검사는 없으며 CORS는 모든 origin을 허용한다.

| Method | Endpoint | Request | Response |
|---|---|---|---|
| GET | `/` | 없음 | status 문자열 JSON |
| POST | `/api/request` | UserRequestDTO JSON | 아래 유형별 JSON 또는 처리되지 않은 경우 null |
| POST | `/api/command` | query `command` 문자열, 필수 | status=accepted, command |
| POST | `/api/config` | query camera_source, robot_target, logic_mode(선택) | status=config_updated |
| WS | `/ws` | 연결 후 client request 없음 | SystemSnapshot JSON text 반복 전송 |

## 통합 요청

```json
{"request_type":"command","command":"물체를 확인해줘"}
```

일반 명령은 BackgroundTasks로 전달하고 `status: accepted`, `type: command`, `payload`를 반환한다. 멈춰/정지/stop/관둬/취소/중단/그만이 포함되면 agent·servoing·driver를 정지시키고 `status: stopped`, message를 반환한다.

```json
{
  "request_type":"config_change",
  "config":{"target_robot":"pybullet","active_camera":"pybullet","op_mode":"rule_based"}
}
```

config 필수 필드는 target_robot(pybullet/dofbot), active_camera(pybullet/realsense), op_mode(rule_based/memory_based)다. `is_emergency_stop`은 기본 false이며 이 필드만으로 긴급 정지 branch를 선택하지 않는다. 응답은 status=config_updated와 config다.

```json
{"request_type":"emergency"}
```

응답은 `status: emergency_stop_triggered`다. DTO 타입 오류는 FastAPI validation 응답을 따른다. command/config 누락을 교차 검증하는 validator는 없어 해당 branch가 처리되지 않으면 null로 끝날 수 있다.

## 레거시 경로의 차이

`/api/command`는 JSON body가 아니라 query parameter다. 통합 경로의 정지 키워드 우회를 구현하지 않고 직접 execute_task를 예약한다. `/api/config`는 인자로 robot_target·logic_mode를 받지만 현재 body에서는 camera_source만 반영한다. 통합 경로와 같은 동작으로 가정하지 않는다.

## WebSocket

`pipeline.get_system_snapshot()`을 JSON text로 보낸다. timestamp, brain, emotion(vector/preset_id/muscles), perception, robot(is_moving/battery/mode), strategy, last_frame/last_depth/last_ee_frame/last_ee_depth가 있다. 영상은 base64이며 일부 값은 null일 수 있다. loop의 0.016초 sleep은 목표 주기다. client message나 인증 handshake는 구현하지 않았다.

[라우팅 소스](../interface/backend/api_server.py) · [DTO](../shared/ui_dto.py) · [스냅샷 생성](../shared/pipeline.py)
