# MACH-VII 얼굴 UI

React 19와 Vite 7 기반 화면. `src/context/FaceContext.jsx`가 `ws://localhost:8000/ws`를 구독해 얼굴·로봇·전략·영상 상태를 갱신한다. framer-motion은 표현 애니메이션, lucide-react는 아이콘, Tailwind/PostCSS는 스타일 구성에 사용한다.

```bash
cd machvii-v2.0/interface/frontend
npm install
npm run dev
```

저장소 루트 기준 명령이다. Node.js 22.12 이상과 npm을 사용하고 Vite가 출력한 주소에 접속한다. backend는 별도 터미널에서 실행한다. `npm run build`, `npm run lint` script도 있다. `npm run preview`는 빌드된 화면 확인이다.

WebSocket 주소는 현재 코드에 고정돼 있다. 실시간 상태를 받으려면 backend도 실행해야 한다.

[backend와 API](../../docs/API.md) · [v2 실행](../../README.md)
