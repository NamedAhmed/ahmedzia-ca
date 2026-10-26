
import * as THREE from "three";

const renderer = new THREE.WebGLRenderer({ antialias: true });
document.body.prepend(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x050510);

const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 100);
camera.position.z = 8;

const geometry = new THREE.BoxGeometry();
const material = new THREE.MeshNormalMaterial();

const cubes = [];

for (let x = -5; x <= 5; x++) {
  for (let y = -4; y <= 4; y++) {
    const cube = new THREE.Mesh(geometry, material);
    cube.position.set(x * 1.5, y * 1.5, -5);
    cube.userData = { ox: 0, oy: 0 };
    cube.visible = false;
    scene.add(cube);
    cubes.push(cube);
  }
}

document.getElementById("rotate").addEventListener("click", () => {
  cubes.forEach((cube) => {
    cube.userData.ox = Math.random() * Math.PI * 2;
    cube.userData.oy = Math.random() * Math.PI * 2;
  });
});

function resize() {
  renderer.setSize(innerWidth, innerHeight);
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
}
addEventListener("resize", resize);
resize();

function animate(t) {
  requestAnimationFrame(animate);
  const index = Math.floor(t / 1) % cubes.length;
  cubes[index].visible = true;
  cubes.forEach((cube) => {
    cube.rotation.x = t / 2000 + cube.userData.ox;
    cube.rotation.y = t / 3000 + cube.userData.oy;
  });
  renderer.render(scene, camera);
}
requestAnimationFrame(animate);
