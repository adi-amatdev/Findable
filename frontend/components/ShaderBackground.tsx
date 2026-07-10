"use client";

import { useEffect, useRef, forwardRef, useImperativeHandle } from "react";
import * as THREE from "three";

const vertexShader = `
  uniform float uTime;
  uniform float uPulse;
  uniform float uSeed;
  varying vec2 vUv;
  varying float vElevation;
  varying float vLuminosity;
  varying vec3 vWorldPos;

  float hash3(vec3 p) {
    return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453);
  }
  float noise3(vec3 p) {
    vec3 i = floor(p);
    vec3 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    float a = hash3(i);
    float b = hash3(i + vec3(1,0,0));
    float c = hash3(i + vec3(0,1,0));
    float d = hash3(i + vec3(1,1,0));
    float e = hash3(i + vec3(0,0,1));
    float ff = hash3(i + vec3(1,0,1));
    float g = hash3(i + vec3(0,1,1));
    float h = hash3(i + vec3(1,1,1));
    return mix(mix(mix(a,b,f.x), mix(c,d,f.x), f.y),
               mix(mix(e,ff,f.x), mix(g,h,f.x), f.y), f.z);
  }
  float fbm(vec3 p) {
    float v = 0.0;
    float a = 0.5;
    for (int i = 0; i < 4; i++) {
      v += a * noise3(p);
      p *= 2.0;
      a *= 0.5;
    }
    return v;
  }

  void main() {
    vUv = uv;
    vec3 pos = position;
    float pulse = uPulse;
    float seed = uSeed;
    float t = uTime;

    // === DOWNWARD FLOW: positive = downward in wave phase ===
    float flowSpeed = 0.8 + pulse * 1.2;
    float flow = t * flowSpeed;

    // === STREAM CURVES: meandering horizontal offset along a vertical path ===
    // Like a river bending left and right as it flows down
    float meander1 = sin(pos.y * 0.6 + t * 0.12 + seed) * 1.8;
    float meander2 = sin(pos.y * 0.25 + t * 0.06 + seed * 2.3) * 0.9;
    float meanderX = meander1 + meander2;

    // === VERTICAL BANDS: broad stripes flowing downward, curving with meander ===
    float band1 = sin((pos.x + meanderX * 0.4) * 0.8 + flow * 0.5 + seed) * 0.6;
    float band2 = sin((pos.x + meanderX * 0.25) * 0.45 - flow * 0.35 + seed * 1.7) * 0.5;
    float band3 = sin((pos.x + meanderX * 0.6) * 1.1 + flow * 0.7 + seed * 3.1) * 0.35;

    // === WIDE CURTAIN: very broad shape that breathes ===
    float curtain = sin(pos.x * 0.15 + meanderX * 0.1 + t * 0.04 + seed * 0.8) * 0.7;

    // === VERTICAL FADE: full screen, gentle top/bottom ===
    float vertFade = smoothstep(-1.8, 0.2, uv.y) * smoothstep(1.8, 0.2, uv.y);

    // === ELEVATION ===
    float elevation = (band1 + band2 + band3 + curtain) * vertFade;
    elevation *= (1.0 + pulse * 0.8);

    // === 3D NOISE: soft organic displacement, mostly vertical ===
    vec3 noiseCoord = vec3(pos.xy * 0.15 + seed * 10.0, flow * 0.08);
    float n1 = fbm(noiseCoord) * 2.0 - 1.0;
    float n2 = fbm(noiseCoord + vec3(5.2, 1.3, 2.8)) * 2.0 - 1.0;
    float n3 = fbm(noiseCoord + vec3(9.7, 4.1, 6.3)) * 2.0 - 1.0;

    float chaosMix = 0.1 + pulse * 0.9;

    // Gentle horizontal sway from noise
    pos.x += n1 * 0.2 * chaosMix * vertFade;
    // Slight vertical compression during flow
    pos.y += n2 * 0.06 * chaosMix * vertFade;
    // Depth undulation — broad, not fine
    pos.z += n3 * 0.35 * chaosMix * vertFade;

    // === PULSE: wave swing and twist ===
    float pulseSwing = sin(pos.y * 0.8 + t * 0.3 + seed * 4.0) * pulse * 0.25;
    pos.x += pulseSwing * vertFade;

    float twist = sin(pos.y * 0.7 + t * 0.15) * pulse * 0.12 * vertFade;
    pos.x += twist;

    // === LUMINOSITY: broad flowing zones ===
    float lumNoise = fbm(vec3(pos.xy * 0.1, flow * 0.06 + seed));
    vLuminosity = lumNoise * (0.6 + pulse * 1.4);

    elevation += n3 * 0.18 * chaosMix * vertFade;
    vElevation = elevation;
    vWorldPos = pos;

    gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
  }
`;

const fragmentShader = `
  uniform float uTime;
  uniform float uPulse;
  uniform vec3 uBaseColor;
  uniform vec3 uPeakColor;
  uniform float uSeed;
  varying vec2 vUv;
  varying float vElevation;
  varying float vLuminosity;
  varying vec3 vWorldPos;

  float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
  }
  float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    float a = hash(i);
    float b = hash(i + vec2(1.0, 0.0));
    float c = hash(i + vec2(0.0, 1.0));
    float d = hash(i + vec2(1.0, 1.0));
    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
  }
  float fbm2(vec2 p) {
    float v = 0.0;
    float a = 0.5;
    for (int i = 0; i < 3; i++) {
      v += a * noise(p);
      p *= 1.8;
      a *= 0.48;
    }
    return v;
  }

  void main() {
    float pulse = uPulse;
    float seed = uSeed;
    float t = uTime;

    float flowSpeed = 0.8 + pulse * 1.2;
    float flow = t * flowSpeed;

    // Meander for band alignment
    float meander1 = sin(vWorldPos.y * 0.6 + t * 0.12 + seed) * 1.8;
    float meander2 = sin(vWorldPos.y * 0.25 + t * 0.06 + seed * 2.3) * 0.9;
    float meanderX = meander1 + meander2;

    // === BASE COLOR ===
    vec3 color = mix(uBaseColor, uPeakColor, pulse * 0.5);

    // === LUMINOSITY ZONES: soft flowing blobs ===
    vec2 lumCoord = vWorldPos.xy * 0.12 + seed * 7.0;
    float hotSpot1 = fbm2(lumCoord + vec2(meanderX * 0.02, flow * 0.05));
    float hotSpot2 = fbm2(lumCoord * 1.3 + vec2(-meanderX * 0.015, flow * 0.04) + 3.14);
    float hotSpot3 = noise(lumCoord * 1.8 + vec2(t * 0.03, flow * 0.03));

    float luminosity = hotSpot1 * 0.5 + hotSpot2 * 0.3 + hotSpot3 * 0.2;
    luminosity = luminosity * (0.5 + pulse * 1.0);

    // === BROAD BANDS: smooth river-like highlights ===
    float bandA = sin((vWorldPos.x + meanderX * 0.4) * 0.8 + flow * 0.5 + seed);
    float bandB = sin((vWorldPos.x + meanderX * 0.25) * 0.45 - flow * 0.35 + seed * 1.7);
    float bandC = sin((vWorldPos.x + meanderX * 0.6) * 1.1 + flow * 0.7 + seed * 3.1);

    float bandVal = smoothstep(0.1, 0.9, bandA) * 0.4
                  + smoothstep(0.2, 0.95, bandB) * 0.35
                  + smoothstep(0.0, 0.85, bandC) * 0.25;
    float bandBrightness = bandVal * (0.3 + pulse * 1.0);

    // === ELEVATION GLOW ===
    float elevGlow = smoothstep(-0.5, 1.0, vElevation);

    // === COLOR TEMPERATURE: warm peaks, cool valleys ===
    vec3 warmTint = vec3(1.06, 0.96, 0.82);
    vec3 coolTint = vec3(0.86, 0.92, 1.06);
    float tempMix = smoothstep(-0.2, 0.5, vElevation + luminosity * 0.25);
    vec3 tempTint = mix(coolTint, warmTint, tempMix);

    // === APPLY ===
    color *= tempTint;
    color += elevGlow * luminosity * vec3(0.2, 0.16, 0.08) * (1.0 + pulse * 1.5);
    color += bandBrightness * vec3(0.3, 0.24, 0.1);

    // === VERTICAL GRADIENT: dimmer at bottom for depth ===
    float vertGrad = mix(0.5, 1.0, vUv.y);
    color *= vertGrad;

    // === ALPHA: low for text visibility, pulse adds gentle fullness ===
    float alpha = mix(0.03, 0.12, pulse);
    alpha += elevGlow * 0.04;
    alpha += bandBrightness * 0.03;
    alpha *= (0.6 + luminosity * 0.4);
    alpha *= vertGrad;

    gl_FragColor = vec4(color, alpha);
  }
`;

export interface ShaderBackgroundHandle {
  triggerPulse: (intensity?: number, duration?: number) => void;
}

interface PulseState {
  active: boolean;
  start: number;
  buildDuration: number;
  holdDuration: number;
  decayDuration: number;
}

const ShaderBackground = forwardRef<ShaderBackgroundHandle>(function ShaderBackground(_, ref) {
  const containerRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef<number>(0);
  const pulseRef = useRef<PulseState>({
    active: false,
    start: 0,
    buildDuration: 3000,
    holdDuration: 400,
    decayDuration: 4000,
  });

  useImperativeHandle(ref, () => ({
    triggerPulse(_intensity = 0.7, duration = 6000) {
      pulseRef.current = {
        active: true,
        start: performance.now(),
        buildDuration: duration * 0.45,
        holdDuration: duration * 0.1,
        decayDuration: duration * 0.45,
      };
    },
  }));

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(
      50,
      window.innerWidth / window.innerHeight,
      0.1,
      100
    );
    camera.position.set(0, 0, 5);

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: "high-performance",
    });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x0c0806, 1);
    container.appendChild(renderer.domElement);

    const clock = new THREE.Clock();

    const layers = [
      { z: -1.5, yOff: 0.4, hue: 34, sat: 48, light: 26, scaleX: 1.6, scaleY: 2.0, seed: 0.0 },
      { z: -0.8, yOff: 0.15, hue: 38, sat: 56, light: 32, scaleX: 1.2, scaleY: 1.4, seed: 1.7 },
      { z: -0.1, yOff: -0.05, hue: 42, sat: 62, light: 40, scaleX: 1.0, scaleY: 1.0, seed: 3.4 },
      { z: 0.6,  yOff: -0.35, hue: 36, sat: 50, light: 30, scaleX: 1.3, scaleY: 1.6, seed: 5.1 },
      { z: 1.2,  yOff: -0.6, hue: 32, sat: 44, light: 24, scaleX: 1.7, scaleY: 2.2, seed: 7.8 },
    ];

    const meshes: THREE.Mesh[] = [];

    layers.forEach((cfg) => {
      const geometry = new THREE.PlaneGeometry(14, 10, 160, 80);
      const material = new THREE.ShaderMaterial({
        transparent: true,
        side: THREE.DoubleSide,
        depthWrite: false,
        blending: THREE.NormalBlending,
        uniforms: {
          uTime: { value: 0 },
          uPulse: { value: 0 },
          uSeed: { value: cfg.seed },
          uBaseColor: { value: new THREE.Color().setHSL(cfg.hue / 360, cfg.sat / 100, cfg.light / 100) },
          uPeakColor: { value: new THREE.Color().setHSL(cfg.hue / 360, (cfg.sat + 12) / 100, (cfg.light + 22) / 100) },
        },
        vertexShader,
        fragmentShader,
      });

      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.set(0, cfg.yOff, cfg.z);
      mesh.scale.set(cfg.scaleX, cfg.scaleY, 1);
      scene.add(mesh);
      meshes.push(mesh);
    });

    const onResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };
    window.addEventListener("resize", onResize);

    const tick = () => {
      const elapsed = clock.getElapsedTime();

      let pulse = 0;
      const p = pulseRef.current;
      if (p.active) {
        const now = performance.now();
        const pElapsed = (now - p.start) / 1000;
        const total = p.buildDuration / 1000 + p.holdDuration / 1000 + p.decayDuration / 1000;
        if (pElapsed >= total) {
          p.active = false;
        } else {
          const buildEnd = p.buildDuration / 1000;
          const holdEnd = buildEnd + p.holdDuration / 1000;
          if (pElapsed < buildEnd) {
            const t = pElapsed / buildEnd;
            pulse = (1 - Math.cos(t * Math.PI)) / 2;
          } else if (pElapsed < holdEnd) {
            pulse = 1;
          } else {
            const t = (pElapsed - holdEnd) / (p.decayDuration / 1000);
            const t2 = 1 - t;
            pulse = 1 - (1 - t2 * t2 * t2);
          }
        }
      }

      meshes.forEach((mesh) => {
        const mat = mesh.material as THREE.ShaderMaterial;
        mat.uniforms.uTime.value = elapsed;
        mat.uniforms.uPulse.value += (pulse - mat.uniforms.uPulse.value) * 0.04;
      });

      renderer.render(scene, camera);
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(rafRef.current);
      window.removeEventListener("resize", onResize);
      meshes.forEach((m) => {
        m.geometry.dispose();
        (m.material as THREE.ShaderMaterial).dispose();
      });
      renderer.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, []);

  return (
    <div
      style={{ position: "fixed", inset: 0, overflow: "hidden", zIndex: 0 }}
    >
      <div
        ref={containerRef}
        style={{ position: "absolute", inset: 0 }}
      />
    </div>
  );
});

export default ShaderBackground;
