"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";

export type BackgroundMode = "calm" | "processing";

interface ShaderBackgroundProps {
  mode: BackgroundMode;
}

const MAX_PULSES = 5;

const nebulaVertexShader = `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = vec4(position, 1.0);
  }
`;

const nebulaFragmentShader = `
  uniform float uTime;
  uniform float uMotion;
  uniform vec3 uPulseCenters[${MAX_PULSES}];
  varying vec2 vUv;

  float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
  }

  float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), f.x),
      mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), f.x), f.y);
  }

  float fbm(vec2 p) {
    float value = 0.0;
    float amplitude = 0.5;
    for (int i = 0; i < 4; i++) {
      value += amplitude * noise(p);
      p = p * 2.03 + vec2(17.2, 9.1);
      amplitude *= 0.5;
    }
    return value;
  }

  float cluster(vec2 uv, vec2 center, vec2 radius) {
    vec2 delta = (uv - center) / radius;
    return exp(-dot(delta, delta) * 3.2);
  }

  void main() {
    vec2 uv = vUv;
    float drift = uTime * 0.012 * uMotion;
    vec2 flow = vec2(drift, -drift * 0.38);

    float cloud = 0.0;
    cloud += cluster(uv, vec2(0.24, 0.27), vec2(0.34, 0.18));
    cloud += cluster(uv, vec2(0.71, 0.64), vec2(0.42, 0.23)) * 0.9;
    cloud += cluster(uv, vec2(0.56, 0.14), vec2(0.28, 0.13)) * 0.65;
    cloud += cluster(uv, vec2(0.07, 0.77), vec2(0.24, 0.19)) * 0.55;

    float texture = fbm(uv * vec2(4.8, 6.2) + flow);
    float detail = fbm(uv * vec2(12.0, 9.0) - flow * 1.5);
    float dust = smoothstep(0.36, 0.78, texture) * cloud;
    dust *= 0.42 + detail * 0.78;

    float pulseGlow = 0.0;
    for (int i = 0; i < ${MAX_PULSES}; i++) {
      vec3 pulse = uPulseCenters[i];
      float distanceFromPulse = distance(uv, pulse.xy);
      pulseGlow += pulse.z * exp(-distanceFromPulse * distanceFromPulse * 95.0);
    }

    vec3 black = vec3(0.018, 0.013, 0.009);
    vec3 umber = vec3(0.16, 0.097, 0.035);
    vec3 gold = vec3(0.78, 0.53, 0.20);
    vec3 color = mix(black, umber, dust * 0.78);
    color += gold * dust * 0.22;
    color += gold * pulseGlow * (0.22 + dust * 0.52);

    float vignette = smoothstep(1.05, 0.26, distance(uv, vec2(0.5)));
    color *= 0.48 + vignette * 0.52;
    gl_FragColor = vec4(color, 1.0);
  }
`;

const starsVertexShader = `
  attribute float aSize;
  attribute float aPhase;
  attribute float aCluster;
  uniform float uTime;
  uniform float uMotion;
  uniform vec3 uPulseCenters[${MAX_PULSES}];
  varying float vBrightness;

  void main() {
    vec3 pos = position;
    float movement = sin(uTime * (0.12 + aPhase * 0.08) + aPhase * 17.0);
    pos.xy += vec2(movement * 0.025, cos(uTime * 0.1 + aPhase * 11.0) * 0.018) * uMotion;

    vec4 clipPosition = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
    vec2 screenUv = clipPosition.xy / clipPosition.w * 0.5 + 0.5;
    float pulseGlow = 0.0;
    for (int i = 0; i < ${MAX_PULSES}; i++) {
      vec3 pulse = uPulseCenters[i];
      vec2 delta = screenUv - pulse.xy;
      pulseGlow += pulse.z * exp(-dot(delta, delta) * 135.0);
    }

    vBrightness = 0.34 + aCluster * 0.43 + pulseGlow * 1.15;
    float twinkle = 0.82 + sin(uTime * (0.9 + aPhase) + aPhase * 41.0) * 0.18;
    gl_PointSize = aSize * (1.0 + pulseGlow * 1.8) * twinkle;
    gl_Position = clipPosition;
  }
`;

const starsFragmentShader = `
  varying float vBrightness;
  void main() {
    vec2 point = gl_PointCoord - vec2(0.5);
    float falloff = smoothstep(0.5, 0.0, length(point));
    vec3 dimGold = vec3(0.58, 0.37, 0.13);
    vec3 brightGold = vec3(1.0, 0.82, 0.48);
    vec3 color = mix(dimGold, brightGold, clamp(vBrightness, 0.0, 1.0));
    gl_FragColor = vec4(color, falloff * vBrightness);
  }
`;

function gaussian() {
  const u = 1 - Math.random();
  const v = 1 - Math.random();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

function createStarField(count: number) {
  const positions = new Float32Array(count * 3);
  const sizes = new Float32Array(count);
  const phases = new Float32Array(count);
  const clusters = new Float32Array(count);
  const centers: Array<[number, number, number, number]> = [
    [-1.75, 0.85, 1.9, 0.85],
    [1.45, -0.72, 2.45, 0.78],
    [0.18, 1.35, 1.45, 0.55],
    [-2.6, -1.25, 1.55, 0.65],
    [2.75, 1.2, 1.3, 0.48],
    [-0.35, -1.55, 1.75, 0.54],
  ];

  for (let index = 0; index < count; index += 1) {
    const clusterIndex = Math.floor(Math.random() * centers.length);
    const [centerX, centerY, spreadX, spreadY] = centers[clusterIndex];
    const clusterWeight = Math.random();
    const offsetX = gaussian() * spreadX * (0.18 + clusterWeight * 0.42);
    const offsetY = gaussian() * spreadY * (0.18 + clusterWeight * 0.42);
    const pointIndex = index * 3;

    positions[pointIndex] = centerX + offsetX;
    positions[pointIndex + 1] = centerY + offsetY;
    positions[pointIndex + 2] = -1.2 - Math.random() * 1.8;
    sizes[index] = 1.1 + Math.pow(Math.random(), 3) * 4.6;
    phases[index] = Math.random();
    clusters[index] = 0.28 + (1 - Math.min(1, Math.hypot(offsetX / spreadX, offsetY / spreadY))) * 0.72;
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("aSize", new THREE.BufferAttribute(sizes, 1));
  geometry.setAttribute("aPhase", new THREE.BufferAttribute(phases, 1));
  geometry.setAttribute("aCluster", new THREE.BufferAttribute(clusters, 1));
  return geometry;
}

export default function ShaderBackground({ mode }: ShaderBackgroundProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const modeRef = useRef<BackgroundMode>(mode);

  useEffect(() => {
    modeRef.current = mode;
  }, [mode]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 10);
    camera.position.z = 1;
    const renderer = new THREE.WebGLRenderer({ alpha: false, antialias: false, powerPreference: "high-performance" });
    renderer.setClearColor(0x050302, 1);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    container.appendChild(renderer.domElement);

    const pulses = Array.from({ length: MAX_PULSES }, () => new THREE.Vector3(-2, -2, 0));
    const nebulaMaterial = new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0 },
        uMotion: { value: reduceMotion ? 0 : 1 },
        uPulseCenters: { value: pulses },
      },
      vertexShader: nebulaVertexShader,
      fragmentShader: nebulaFragmentShader,
    });
    const nebula = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), nebulaMaterial);
    scene.add(nebula);

    const starsGeometry = createStarField(window.innerWidth < 640 ? 900 : 2000);
    const starsMaterial = new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      uniforms: {
        uTime: { value: 0 },
        uMotion: { value: reduceMotion ? 0 : 1 },
        uPulseCenters: { value: pulses },
      },
      vertexShader: starsVertexShader,
      fragmentShader: starsFragmentShader,
    });
    scene.add(new THREE.Points(starsGeometry, starsMaterial));

    let frame = 0;
    let previousTime = performance.now();
    let pulseDelay = 0.9 + Math.random() * 1.8;
    const pulseAges = new Float32Array(MAX_PULSES);
    const pulseDurations = new Float32Array(MAX_PULSES);

    const resize = () => {
      const viewHeight = 4;
      const aspect = window.innerWidth / window.innerHeight;
      camera.left = (-viewHeight * aspect) / 2;
      camera.right = (viewHeight * aspect) / 2;
      camera.top = viewHeight / 2;
      camera.bottom = -viewHeight / 2;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight, false);
    };
    resize();
    window.addEventListener("resize", resize);

    const render = (now: number) => {
      const delta = Math.min((now - previousTime) / 1000, 0.1);
      previousTime = now;
      const elapsed = now / 1000;
      const processing = modeRef.current === "processing" && !reduceMotion;

      if (processing) {
        pulseDelay -= delta;
        if (pulseDelay <= 0) {
          const slot = pulseAges.findIndex((age, index) => age >= pulseDurations[index]);
          const target = slot === -1 ? Math.floor(Math.random() * MAX_PULSES) : slot;
          pulses[target].set(0.12 + Math.random() * 0.76, 0.16 + Math.random() * 0.68, 0);
          pulseAges[target] = 0;
          pulseDurations[target] = 1.6 + Math.random() * 2.2;
          pulseDelay = 0.75 + Math.random() * 1.9;
        }
      }

      for (let index = 0; index < MAX_PULSES; index += 1) {
        if (!processing) {
          pulseAges[index] = pulseDurations[index] || 1;
        }
        if (pulseAges[index] < pulseDurations[index]) {
          pulseAges[index] += delta;
          const progress = pulseAges[index] / pulseDurations[index];
          pulses[index].z = Math.sin(progress * Math.PI) * 1.12;
        } else {
          pulses[index].z *= 0.86;
        }
      }

      nebulaMaterial.uniforms.uTime.value = elapsed;
      starsMaterial.uniforms.uTime.value = elapsed;
      renderer.render(scene, camera);
      frame = requestAnimationFrame(render);
    };
    frame = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", resize);
      nebula.geometry.dispose();
      nebulaMaterial.dispose();
      starsGeometry.dispose();
      starsMaterial.dispose();
      renderer.dispose();
      if (container.contains(renderer.domElement)) container.removeChild(renderer.domElement);
    };
  }, []);

  return <div ref={containerRef} className="shader-background" aria-hidden="true" />;
}
