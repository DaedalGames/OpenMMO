import * as THREE from 'three'
import { disposeObjects } from './dispose-objects'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js'

export async function showFemaleBob(
  scene: THREE.Scene,
  resources: THREE.Object3D[],
  cleanup: (() => void)[],
  disposed: () => boolean
) {
  document.title = '단발 헤어 · 미리보기'
  document.querySelector('h1')!.textContent = '단발 헤어 미리보기'
  document.querySelector('header p:last-child')!.textContent =
    '금발 단발의 정면·측면·후면을 회전하고 확대해 살펴보세요.'
  const status = document.getElementById('status')!
  const aside = document.querySelector('aside')!
  aside.replaceChildren(status)
  aside.insertAdjacentHTML(
    'beforeend',
    `
    <fieldset id="bob-controls" disabled>
      <legend>헤어 살펴보기</legend>
      <label for="bob-view">시점</label>
      <select id="bob-view">
        <option value="front">정면</option>
        <option value="side">측면</option>
        <option value="back">후면</option>
        <option value="top">정수리</option>
      </select>
      <label class="toggle"><input id="bob-rotate" type="checkbox" /> 자동 회전</label>
      <label class="toggle"><input id="bob-wireframe" type="checkbox" /> 와이어프레임</label>
      <button id="bob-reset" type="button">시점 초기화</button>
    </fieldset>
    <p id="bob-stats" class="details"></p>
    <p class="details">피팅 전 원본입니다. 캐릭터에 맞춘 단발은 여성 캐릭터 화면에서 확인할 수 있습니다.</p>
    <a href="?character=female&hair=bob&camera=face">피팅한 단발 착용 보기</a>`
  )
  status.textContent = '단발 헤어를 불러오는 중…'
  const { scene: model } = await new GLTFLoader().loadAsync(
    '/__modular-character/parts/female_knight_bob_source.glb'
  )
  resources.push(model)
  if (disposed()) {
    disposeObjects([model])
    return
  }
  model.rotation.y = -Math.PI / 2
  model.updateMatrixWorld(true)
  const bounds = new THREE.Box3().setFromObject(model)
  const center = bounds.getCenter(new THREE.Vector3())
  const size = bounds.getSize(new THREE.Vector3())
  const scale = 1 / Math.max(size.x, size.y, size.z)
  model.scale.setScalar(scale)
  model.position.copy(center).multiplyScalar(-scale)
  scene.add(model)
  const materials = new Set<THREE.MeshStandardMaterial>()
  let triangles = 0
  model.traverse((node) => {
    if (!(node instanceof THREE.Mesh)) return
    triangles +=
      (node.geometry.index?.count ?? node.geometry.attributes.position.count) /
      3
    for (const material of Array.isArray(node.material)
      ? node.material
      : [node.material])
      if (material instanceof THREE.MeshStandardMaterial)
        materials.add(material)
  })
  document.getElementById('bob-stats')!.textContent =
    `${triangles.toLocaleString()}삼각형 · 4K 텍스처`
  const host = document.getElementById('viewport')!
  const renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2))
  renderer.setClearColor('#17252d')
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  host.append(renderer.domElement)
  cleanup.push(() => {
    renderer.setAnimationLoop(null)
    renderer.dispose()
    renderer.domElement.remove()
  })
  const room = new RoomEnvironment()
  const pmrem = new THREE.PMREMGenerator(renderer)
  const environment = pmrem.fromScene(room)
  room.dispose()
  pmrem.dispose()
  scene.environment = environment.texture
  scene.environmentIntensity = 0.7
  cleanup.push(() => environment.dispose())
  scene.add(new THREE.HemisphereLight('#e1ecf2', '#62716b', 2))
  const key = new THREE.DirectionalLight('#fff1e0', 2.5)
  key.position.set(-3, 6, 5)
  const fill = new THREE.DirectionalLight('#b1cbe8', 1.6)
  fill.position.set(3, 3, -3)
  scene.add(key, fill)
  const camera = new THREE.PerspectiveCamera(35, 1, 0.01, 30)
  const controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.minDistance = 0.65
  controls.maxDistance = 6
  cleanup.push(() => controls.dispose())
  const views: Record<string, [number, number, number]> = {
    front: [0, 0, 1],
    side: [1, 0, 0],
    back: [0, 0, -1],
    top: [0, 1, 0.001],
  }
  const select = document.getElementById('bob-view') as HTMLSelectElement
  const requested = new URLSearchParams(location.search).get('view')
  if (requested && Object.hasOwn(views, requested)) select.value = requested
  const reset = () => {
    controls.target.set(0, 0, 0)
    const halfFov = Math.atan(
      Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) *
        Math.min(camera.aspect, 1)
    )
    const distance = (size.length() * scale * 0.55) / Math.sin(halfFov)
    camera.position
      .fromArray(views[select.value])
      .normalize()
      .multiplyScalar(distance)
    controls.update()
  }
  select.onchange = reset
  document.getElementById('bob-reset')!.onclick = reset
  const rotate = document.getElementById('bob-rotate') as HTMLInputElement
  rotate.onchange = () => {
    controls.autoRotate = rotate.checked
  }
  const wireframe = document.getElementById('bob-wireframe') as HTMLInputElement
  wireframe.onchange = () => {
    for (const material of materials) material.wireframe = wireframe.checked
  }
  const resize = () => {
    camera.aspect = host.clientWidth / Math.max(host.clientHeight, 1)
    camera.updateProjectionMatrix()
    renderer.setSize(host.clientWidth, host.clientHeight)
  }
  const observer = new ResizeObserver(resize)
  observer.observe(host)
  cleanup.push(() => observer.disconnect())
  resize()
  reset()
  renderer.setAnimationLoop(() => {
    controls.update()
    renderer.render(scene, camera)
  })
  status.textContent = '단발 헤어를 불러왔습니다.'
  const fieldset = document.getElementById(
    'bob-controls'
  ) as HTMLFieldSetElement
  fieldset.disabled = false
  document.body.dataset.ready = 'true'
}
