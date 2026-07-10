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

    float wave1 = sin(pos.x * 1.1 + pos.y * 0.4 + t * 0.25 + seed) * 0.45;
    float wave2 = sin(pos.x * 0.6 - pos.y * 0.8 + t * 0.12 + seed * 2.1) * 0.32;
    float wave3 = sin(pos.x * 2.5 + pos.y * 1.2 + t * 0.5 + seed * 0.7) * 0.18;
    float wave4 = sin(pos.x * 3.8 - pos.y * 0.5 + t * 0.7 + seed * 3.3) * 0.10;
    float wave5 = sin(pos.x * 1.8 + pos.y * 2.2 + t * 0.35 + seed * 4.1) * 0.22;
    float wave6 = sin(pos.x * 0.4 - pos.y * 0.3 + t * 0.08 + seed * 1.3) * 0.40;
    float wave7 = sin(pos.x * 5.2 + pos.y * 0.9 + t * 0.9 + seed * 2.7) * 0.08;
    float wave8 = sin(pos.x * 0.9 - pos.y * 1.6 + t * 0.18 + seed * 5.5) * 0.28;

    float streakNoise1 = sin(pos.x * 7.0 + pos.y * 3.0 + t * 0.4 + seed * 6.0);
    float streak1 = pow(max(streakNoise1, 0.0), 8.0) * 0.5;
    float streakNoise2 = sin(pos.x * 4.0 - pos.y * 5.0 + t * 0.25 + seed * 3.0);
    float streak2 = pow(max(streakNoise2, 0.0), 10.0) * 0.4;
    float streakNoise3 = sin(pos.x * 9.0 + pos.y * 1.5 + t * 0.6 + seed * 8.0);
    float streak3 = pow(max(streakNoise3, 0.0), 12.0) * 0.3;

    float vertFade = smoothstep(-1.2, -0.2, uv.y) * smoothstep(1.2, 0.3, uv.y);

    float elevation = (wave1 + wave2 + wave3 + wave4 + wave5 + wave6 + wave7 + wave8) * vertFade;
    elevation += (streak1 + streak2 + streak3) * vertFade;
    elevation *= (1.0 + pulse * 1.5);

    vec3 noiseCoord = vec3(pos.xy * 0.4 + seed * 10.0, t * 0.08);
    float n1 = fbm(noiseCoord) * 2.0 - 1.0;
    float n2 = fbm(noiseCoord + vec3(5.2, 1.3, 2.8)) * 2.0 - 1.0;
    float n3 = fbm(noiseCoord + vec3(9.7, 4.1, 6.3)) * 2.0 - 1.0;

    float chaosMix = 0.12 + pulse * 0.88;

    pos.x += n1 * 0.18 * chaosMix * vertFade;
    pos.y += n2 * 0.10 * chaosMix * vertFade;
    pos.z += n3 * 0.30 * chaosMix * vertFade;

    float diagChaos = sin(pos.x * 3.0 + pos.y * 2.5 + t * 0.8 + seed * 5.0) * pulse * 0.2;
    pos.z += diagChaos * vertFade;

    float twist = sin(pos.y * 1.5 + t * 0.3) * pulse * 0.12 * vertFade;
    pos.x += twist;

    float lumNoise = fbm(vec3(pos.xy * 0.3, t * 0.06 + seed));
    vLuminosity = lumNoise * (0.7 + pulse * 1.3);

    float streakLum = streak1 * 0.6 + streak2 * 0.4 + streak3 * 0.3;
    vLuminosity += streakLum * (0.5 + pulse * 1.5);

    elevation += n3 * 0.15 * chaosMix * vertFade;
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
      p *= 2.1;
      a *= 0.48;
    }
    return v;
  }

  void main() {
    float pulse = uPulse;
    float seed = uSeed;
    float t = uTime;

    vec3 color = mix(uBaseColor, uPeakColor, pulse * 0.7);

    vec2 lumCoord = vWorldPos.xy * 0.25 + seed * 7.0;
    float hotSpot1 = fbm2(lumCoord + vec2(t * 0.04, t * 0.03));
    float hotSpot2 = fbm2(lumCoord * 1.7 + vec2(-t * 0.03, t * 0.05) + 3.14);
    float hotSpot3 = noise(lumCoord * 3.0 + vec2(t * 0.08, -t * 0.02));

    float luminosity = hotSpot1 * 0.5 + hotSpot2 * 0.3 + hotSpot3 * 0.2;
    luminosity = luminosity * (0.7 + pulse * 1.3);

    float streakA = sin(vWorldPos.x * 7.0 + vWorldPos.y * 3.0 + t * 0.4 + seed * 6.0);
    float streakB = sin(vWorldPos.x * 4.0 - vWorldPos.y * 5.0 + t * 0.25 + seed * 3.0);
    float streakC = sin(vWorldPos.x * 9.0 + vWorldPos.y * 1.5 + t * 0.6 + seed * 8.0);

    float streakVal = pow(max(streakA, 0.0), 10.0) * 0.5
                    + pow(max(streakB, 0.0), 12.0) * 0.4
                    + pow(max(streakC, 0.0), 14.0) * 0.3;
    float streakBrightness = streakVal * (0.6 + pulse * 2.0);

    float elevGlow = smoothstep(-0.4, 1.0, vElevation);

    vec3 warmTint = vec3(1.08, 0.95, 0.78);
    vec3 coolTint = vec3(0.82, 0.90, 1.08);
    float tempMix = smoothstep(-0.3, 0.6, vElevation + luminosity * 0.3);
    vec3 tempTint = mix(coolTint, warmTint, tempMix);

    color *= tempTint;
    color += elevGlow * luminosity * vec3(0.25, 0.2, 0.1) * (1.0 + pulse * 2.0);
    color += streakBrightness * vec3(0.35, 0.28, 0.12);

    float grain = noise(vUv * 15.0 + t * 0.02 + seed) * 0.05;
    color += grain;

    float vertGrad = mix(0.55, 1.0, vUv.y);
    color *= vertGrad;

    float alpha = mix(0.04, 0.16, pulse);
    alpha += elevGlow * 0.06;
    alpha += streakBrightness * 0.04;
    alpha *= (0.75 + luminosity * 0.5);
    alpha *= vertGrad;

    gl_FragColor = vec4(color, alpha);
  }
`;

export interface ShaderBackgroundHandle {
  /** Trigger a chaos pulse. Intensity 0-1 (default 0.7), duration in ms (default 6000) */
  triggerPulse: (intensity?: number, duration?: number) => void;
}

interface PulseState {
  active: boolean;
  start: number;
  buildDuration: number;
  holdDuration: number;
  decayDuration: number;
  targetIntensity: number;
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
    targetIntensity: 0.7,
  });

  useImperativeHandle(ref, () => ({
    triggerPulse(intensity = 0.7, duration = 6000) {
      pulseRef.current = {
        active: true,
        start: performance.now(),
        buildDuration: duration * 0.45,
        holdDuration: duration * 0.1,
        decayDuration: duration * 0.45,
        targetIntensity: intensity,
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
          pulse *= p.targetIntensity;
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
