import React, { useState } from 'react';
/*
 * FaceController.jsx
 * 얼굴 표정 파라미터(눈, 입, 고개 등)를 실시간으로 제어하는 디버깅용 UI 패널입니다.
 * 슬라이더를 통해 각 부위별 값을 미세 조정할 수 있습니다.
 */
import { Settings, Eye, MessageSquare, Sun, Move, Lock, Unlock } from 'lucide-react';

const Slider = ({ label, value, onChange, min, max, step = 1, icon: Icon }) => (
    <div className="mb-4">
        <div className="flex items-center justify-between mb-1">
            <div className="flex items-center text-gray-200 text-sm font-medium">
                {Icon && <Icon size={14} className="mr-2" />}
                {label}
            </div>
            <span className="text-xs text-gray-400 font-mono">{value}</span>
        </div>
        <input
            type="range"
            min={min}
            max={max}
            step={step}
            value={value}
            onChange={(e) => onChange(parseFloat(e.target.value))}
            className="w-full h-1 bg-white/20 rounded-lg appearance-none cursor-pointer accent-blue-500 hover:accent-blue-400 transition-all"
        />
    </div>
);

const FaceController = ({ params, setParams }) => {
    const [isSymmetric, setIsSymmetric] = useState(true); // 대칭 고정 상태 (기본값: true)

    const handleChange = (key, value) => {
        setParams(prev => {
            let nextParams = { ...prev };

            // 파라미터 업데이트 헬퍼 함수
            const updateField = (targetParams, targetKey, targetValue) => {
                if (targetKey.includes('.')) {
                    const [parent, child] = targetKey.split('.');
                    return {
                        ...targetParams,
                        [parent]: {
                            ...targetParams[parent],
                            [child]: targetValue
                        }
                    };
                } else {
                    return { ...targetParams, [targetKey]: targetValue };
                }
            };

            // 1. 현재 변경된 필드 업데이트
            nextParams = updateField(nextParams, key, value);

            // 2. 대칭 모드일 경우 반대쪽 눈 동기화
            if (isSymmetric) {
                if (key.startsWith('leftEye.')) {
                    const mirrorKey = key.replace('leftEye.', 'rightEye.');
                    nextParams = updateField(nextParams, mirrorKey, value);
                } else if (key.startsWith('rightEye.')) {
                    const mirrorKey = key.replace('rightEye.', 'leftEye.');
                    nextParams = updateField(nextParams, mirrorKey, value);
                }
            }

            return nextParams;
        });
    };

    return (
        // 플로팅 글래스 패널 - 블랙 글래스 스타일의 디버깅 패널
        <div className="w-80 max-h-[90vh] bg-black/50 backdrop-blur-xl border border-white/10 rounded-2xl p-6 overflow-y-auto text-white shadow-2xl transition-all duration-300">
            <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold flex items-center tracking-tight text-white">
                    <Settings className="mr-2" size={20} />
                    Face Control
                </h2>
                <label className="flex items-center space-x-2 cursor-pointer bg-white/5 px-2 py-1 rounded hover:bg-white/10 transition-colors border border-white/10">
                    {isSymmetric ? <Lock size={14} className="text-blue-400" /> : <Unlock size={14} className="text-gray-500" />}
                    <input
                        type="checkbox"
                        checked={isSymmetric}
                        onChange={(e) => setIsSymmetric(e.target.checked)}
                        className="hidden"
                    />
                    <span className={`text-xs font-medium ${isSymmetric ? 'text-blue-400' : 'text-gray-400'}`}>
                        대칭 고정
                    </span>
                </label>
            </div>

            {/* 그룹: 왼쪽 눈 (Left Eye) 제어 */}
            <div className="mb-6">
                <h3 className="text-xs uppercase tracking-wider text-pink-400 font-semibold mb-4 border-b border-white/10 pb-2">Left Eye</h3>
                <Slider
                    label="눈 크기 (Openness)" value={params.leftEye.openness} min={0} max={1} step={0.01} icon={Eye}
                    onChange={(v) => handleChange('leftEye.openness', v)}
                />
                <Slider
                    label="눈웃음 / 눈꺼풀" value={params.leftEye.smile} min={-0.3} max={0.3} step={0.01} icon={Eye}
                    onChange={(v) => handleChange('leftEye.smile', v)}
                />
                <Slider
                    label="눈 회전" value={params.leftEye.rotation} min={-30} max={30} icon={Eye}
                    onChange={(v) => handleChange('leftEye.rotation', v)}
                />
                <Slider
                    label="찡그리기 (Squeeze)" value={params.leftEye.squeeze} min={0} max={1} step={0.01} icon={Eye}
                    onChange={(v) => handleChange('leftEye.squeeze', v)}
                />
            </div>

            {/* 그룹: 오른쪽 눈 (Right Eye) 제어 */}
            <div className="mb-6">
                <h3 className="text-xs uppercase tracking-wider text-blue-400 font-semibold mb-4 border-b border-white/10 pb-2">Right Eye</h3>
                <Slider
                    label="눈 크기 (Openness)" value={params.rightEye.openness} min={0} max={1} step={0.01} icon={Eye}
                    onChange={(v) => handleChange('rightEye.openness', v)}
                />
                <Slider
                    label="눈웃음 / 눈꺼풀" value={params.rightEye.smile} min={-0.3} max={0.3} step={0.01} icon={Eye}
                    onChange={(v) => handleChange('rightEye.smile', v)}
                />
                <Slider
                    label="눈 회전" value={params.rightEye.rotation} min={-30} max={30} icon={Eye}
                    onChange={(v) => handleChange('rightEye.rotation', v)}
                />
                <Slider
                    label="찡그리기 (Squeeze)" value={params.rightEye.squeeze} min={0} max={1} step={0.01} icon={Eye}
                    onChange={(v) => handleChange('rightEye.squeeze', v)}
                />
            </div>

            {/* 그룹: 시선 (Gaze) 제어 */}
            <div className="mb-6">
                <h3 className="text-xs uppercase tracking-wider text-white/50 font-semibold mb-4 border-b border-white/10 pb-2">Gaze</h3>
                <Slider
                    label="시선 좌우 (Gaze X)" value={params.gazeX} min={-40} max={40} icon={Move}
                    onChange={(v) => handleChange('gazeX', v)}
                />
                <Slider
                    label="시선 상하 (Gaze Y)" value={params.gazeY} min={-50} max={60} icon={Move}
                    onChange={(v) => handleChange('gazeY', v)}
                />
            </div>

            {/* 그룹: 입 (Mouth) 제어 */}
            <div className="mb-6">
                <h3 className="text-xs uppercase tracking-wider text-white/50 font-semibold mb-4 border-b border-white/10 pb-2">Mouth</h3>
                <Slider
                    label="입꼬리 (미소/슬픔)" value={params.mouthCurve} min={-100} max={50} icon={MessageSquare}
                    onChange={(v) => handleChange('mouthCurve', v)}
                />
                <Slider
                    label="입 벌림" value={params.mouthOpenness} min={-29} max={31} icon={MessageSquare}
                    onChange={(v) => handleChange('mouthOpenness', v)}
                />
                <Slider
                    label="입 위치 좌우" value={params.mouthX} min={-50} max={50} icon={Move}
                    onChange={(v) => handleChange('mouthX', v)}
                />
                <Slider
                    label="입 위치 상하" value={params.mouthY} min={-50} max={50} icon={Move}
                    onChange={(v) => handleChange('mouthY', v)}
                />
                <Slider
                    label="입 오므리기 (Roundness)" value={params.mouthRoundness} min={0} max={1} step={0.01} icon={MessageSquare}
                    onChange={(v) => handleChange('mouthRoundness', v)}
                />
            </div>

            {/* 그룹: 스타일 (Styling) 및 테마 제어 */}
            <div className="mb-6">
                <h3 className="text-xs uppercase tracking-wider text-white/50 font-semibold mb-4 border-b border-white/10 pb-2">스타일 (Style)</h3>

                <div className="mb-4">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-gray-300">색상 테마</span>
                    </div>
                    <div className="flex items-center gap-3">
                        <input
                            type="color"
                            value={params.color}
                            onChange={(e) => handleChange('color', e.target.value)}
                            className="w-8 h-8 rounded-full cursor-pointer bg-transparent border border-gray-500 p-0 overflow-hidden"
                            title="Choose color"
                        />
                        <span className="text-xs font-mono text-gray-400 uppercase">{params.color}</span>
                    </div>
                </div>
            </div>

        </div>
    );
};

export default FaceController;
