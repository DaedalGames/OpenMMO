import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js'

export async function showFemaleBase(
  scene: THREE.Scene,
  resources: THREE.Object3D[],
  cleanup: (() => void)[],
  disposed: () => boolean
) {
  document.title = '여성 베이스 · 캐릭터 미리보기'
  document.querySelector('h1')!.textContent = '여성 베이스 미리보기'
  document.querySelector('header p:last-child')!.textContent =
    '눈꺼풀 경계를 다듬은 눈과 여성 기본 체형을 살펴보세요.'
  const status = document.getElementById('status')!
  const aside = document.querySelector('aside')!
  aside.replaceChildren(status)
  aside.insertAdjacentHTML(
    'beforeend',
    `
    <fieldset id="female-controls" disabled>
      <legend>모델 살펴보기</legend>
      <label for="female-camera">시점</label>
      <select id="female-camera">
        <option value="face">얼굴 확대</option>
        <option value="full">전신 정면</option>
        <option value="side">전신 측면</option>
        <option value="back">전신 후면</option>
        <option value="feet">발 확대</option>
      </select>
      <label class="toggle"><input id="female-wireframe" type="checkbox" /> 와이어프레임</label>
      <button id="female-reset" type="button">시점 초기화</button>
    </fieldset>
    <p id="female-stats" class="details"></p>
    <p class="details">여성 기본 체형 · 속눈썹 뿌리 밀착 v10<br />리깅 전 모델입니다. 복장 교체와 동작은 아직 적용되지 않았습니다.</p>`
  )
  status.textContent = '여성 베이스를 불러오는 중…'
  const { scene: model } = await new GLTFLoader().loadAsync(
    '/__modular-character/parts/female_base.glb'
  )
  resources.push(model)
  if (disposed()) {
    model.traverse((node) => {
      if (!(node instanceof THREE.Mesh)) return
      node.geometry.dispose()
      for (const material of Array.isArray(node.material)
        ? node.material
        : [node.material]) {
        for (const value of Object.values(material))
          if (value instanceof THREE.Texture) {
            if (value.image instanceof ImageBitmap) value.image.close()
            value.dispose()
          }
        material.dispose()
      }
    })
    return
  }
  scene.add(model)
  let triangles = 0
  const materials = new Set<THREE.MeshStandardMaterial>()
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
  scene.environmentIntensity = 0.65
  cleanup.push(() => environment.dispose())
  scene.add(new THREE.HemisphereLight('#e1ecf2', '#62716b', 2))
  const key = new THREE.DirectionalLight('#fff1e0', 2.5)
  key.position.set(-3, 6, 5)
  const fill = new THREE.DirectionalLight('#b1cbe8', 1.6)
  fill.position.set(3, 3, -3)
  scene.add(key, fill)
  const floor = new THREE.Mesh(
    new THREE.CircleGeometry(2, 64),
    new THREE.MeshStandardMaterial({ color: '#273940', roughness: 1 })
  )
  floor.rotation.x = -Math.PI / 2
  floor.position.y = -0.002
  scene.add(floor)
  const camera = new THREE.PerspectiveCamera(35, 1, 0.001, 20)
  const controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.minDistance = 0.08
  controls.maxDistance = 5
  cleanup.push(() => controls.dispose())
  const views: Record<string, { target: number[]; position: number[] }> = {
    face: { target: [0, 0.916, 0], position: [0, 0.926, 0.36] },
    full: { target: [0, 0.5, 0], position: [0, 0.55, 1.9] },
    side: { target: [0, 0.5, 0], position: [1.9, 0.55, 0] },
    back: { target: [0, 0.5, 0], position: [0, 0.55, -1.9] },
    feet: { target: [0, 0.065, 0], position: [0.24, 0.16, 0.45] },
  }
  const select = document.getElementById('female-camera') as HTMLSelectElement
  const requested = new URLSearchParams(location.search).get('camera')
  if (requested && Object.hasOwn(views, requested)) select.value = requested
  const reset = () => {
    const view = views[select.value]
    const aspect = host.clientWidth / host.clientHeight
    controls.target.fromArray(view.target)
    camera.position.fromArray(view.position)
    camera.position
      .sub(controls.target)
      .multiplyScalar(Math.max(1, 1 / aspect))
      .add(controls.target)
    controls.update()
  }
  select.onchange = reset
  document.getElementById('female-reset')!.onclick = reset
  const wireframe = document.getElementById(
    'female-wireframe'
  ) as HTMLInputElement
  wireframe.onchange = () => {
    for (const material of materials) material.wireframe = wireframe.checked
  }
  const resize = () => {
    camera.aspect = host.clientWidth / host.clientHeight
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
  document.getElementById('female-stats')!.textContent =
    `${triangles.toLocaleString()}삼각형 · 속눈썹 뿌리 밀착 v10`
  status.textContent = '피부에 밀착한 속눈썹 뿌리'
  const fieldset = document.getElementById(
    'female-controls'
  ) as HTMLFieldSetElement
  fieldset.disabled = false
  document.body.dataset.ready = 'true'
}
