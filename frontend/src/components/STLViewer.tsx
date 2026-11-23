import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";
import { Maximize2, RotateCcw, Grid, Eye, AlertTriangle } from "lucide-react";
import { GeometryAnalysis } from "../types";

interface STLViewerProps {
  stlFile?: File | null;
  stlBuffer?: ArrayBuffer | null;
  analysis?: GeometryAnalysis | null;
}

export const STLViewer: React.FC<STLViewerProps> = ({ stlFile, stlBuffer, analysis }) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const [wireframe, setWireframe] = useState<boolean>(false);
  const [showGrid, setShowGrid] = useState<boolean>(true);
  const [showBBox, setShowBBox] = useState<boolean>(true);

  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const meshRef = useRef<THREE.Mesh | null>(null);
  const bboxHelperRef = useRef<THREE.BoxHelper | null>(null);
  const gridHelperRef = useRef<THREE.GridHelper | null>(null);

  // Initialize Three.js scene
  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    const width = mount.clientWidth || 600;
    const height = mount.clientHeight || 550;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1c1e20);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.001, 10000);
    camera.position.set(2, 2, 2);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.shadowMap.enabled = true;
    rendererRef.current = renderer;

    mount.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controlsRef.current = controls;

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0xffffff, 1.2);
    dirLight1.position.set(10, 20, 15);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0xd2dce3, 0.8);
    dirLight2.position.set(-10, -10, -10);
    scene.add(dirLight2);

    // Floor Grid
    const gridHelper = new THREE.GridHelper(10, 20, 0x8ca3aa, 0x35393b);
    gridHelper.position.y = 0;
    scene.add(gridHelper);
    gridHelperRef.current = gridHelper;

    // Axes
    const axesHelper = new THREE.AxesHelper(1);
    scene.add(axesHelper);

    // Animation Loop
    let animationFrameId: number;
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    // Handle Resize
    const handleResize = () => {
      if (!mount || !renderer || !camera) return;
      const w = mount.clientWidth;
      const h = mount.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener("resize", handleResize);

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener("resize", handleResize);
      renderer.dispose();
      if (mount.contains(renderer.domElement)) {
        mount.removeChild(renderer.domElement);
      }
    };
  }, []);

  // Fit to view helper
  const fitCameraToMesh = (geometry: THREE.BufferGeometry) => {
    if (!cameraRef.current || !controlsRef.current) return;
    geometry.computeBoundingBox();
    const bbox = geometry.boundingBox;
    if (!bbox) return;

    const center = new THREE.Vector3();
    bbox.getCenter(center);
    const size = new THREE.Vector3();
    bbox.getSize(size);

    const maxDim = Math.max(size.x, size.y, size.z) || 1;
    const fov = cameraRef.current.fov * (Math.PI / 180);
    let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2)) * 1.8;

    cameraRef.current.position.set(center.x + cameraZ * 0.8, center.y + cameraZ * 0.8, center.z + cameraZ * 0.8);
    cameraRef.current.lookAt(center);
    cameraRef.current.near = maxDim / 1000;
    cameraRef.current.far = maxDim * 1000;
    cameraRef.current.updateProjectionMatrix();

    controlsRef.current.target.copy(center);
    controlsRef.current.update();

    if (gridHelperRef.current) {
      gridHelperRef.current.position.y = bbox.min.y;
    }
  };

  // Load and render STL
  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene) return;

    const loadGeometry = (buffer: ArrayBuffer) => {
      // Remove old mesh and helpers
      if (meshRef.current) {
        scene.remove(meshRef.current);
        meshRef.current.geometry.dispose();
        if (Array.isArray(meshRef.current.material)) {
          meshRef.current.material.forEach((m) => m.dispose());
        } else {
          meshRef.current.material.dispose();
        }
        meshRef.current = null;
      }
      if (bboxHelperRef.current) {
        scene.remove(bboxHelperRef.current);
        bboxHelperRef.current = null;
      }

      const loader = new STLLoader();
      const geometry = loader.parse(buffer);
      geometry.computeVertexNormals();

      const material = new THREE.MeshStandardMaterial({
        color: 0x859aa1,
        roughness: 0.35,
        metalness: 0.2,
        wireframe: wireframe,
        side: THREE.DoubleSide,
      });

      const mesh = new THREE.Mesh(geometry, material);
      scene.add(mesh);
      meshRef.current = mesh;

      // Add Bounding Box Helper
      const bboxHelper = new THREE.BoxHelper(mesh, 0x8ca3aa);
      scene.add(bboxHelper);
      bboxHelperRef.current = bboxHelper;
      bboxHelper.visible = showBBox;

      fitCameraToMesh(geometry);
    };

    if (stlBuffer) {
      loadGeometry(stlBuffer);
    } else if (stlFile) {
      const reader = new FileReader();
      reader.onload = (e) => {
        if (e.target?.result instanceof ArrayBuffer) {
          loadGeometry(e.target.result);
        }
      };
      reader.readAsArrayBuffer(stlFile);
    }
  }, [stlFile, stlBuffer]);

  // Wireframe toggle update
  useEffect(() => {
    if (meshRef.current && meshRef.current.material instanceof THREE.MeshStandardMaterial) {
      meshRef.current.material.wireframe = wireframe;
    }
  }, [wireframe]);

  // Grid toggle update
  useEffect(() => {
    if (gridHelperRef.current) {
      gridHelperRef.current.visible = showGrid;
    }
  }, [showGrid]);

  // Bounding box toggle update
  useEffect(() => {
    if (bboxHelperRef.current) {
      bboxHelperRef.current.visible = showBBox;
    }
  }, [showBBox]);

  const handleResetCamera = () => {
    if (meshRef.current) {
      fitCameraToMesh(meshRef.current.geometry);
    }
  };

  return (
    <div className="card viewport-card">
      <div className="viewport-toolbar">
        <button
          className={`viewport-btn ${wireframe ? "active" : ""}`}
          onClick={() => setWireframe(!wireframe)}
          title="Toggle Wireframe"
        >
          <Eye size={14} />
          {wireframe ? "Shaded" : "Wireframe"}
        </button>
        <button
          className={`viewport-btn ${showGrid ? "active" : ""}`}
          onClick={() => setShowGrid(!showGrid)}
          title="Toggle Grid Floor"
        >
          <Grid size={14} />
          Grid
        </button>
        <button
          className={`viewport-btn ${showBBox ? "active" : ""}`}
          onClick={() => setShowBBox(!showBBox)}
          title="Toggle Bounding Box"
        >
          <Maximize2 size={14} />
          Box
        </button>
        <button className="viewport-btn" onClick={handleResetCamera} title="Reset Camera">
          <RotateCcw size={14} />
          Fit
        </button>
      </div>

      <div className="viewport-canvas-container" ref={mountRef} />

      {/* Warning Banners */}
      {analysis?.warnings && analysis.warnings.length > 0 && (
        <div
          style={{
            position: "absolute",
            top: 60,
            left: 16,
            right: 16,
            zIndex: 10,
          }}
        >
          {analysis.warnings.slice(0, 2).map((w, idx) => (
            <div key={idx} className="alert alert-warning" style={{ margin: "4px 0", padding: "8px 12px" }}>
              <AlertTriangle size={16} />
              <span>{w}</span>
            </div>
          ))}
        </div>
      )}

      {/* Geometry Stats Overlay */}
      {analysis && (
        <div className="viewport-overlay font-mono">
          <div className="dim-tag">
            <span className="text-dim">Triangles:</span>
            <span className="text-cyan font-bold">{analysis.triangle_count.toLocaleString()}</span>
          </div>
          <div className="dim-tag">
            <span className="text-dim">Bounds (m):</span>
            <span>
              {analysis.bounding_box.dim_x.toFixed(3)} × {analysis.bounding_box.dim_y.toFixed(3)} ×{" "}
              {analysis.bounding_box.dim_z.toFixed(3)}
            </span>
          </div>
          <div className="dim-tag">
            <span className="text-dim">Watertight:</span>
            <span className={analysis.is_watertight ? "text-success" : "text-warning"}>
              {analysis.is_watertight ? "YES" : "NO"}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
