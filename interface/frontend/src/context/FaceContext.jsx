import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import { EXPRESSIONS } from '../constants/expressions';

const FaceContext = createContext(null);

export const useFace = () => useContext(FaceContext);

const lerp = (start, end, factor) => start + (end - start) * factor;

const deepLerp = (current, target, factor) => {
    if (typeof target === 'number') {
        return lerp(current || 0, target, factor);
    }
    if (Array.isArray(target)) {
        return target.map((v, i) => deepLerp(current[i], v, factor));
    }
    if (typeof target === 'object' && target !== null) {
        const result = { ...(current || {}) };
        for (const key in target) {
            result[key] = deepLerp(result[key], target[key], factor);
        }
        return result;
    }
    return target;
};

export const FaceProvider = ({ children }) => {
    const activeEmotionsRef = useRef([]);
    const neutralBase = EXPRESSIONS.find(e => e.id === 'neutral').base;

    // [Manual Control State]
    // 수동 제어(슬라이더)를 위한 상태입니다. 렌더링 루프에서 Base Pose로 사용됩니다.
    const [targetValues, setTargetValues] = useState(JSON.parse(JSON.stringify(neutralBase)));
    const targetValuesRef = useRef(JSON.parse(JSON.stringify(neutralBase))); // 루프 성능용 Ref

    const [currentExprId, setCurrentExprId] = useState('neutral');
    const [renderValues, setRenderValues] = useState(neutralBase);

    const livenessRef = useRef({ blinkScale: 1.0, jitterX: 0, jitterY: 0 });
    const currentBaseRef = useRef(JSON.parse(JSON.stringify(neutralBase)));
    const currentExprIdRef = useRef('neutral'); // [New] Motion Base ID Tracking

    // Deduplication Set for Events
    const processedEventIdsRef = useRef(new Set());

    // [Handler] Manual Slider Update
    const setParams = useCallback((newParamsOrFn) => {
        setTargetValues(prev => {
            const next = typeof newParamsOrFn === 'function' ? newParamsOrFn(prev) : newParamsOrFn;
            targetValuesRef.current = next; // Ref 동기화
            return next;
        });
    }, []);

    const pushEmotion = useCallback((id, weight = 1.0, duration = 3.0) => {
        const expr = EXPRESSIONS.find(e => e.id === id);
        if (!expr) {
            console.warn(`[FaceSystem] Unknown expression signal: ${id}`);
            return;
        }

        console.log(`[FaceSystem] Emotion Impulse: ${id} (w=${weight}, d=${duration})`);

        // UI 상태 업데이트 (현재 표정 표시용)
        setCurrentExprId(id);

        const now = Date.now();
        const existingIdx = activeEmotionsRef.current.findIndex(e => e.id === id);

        if (existingIdx >= 0) {
            activeEmotionsRef.current[existingIdx] = {
                id,
                base: expr.base,
                motion: expr.motion,
                weight: Math.max(activeEmotionsRef.current[existingIdx].weight, weight),
                decaySpeed: 1.0 / duration,
                lastUpdate: now
            };
        } else {
            activeEmotionsRef.current.push({
                id,
                base: expr.base,
                motion: expr.motion,
                weight: weight,
                decaySpeed: 1.0 / duration,
                lastUpdate: now
            });
        }
    }, []);

    // [Handler] Preset Button Click
    const setExpression = useCallback((id) => {
        // 프리셋 버튼 클릭 시:
        // 1. 해당 프리셋의 Base 값을 슬라이더(TargetValues)에 적용하여 '기본 상태'로 만듭니다.
        // 2. 기존의 Overlay 감정들을 모두 제거합니다. (Reset)
        // 3. 현재 프리셋 ID를 업데이트하여 Loop에서 해당 Motion을 사용하게 합니다.
        const expr = EXPRESSIONS.find(e => e.id === id);
        if (expr) {
            setTargetValues(expr.base);
            targetValuesRef.current = JSON.parse(JSON.stringify(expr.base));

            // UI 및 루프 참조 업데이트
            setCurrentExprId(id);
            currentExprIdRef.current = id;

            // 기존 감정 모두 제거 (Clean Slate)
            activeEmotionsRef.current = [];
        }
    }, []);

    // [Liveness Loop] Blinking & Saccades
    useEffect(() => {
        const interval = setInterval(() => {
            const now = Date.now();

            // 1. Blink Logic
            // 2~5초마다 한번씩 눈 깜빡임
            if (Math.random() < 0.05) {
                livenessRef.current.blinkScale = 0.0;
                setTimeout(() => { livenessRef.current.blinkScale = 1.0; }, 150);
            }

            // 2. Micro Saccades (Jitter)
            // 아주 미세하게 눈동자가 떨림
            livenessRef.current.jitterX = (Math.random() - 0.5) * 2.0;
            livenessRef.current.jitterY = (Math.random() - 0.5) * 2.0;

        }, 100); // 10Hz Update

        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        window.pushEmotion = pushEmotion;
        window.setFace = (id) => pushEmotion(id, 1.0, 5.0);
        return () => {
            delete window.pushEmotion;
            delete window.setFace;
        };
    }, [pushEmotion]);

    useEffect(() => {
        const wsUrl = "ws://localhost:8000/ws";
        let socket;
        let retryTimeout;

        const connect = () => {
            socket = new WebSocket(wsUrl);
            socket.onopen = () => console.log("[FaceSystem] Signal Line Connected.");

            socket.onmessage = (event) => {
                try {
                    const packet = JSON.parse(event.data);

                    // [Event Buffer Consumption]
                    const events = packet.brain?.events || [];

                    events.forEach(evt => {
                        if (!processedEventIdsRef.current.has(evt.id)) {
                            processedEventIdsRef.current.add(evt.id);

                            // Set Clean-up (Prevent Memory Leak)
                            if (processedEventIdsRef.current.size > 200) {
                                processedEventIdsRef.current = new Set(Array.from(processedEventIdsRef.current).slice(-50));
                            }

                            if (evt.type === 'emotion_pulse') {
                                const { preset, weight, duration } = evt.payload;
                                console.log(`[Event] Consuming Emotion Pulse: ${preset} (${evt.id})`);
                                pushEmotion(preset, weight, duration);
                            }
                        }
                    });

                } catch (e) { }
            };

            socket.onclose = () => {
                retryTimeout = setTimeout(connect, 3000);
            };
        };
        connect();
        return () => { if (socket) socket.close(); if (retryTimeout) clearTimeout(retryTimeout); };
    }, [pushEmotion]);

    useEffect(() => {
        let frameId;
        const startTime = Date.now();
        let lastTime = startTime;

        const loop = () => {
            const now = Date.now();
            const dt = (now - lastTime) / 1000;
            lastTime = now;
            const elapsed = (now - startTime) / 1000;

            // Decay Emotions
            activeEmotionsRef.current.forEach(e => {
                e.weight -= e.decaySpeed * dt;
            });
            activeEmotionsRef.current = activeEmotionsRef.current.filter(e => e.weight > 0);

            // Calculate Weights
            let totalWeight = activeEmotionsRef.current.reduce((acc, e) => acc + e.weight, 0);
            totalWeight = Math.min(1.0, totalWeight);
            const baseWeight = 1.0 - totalWeight;

            // Helper Functions
            const mixParams = (target, source, weight) => {
                Object.keys(source).forEach(key => {
                    if (typeof source[key] === 'number') {
                        target[key] = (target[key] || 0) + source[key] * weight;
                    } else if (typeof source[key] === 'object' && source[key] !== null) {
                        if (!target[key]) target[key] = {};
                        mixParams(target[key], source[key], weight);
                    }
                });
            };

            const multiplyParams = (src, factor) => {
                const res = Array.isArray(src) ? [] : {};
                Object.keys(src).forEach(key => {
                    if (typeof src[key] === 'number') {
                        res[key] = src[key] * factor;
                    } else if (typeof src[key] === 'object' && src[key] !== null) {
                        res[key] = multiplyParams(src[key], factor);
                    } else {
                        res[key] = src[key];
                    }
                });
                return res;
            };

            // 1. Base Pose Calculation
            // [Modified] 고정된 neutralBase 대신, 사용자가 슬라이더로 조작 중인 targetValuesRef를 Base로 사용합니다.
            const targetPose = multiplyParams(targetValuesRef.current, baseWeight);

            // 2. Add Active Emotions
            activeEmotionsRef.current.forEach(emotion => {
                mixParams(targetPose, emotion.base, emotion.weight);
            });

            // 3. Color Logic
            if (activeEmotionsRef.current.length > 0) {
                const dominant = activeEmotionsRef.current.reduce((prev, curr) => prev.weight > curr.weight ? prev : curr);
                if (dominant.base.color) targetPose.color = dominant.base.color;
            } else {
                targetPose.color = targetValuesRef.current.color || neutralBase.color;
            }

            // 4. Smooth & Motion
            const smoothFactor = 5.0 * dt;
            currentBaseRef.current = deepLerp(currentBaseRef.current, targetPose, smoothFactor);

            const motionOffsets = {};
            // [Modified] Motion Base Selection
            // 기존에는 neutralExpr.motion만 사용했으나, 이제는 '현재 선택된 프리셋'의 모션을 Base로 사용합니다.
            const currentExpr = EXPRESSIONS.find(e => e.id === currentExprIdRef.current) || neutralExpr;
            const calcWave = (m) => Math.sin(elapsed * m.freq * Math.PI * 2) * m.amp;

            const addMotion = (target, motionDef, weight = 1.0) => {
                const recurse = (tgt, def) => {
                    Object.entries(def).forEach(([key, value]) => {
                        if (key === 'all') {
                            const val = (Math.random() - 0.5) * value.amp * weight;
                            tgt.gazeX = (tgt.gazeX || 0) + val;
                            tgt.gazeY = (tgt.gazeY || 0) + val;
                        } else if (typeof value === 'object' && !value.amp) {
                            if (!tgt[key]) tgt[key] = {};
                            recurse(tgt[key], value);
                        } else {
                            tgt[key] = (tgt[key] || 0) + calcWave(value) * weight;
                        }
                    });
                };
                recurse(target, motionDef);
            };

            if (currentExpr?.motion) addMotion(motionOffsets, currentExpr.motion, 0.5);

            activeEmotionsRef.current.forEach(e => {
                if (e.motion) addMotion(motionOffsets, e.motion, e.weight);
            });

            const finalValues = JSON.parse(JSON.stringify(currentBaseRef.current));

            const applyOffset = (tgt, off) => {
                Object.keys(off).forEach(k => {
                    if (typeof off[k] === 'object') {
                        if (!tgt[k]) tgt[k] = {};
                        applyOffset(tgt[k], off[k]);
                    } else if (typeof off[k] === 'number') {
                        tgt[k] = (tgt[k] || 0) + off[k];
                    }
                });
            };
            applyOffset(finalValues, motionOffsets);

            finalValues.gazeX += livenessRef.current.jitterX;
            finalValues.gazeY += livenessRef.current.jitterY;
            if (finalValues.leftEye) finalValues.leftEye.openness *= livenessRef.current.blinkScale;
            if (finalValues.rightEye) finalValues.rightEye.openness *= livenessRef.current.blinkScale;

            setRenderValues(finalValues);
            frameId = requestAnimationFrame(loop);
        };

        frameId = requestAnimationFrame(loop);
        return () => cancelAnimationFrame(frameId);
    }, []);

    return (
        <FaceContext.Provider value={{
            pushEmotion,
            renderValues,
            isReady: true,
            // [Restored Debug Props]
            targetValues,
            setParams,
            currentExprId,
            setExpression
        }}>
            {children}
        </FaceContext.Provider>
    );
};
