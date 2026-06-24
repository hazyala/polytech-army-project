import { StrictMode } from 'react' // 리액트 엄격 모드 활성화
import { createRoot } from 'react-dom/client' // 루트 요소 생성을 위한 패키지
import './index.css'
import App from './App.jsx'

// DOM의 'root' 엘리먼트에 React 앱을 렌더링합니다.
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
