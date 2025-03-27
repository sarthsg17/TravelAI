import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
import mapboxgl from 'mapbox-gl';

export default function ThreeDMap({ locations, route }) {
  const mountRef = useRef(null);
  const sceneRef = useRef(null);

  useEffect(() => {
    // Initialize Three.js scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf0f0f0);
    const camera = new THREE.PerspectiveCamera(
      75, 
      mountRef.current.clientWidth / mountRef.current.clientHeight, 
      0.1, 
      1000
    );
    camera.position.z = 5;
    
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(mountRef.current.clientWidth, mountRef.current.clientHeight);
    mountRef.current.appendChild(renderer.domElement);

    // Add lighting
    const ambientLight = new THREE.AmbientLight(0x404040);
    scene.add(ambientLight);
    const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
    directionalLight.position.set(1, 1, 1);
    scene.add(directionalLight);

    // Add controls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.25;

    // Load 3D models for locations
    const loader = new GLTFLoader();
    locations.forEach((location, index) => {
      loader.load(
        `/models/location-${index % 3}.gltf`, // Sample model paths
        (gltf) => {
          const model = gltf.scene;
          model.position.set(
            location.longitude / 10, 
            location.latitude / 10, 
            0
          );
          model.scale.set(0.1, 0.1, 0.1);
          scene.add(model);
        },
        undefined,
        (error) => console.error('Error loading 3D model:', error)
      );
    });

    // Add route path if available
    if (route) {
      const points = route.geometry.coordinates.map(coord => 
        new THREE.Vector3(coord[0] / 10, coord[1] / 10, 0)
      );
      const routeGeometry = new THREE.BufferGeometry().setFromPoints(points);
      const routeMaterial = new THREE.LineBasicMaterial({ color: 0x3b82f6 });
      const routeLine = new THREE.Line(routeGeometry, routeMaterial);
      scene.add(routeLine);
    }

    // Animation loop
    const animate = () => {
      requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    // Cleanup
    return () => {
      mountRef.current?.removeChild(renderer.domElement);
      controls.dispose();
    };
  }, [locations, route]);

  // Handle window resize
  useEffect(() => {
    const handleResize = () => {
      if (sceneRef.current) {
        sceneRef.current.camera.aspect = mountRef.current.clientWidth / mountRef.current.clientHeight;
        sceneRef.current.camera.updateProjectionMatrix();
        sceneRef.current.renderer.setSize(
          mountRef.current.clientWidth, 
          mountRef.current.clientHeight
        );
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return (
    <div 
      ref={mountRef} 
      style={{ 
        width: '100%', 
        height: '600px',
        borderRadius: '8px',
        overflow: 'hidden'
      }} 
    />
  );
}