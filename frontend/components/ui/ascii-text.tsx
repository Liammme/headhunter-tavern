"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";

const vertexShader = `
varying vec2 vUv;
uniform float uTime;
uniform float uEnableWaves;

void main() {
  vUv = uv;
  float time = uTime * 5.;
  float waveFactor = uEnableWaves;
  vec3 transformed = position;

  transformed.x += sin(time + position.y) * 0.5 * waveFactor;
  transformed.y += cos(time + position.z) * 0.15 * waveFactor;
  transformed.z += sin(time + position.x) * waveFactor;

  gl_Position = projectionMatrix * modelViewMatrix * vec4(transformed, 1.0);
}
`;

const fragmentShader = `
varying vec2 vUv;
uniform float uTime;
uniform sampler2D uTexture;

void main() {
  float time = uTime;
  vec2 pos = vUv;
  float r = texture2D(uTexture, pos + cos(time * 2. - time + pos.x) * .01).r;
  float g = texture2D(uTexture, pos + tan(time * .5 + pos.x - time) * .01).g;
  float b = texture2D(uTexture, pos - cos(time * 2. + time + pos.y) * .01).b;
  float a = texture2D(uTexture, pos).a;

  gl_FragColor = vec4(r, g, b, a);
}
`;

const ASCII_CHARSET = " .'`^\",:;Il!i~+_-?][}{1)(|/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$";
const FONT_FAMILY = "'Consolas', 'Courier New', monospace";

type ASCIITextProps = {
  text?: string;
  enableWaves?: boolean;
  asciiFontSize?: number;
  textFontSize?: number;
  planeBaseHeight?: number;
  textColor?: string;
};

class AsciiFilter {
  private readonly renderer: THREE.WebGLRenderer;
  readonly domElement: HTMLDivElement;
  private readonly pre: HTMLPreElement;
  private readonly canvas: HTMLCanvasElement;
  private readonly context: CanvasRenderingContext2D;
  private readonly fontSize: number;
  private readonly fontFamily: string;
  private readonly charset: string;
  private readonly invert: boolean;
  private width = 0;
  private height = 0;
  private center = { x: 0, y: 0 };
  private mouse = { x: 0, y: 0 };
  private deg = 0;

  constructor(
    renderer: THREE.WebGLRenderer,
    { fontSize = 12, fontFamily = FONT_FAMILY, charset = ASCII_CHARSET, invert = true } = {},
  ) {
    this.renderer = renderer;
    this.fontSize = fontSize;
    this.fontFamily = fontFamily;
    this.charset = charset;
    this.invert = invert;
    this.domElement = document.createElement("div");
    this.domElement.className = "ascii-text-filter";
    this.pre = document.createElement("pre");
    this.canvas = document.createElement("canvas");

    const context = this.canvas.getContext("2d");
    if (!context) {
      throw new Error("Canvas 2D context is unavailable.");
    }

    this.context = context;
    this.context.imageSmoothingEnabled = false;
    this.domElement.appendChild(this.pre);
    this.domElement.appendChild(this.canvas);
    this.onMouseMove = this.onMouseMove.bind(this);
    document.addEventListener("mousemove", this.onMouseMove);
  }

  setSize(width: number, height: number) {
    this.width = width;
    this.height = height;
    this.renderer.setSize(width, height);
    this.reset();
    this.center = { x: width / 2, y: height / 2 };
    this.mouse = { ...this.center };
  }

  render(scene: THREE.Scene, camera: THREE.Camera) {
    this.renderer.render(scene, camera);
    const w = this.canvas.width;
    const h = this.canvas.height;
    this.context.clearRect(0, 0, w, h);

    if (w && h) {
      this.context.drawImage(this.renderer.domElement, 0, 0, w, h);
      this.asciify(w, h);
      this.hue();
    }
  }

  dispose() {
    document.removeEventListener("mousemove", this.onMouseMove);
  }

  private reset() {
    this.context.font = `${this.fontSize}px ${this.fontFamily}`;
    const charWidth = this.context.measureText("A").width || this.fontSize * 0.62;
    this.canvas.width = Math.max(1, Math.floor(this.width / charWidth));
    this.canvas.height = Math.max(1, Math.floor(this.height / this.fontSize));
    this.pre.style.fontFamily = this.fontFamily;
    this.pre.style.fontSize = `${this.fontSize}px`;
  }

  private onMouseMove(event: MouseEvent) {
    const ratio = window.devicePixelRatio || 1;
    this.mouse = { x: event.clientX * ratio, y: event.clientY * ratio };
  }

  private hue() {
    const deg = (Math.atan2(this.mouse.y - this.center.y, this.mouse.x - this.center.x) * 180) / Math.PI;
    this.deg += (deg - this.deg) * 0.075;
    this.domElement.style.filter = `hue-rotate(${this.deg.toFixed(1)}deg)`;
  }

  private asciify(w: number, h: number) {
    const imgData = this.context.getImageData(0, 0, w, h).data;
    let result = "";

    for (let y = 0; y < h; y += 1) {
      for (let x = 0; x < w; x += 1) {
        const index = x * 4 + y * 4 * w;
        const [r, g, b, a] = [imgData[index], imgData[index + 1], imgData[index + 2], imgData[index + 3]];

        if (a === 0) {
          result += " ";
          continue;
        }

        const gray = (0.3 * r + 0.6 * g + 0.1 * b) / 255;
        const rawIndex = Math.floor((1 - gray) * (this.charset.length - 1));
        result += this.charset[this.invert ? this.charset.length - rawIndex - 1 : rawIndex];
      }
      result += "\n";
    }

    this.pre.textContent = result;
  }
}

class CanvasText {
  readonly canvas: HTMLCanvasElement;
  private readonly context: CanvasRenderingContext2D;
  private readonly text: string;
  private readonly fontSize: number;
  private readonly color: string;
  private readonly font = FONT_FAMILY;

  constructor(text: string, fontSize: number, color: string) {
    this.canvas = document.createElement("canvas");
    const context = this.canvas.getContext("2d");
    if (!context) {
      throw new Error("Canvas 2D context is unavailable.");
    }
    this.context = context;
    this.text = text;
    this.fontSize = fontSize;
    this.color = color;
  }

  resize() {
    this.context.font = this.fontStyle;
    const metrics = this.context.measureText(this.text);
    this.canvas.width = Math.ceil(metrics.width) + 24;
    this.canvas.height = Math.ceil(metrics.actualBoundingBoxAscent + metrics.actualBoundingBoxDescent) + 24;
  }

  render() {
    this.context.clearRect(0, 0, this.canvas.width, this.canvas.height);
    this.context.fillStyle = this.color;
    this.context.font = this.fontStyle;
    const metrics = this.context.measureText(this.text);
    this.context.fillText(this.text, 12, 12 + metrics.actualBoundingBoxAscent);
  }

  get aspect() {
    return this.canvas.width / Math.max(1, this.canvas.height);
  }

  private get fontStyle() {
    return `700 ${this.fontSize}px ${this.font}`;
  }
}

class CanvAscii {
  private readonly container: HTMLElement;
  private readonly textCanvas: CanvasText;
  private readonly texture: THREE.CanvasTexture;
  private readonly scene = new THREE.Scene();
  private readonly camera: THREE.PerspectiveCamera;
  private readonly geometry: THREE.PlaneGeometry;
  private readonly material: THREE.ShaderMaterial;
  private readonly mesh: THREE.Mesh;
  private readonly renderer: THREE.WebGLRenderer;
  private readonly filter: AsciiFilter;
  private width: number;
  private height: number;
  private mouse: { x: number; y: number };
  private animationFrameId = 0;

  constructor(props: Required<ASCIITextProps>, container: HTMLElement, width: number, height: number) {
    this.container = container;
    this.width = width;
    this.height = height;
    this.mouse = { x: width / 2, y: height / 2 };
    this.camera = new THREE.PerspectiveCamera(45, width / height, 1, 1000);
    this.camera.position.z = 30;
    this.textCanvas = new CanvasText(props.text, props.textFontSize, props.textColor);
    this.textCanvas.resize();
    this.textCanvas.render();
    this.texture = new THREE.CanvasTexture(this.textCanvas.canvas);
    this.texture.minFilter = THREE.NearestFilter;

    const planeHeight = props.planeBaseHeight;
    this.geometry = new THREE.PlaneGeometry(planeHeight * this.textCanvas.aspect, planeHeight, 36, 36);
    this.material = new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader,
      transparent: true,
      uniforms: {
        uTime: { value: 0 },
        uTexture: { value: this.texture },
        uEnableWaves: { value: props.enableWaves ? 1 : 0 },
      },
    });
    this.mesh = new THREE.Mesh(this.geometry, this.material);
    this.scene.add(this.mesh);
    this.renderer = new THREE.WebGLRenderer({ antialias: false, alpha: true });
    this.renderer.setPixelRatio(1);
    this.renderer.setClearColor(0x000000, 0);
    this.filter = new AsciiFilter(this.renderer, { fontSize: props.asciiFontSize });
    this.container.appendChild(this.filter.domElement);
    this.setSize(width, height);
    this.onMouseMove = this.onMouseMove.bind(this);
    this.container.addEventListener("mousemove", this.onMouseMove);
    this.container.addEventListener("touchmove", this.onMouseMove);
  }

  load() {
    const animateFrame = () => {
      this.animationFrameId = requestAnimationFrame(animateFrame);
      this.render();
    };
    animateFrame();
  }

  setSize(width: number, height: number) {
    this.width = width;
    this.height = height;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.filter.setSize(width, height);
  }

  dispose() {
    cancelAnimationFrame(this.animationFrameId);
    this.filter.dispose();
    this.filter.domElement.remove();
    this.container.removeEventListener("mousemove", this.onMouseMove);
    this.container.removeEventListener("touchmove", this.onMouseMove);
    this.geometry.dispose();
    this.material.dispose();
    this.texture.dispose();
    this.renderer.dispose();
    this.renderer.forceContextLoss();
    this.scene.clear();
  }

  private onMouseMove(event: MouseEvent | TouchEvent) {
    const pointer = "touches" in event ? event.touches[0] : event;
    if (!pointer) {
      return;
    }
    const bounds = this.container.getBoundingClientRect();
    this.mouse = { x: pointer.clientX - bounds.left, y: pointer.clientY - bounds.top };
  }

  private render() {
    const time = Date.now() * 0.001;
    this.textCanvas.render();
    this.texture.needsUpdate = true;
    this.material.uniforms.uTime.value = Math.sin(time);
    this.updateRotation();
    this.filter.render(this.scene, this.camera);
  }

  private updateRotation() {
    const x = mapRange(this.mouse.y, 0, this.height, 0.5, -0.5);
    const y = mapRange(this.mouse.x, 0, this.width, -0.5, 0.5);
    this.mesh.rotation.x += (x - this.mesh.rotation.x) * 0.05;
    this.mesh.rotation.y += (y - this.mesh.rotation.y) * 0.05;
  }
}

export default function ASCIIText({
  text = "TalentSignal",
  enableWaves = true,
  asciiFontSize = 7,
  textFontSize = 180,
  planeBaseHeight = 8,
  textColor = "#101510",
}: ASCIITextProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const asciiRef = useRef<CanvAscii | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    let cancelled = false;
    let resizeObserver: ResizeObserver | null = null;

    const setup = () => {
      const { width, height } = container.getBoundingClientRect();
      if (width <= 0 || height <= 0 || cancelled) {
        return;
      }

      asciiRef.current?.dispose();
      asciiRef.current = new CanvAscii(
        {
          text,
          enableWaves,
          asciiFontSize,
          textFontSize,
          planeBaseHeight,
          textColor,
        },
        container,
        width,
        height,
      );
      asciiRef.current.load();
    };

    setup();
    resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry || !asciiRef.current) {
        setup();
        return;
      }
      const { width, height } = entry.contentRect;
      if (width > 0 && height > 0) {
        asciiRef.current.setSize(width, height);
      }
    });
    resizeObserver.observe(container);

    return () => {
      cancelled = true;
      resizeObserver?.disconnect();
      asciiRef.current?.dispose();
      asciiRef.current = null;
    };
  }, [asciiFontSize, enableWaves, planeBaseHeight, text, textColor, textFontSize]);

  return <div ref={containerRef} className="ascii-text-container" aria-hidden="true" />;
}

function mapRange(value: number, start: number, stop: number, start2: number, stop2: number) {
  return ((value - start) / (stop - start)) * (stop2 - start2) + start2;
}
