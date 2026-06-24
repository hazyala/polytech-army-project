import { motion } from 'framer-motion';

const Mouth = ({
    x = 200, // 가로 중앙 좌표
    y = 280, // 세로 기준 좌표
    width = 80,
    curve = 0, // -100 (슬픔/찡그림)에서 100 (행복/웃음) 사이의 곡률
    openness = 0, // 0 (다묾)에서 100 (벌림/놀람) 사이의 개방 정도
    roundness = 0, // 0 (넓은 타원)에서 1 (동그란 O형) 사이의 정도
    color = "#FFFFFF",
    glowIntensity = 0.5
}) => {

    // 베지어 곡선 제어점 (Bezier Control Points)
    // roundness가 높을수록 너비를 좁힙니다.
    const effectiveWidth = width * (1 - roundness * 0.5);

    // 시작 및 끝점 계산
    const startX = x - effectiveWidth / 2;
    const endX = x + effectiveWidth / 2;

    // 제어점 (곡률 결정)
    const controlY = y + (curve * 1.5) + openness;

    // 단순한 선 또는 곡선 (입을 다물었을 때)
    const dClosed = `M ${startX} ${y} Q ${x} ${controlY} ${endX} ${y}`;

    let d = dClosed;
    if (openness > 10) {
        const upperControlShift = (openness * 0.5) * roundness;
        const upperControlY = y + (curve * 0.5) - upperControlShift;
        const lowerControlY = y + openness + (curve * 0.5) + upperControlShift;

        d = `M ${startX} ${y} 
           Q ${x} ${upperControlY} ${endX} ${y}
           Q ${x} ${lowerControlY} ${startX} ${y}`;
    }

    return (
        <motion.path
            d={d}
            stroke={color}
            strokeWidth={openness > 10 ? 0 : 8}
            fill={openness > 10 ? color : "transparent"}
            strokeLinecap="round"
            strokeLinejoin="round"

            animate={{
                d: d,
                stroke: color,
                fill: openness > 10 ? color : "transparent",
                filter: `drop-shadow(0 0 ${glowIntensity * 20}px ${color})`
            }}
            transition={{
                type: "spring",
                stiffness: 300,
                damping: 30
            }}

            style={{
                strokeWidth: openness > 10 ? 0 : 8
            }}
        />
    );
};

export default Mouth;
