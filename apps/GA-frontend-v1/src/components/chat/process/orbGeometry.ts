/**
 * Orbs（aicss.dev）G1「Globe spin」几何预计算
 *
 * 40 个点（5 条纬度环 × 8 点）按 28px 舞台绘制，由 CSS 的 --orb-k 缩放到显示尺寸。
 * 8 个姿势在模块作用域一次性算好，写进每点的 --g0…--g7 变量，运行时零计算。
 *
 * 原先内联在 ChatMessage.vue 中，现抽出为共享模块，
 * 由 ThinkingState 复用，覆盖首次等待、普通思考和 Agent 分段思考。
 */

const GLOBE_R = 8.5;
const GLOBE_TILT = (14 * Math.PI) / 180;

const GLOBE_RINGS = [
  { lat: 52, count: 8 },
  { lat: 26, count: 8 },
  { lat: 0, count: 8 },
  { lat: -26, count: 8 },
  { lat: -52, count: 8 },
];

/** G1 节奏：一整圈均匀切成 8 个姿势，每步自转 45°，不做缩放 */
const GLOBE_STEPS = 8;

/** 先绕 Y 轴自转 spin，再绕 X 轴倾斜 GLOBE_TILT 投影到屏幕 */
function projectGlobe(x: number, y: number, z: number, spin: number) {
  const cs = Math.cos(spin);
  const ss = Math.sin(spin);
  const x1 = x * cs - z * ss;
  const z1 = x * ss + z * cs;
  const ct = Math.cos(GLOBE_TILT);
  const st = Math.sin(GLOBE_TILT);
  return { x: x1, y: y * ct - z1 * st, z: y * st + z1 * ct };
}

/** 深度着色：背面的点压暗到 0.12，正面的点趋近 1，转出立体感 */
function globeOpacity(z: number) {
  const t = Math.max(0, Math.min(1, (z / GLOBE_R + 0.15) / 1.15));
  return 0.12 + 0.88 * t * t;
}

export interface OrbDot {
  key: number;
  style: Record<string, string>;
}

export const orbDots: OrbDot[] = (() => {
  const dots: OrbDot[] = [];
  let idx = 0;
  for (const ring of GLOBE_RINGS) {
    const latRad = (ring.lat * Math.PI) / 180;
    const y0 = Math.sin(latRad) * GLOBE_R;
    const ringR = Math.cos(latRad) * GLOBE_R;
    for (let j = 0; j < ring.count; j++) {
      const lon = (j / ring.count) * Math.PI * 2;
      const x0 = Math.cos(lon) * ringR;
      const z0 = Math.sin(lon) * ringR;
      const style: Record<string, string> = {};
      for (let k = 0; k < GLOBE_STEPS; k++) {
        const spin = (k / GLOBE_STEPS) * Math.PI * 2;
        const p = projectGlobe(x0, y0, z0, spin);
        style[`--g${k}x`] = `${p.x.toFixed(2)}px`;
        // 屏幕 y 轴向下，取反让北极朝上
        style[`--g${k}y`] = `${(-p.y).toFixed(2)}px`;
        style[`--g${k}o`] = globeOpacity(p.z).toFixed(3);
      }
      dots.push({ key: idx++, style });
    }
  }
  return dots;
})();
