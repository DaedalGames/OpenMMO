import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js'
import { disposeObjects } from './dispose-objects'

export async function showYsoldeTent(
  scene: THREE.Scene,
  resources: THREE.Object3D[],
  cleanup: (() => void)[],
  disposed: () => boolean
) {
  document.title = '이졸데의 텐트 · 미리보기'
  document.querySelector('h1')!.textContent = '이졸데의 텐트'
  document.querySelector('header p:last-child')!.textContent =
    '전면을 숨겨 내부를 살펴보고, 매트리스나 야전침대를 놓아 공간을 확인하세요.'
  document
    .querySelector('nav[aria-label="광휘의 투구 착용 비교"]')
    ?.setAttribute('hidden', '')
  const host = document.getElementById('viewport')!
  host.setAttribute('aria-label', '텐트 3D 미리보기')
  const status = document.getElementById('status')!
  const aside = document.querySelector('aside')!
  aside.replaceChildren(status)
  aside.insertAdjacentHTML(
    'beforeend',
    `<fieldset id="tent-controls" disabled>
      <legend>텐트 살펴보기</legend>
      <label for="tent-mode">표시</label>
      <select id="tent-mode">
        <option value="outside">전체 텐트</option>
        <option value="inside">실내 · 전면 숨김</option>
        <option value="front">전면부만</option>
      </select>
      <label for="tent-camera">시점</label>
      <select id="tent-camera">
        <option value="angle">사선</option>
        <option value="front">정면</option>
        <option value="side">오른쪽</option>
        <option value="back">후면</option>
        <option value="top">위에서</option>
      </select>
      <label for="tent-bed">잠자리</label>
      <select id="tent-bed">
        <option value="none">놓지 않음</option>
        <option value="mattress">바닥 매트리스</option>
        <option value="cot">낮은 야전침대</option>
        <option value="inn">여관 침대 · 비교용</option>
      </select>
      <label class="toggle"><input id="tent-grid" type="checkbox" checked /> 1m 격자</label>
      <label class="toggle"><input id="tent-wireframe" type="checkbox" /> 와이어프레임</label>
      <button id="tent-reset" type="button">시점 초기화</button>
    </fieldset>
    <p id="tent-stats" class="details"></p>
    <p class="details">바닥 2.4 × 3.2m · 기둥 끝 높이 2.3m</p>`
  )
  const el = <T extends HTMLElement>(id: string) =>
    document.getElementById(`tent-${id}`) as T
  const mode = el<HTMLSelectElement>('mode')
  const view = el<HTMLSelectElement>('camera')
  const bedding = el<HTMLSelectElement>('bed')
  const showGrid = el<HTMLInputElement>('grid')
  const wireframe = el<HTMLInputElement>('wireframe')
  const params = new URLSearchParams(location.search)
  status.textContent = '텐트와 잠자리를 불러오는 중…'
  const loader = new GLTFLoader()
  const load = async (path: string) => {
    const gltf = await loader.loadAsync(path)
    if (disposed()) {
      disposeObjects([gltf.scene])
      throw new Error('Preview closed')
    }
    resources.push(gltf.scene)
    return gltf.scene
  }
  const [back, front, mattress, cot, bed] = await Promise.all([
    load('/__modular-character/parts/ysolde_tent_back.glb'),
    load('/__modular-character/parts/ysolde_tent_front.glb'),
    load('/__modular-character/parts/ysolde_ground_mattress.glb'),
    load('/__modular-character/parts/ysolde_field_cot.glb'),
    load('/models/objects/rustic_bed.glb'),
  ])
  if (disposed()) return
  back.name = 'tent-back'
  front.name = 'tent-front'
  const beds = { mattress, cot, inn: bed }
  for (const [name, model] of Object.entries(beds)) {
    model.name = `tent-bed-${name}`
    const bounds = new THREE.Box3().setFromObject(model)
    const center = bounds.getCenter(new THREE.Vector3())
    model.position.set(-0.2 - center.x, 0.015 - bounds.min.y, -0.2 - center.z)
    scene.add(model)
  }
  scene.add(back, front)
  const materials = new Set<THREE.MeshStandardMaterial>()
  const triangleCounts = [back, front].map((root) => {
    let triangles = 0
    root.traverse((node) => {
      if (!(node instanceof THREE.Mesh)) return
      triangles +=
        (node.geometry.index?.count ??
          node.geometry.attributes.position.count) / 3
      for (const material of [node.material].flat())
        if (material instanceof THREE.MeshStandardMaterial)
          materials.add(material)
    })
    return triangles
  })
  el('stats').textContent =
    `후면부 ${triangleCounts[0].toLocaleString()} · 전면부 ${triangleCounts[1].toLocaleString()} 삼각형`
  const grid = new THREE.GridHelper(10, 10, '#6f8881', '#354b47')
  grid.position.y = -0.015
  scene.add(grid)
  cleanup.push(() => {
    grid.geometry.dispose()
    for (const material of [grid.material].flat()) material.dispose()
  })
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
  scene.add(new THREE.HemisphereLight('#e5eff0', '#777360', 1.8))
  const key = new THREE.DirectionalLight('#fff1db', 2.8)
  key.position.set(3, 6, 5)
  scene.add(key)
  const camera = new THREE.OrthographicCamera(-2, 2, 2, -2, 0.01, 100)
  const controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.minZoom = 0.4
  controls.maxZoom = 8
  cleanup.push(() => controls.dispose())
  const views: Record<string, [number, number, number]> = {
    angle: [4, 3.2, 5],
    front: [0, 0, 1],
    side: [1, 0, 0],
    back: [0, 0, -1],
    top: [0, 1, 0.001],
  }
  const requestedMode = params.get('mode')
  if (requestedMode && ['outside', 'inside', 'front'].includes(requestedMode))
    mode.value = requestedMode
  if (Object.hasOwn(views, params.get('camera') ?? ''))
    view.value = params.get('camera')!
  const requestedBed = params.get('bed')
  bedding.value =
    requestedBed === '1'
      ? 'mattress'
      : requestedBed && Object.hasOwn(beds, requestedBed)
        ? requestedBed
        : 'none'
  const remember = () => {
    const query = new URLSearchParams(location.search)
    query.set('mode', mode.value)
    query.set('camera', view.value)
    if (bedding.value !== 'none') query.set('bed', bedding.value)
    else query.delete('bed')
    history.replaceState(null, '', `?${query}`)
  }
  const updateVisibility = () => {
    front.visible = mode.value !== 'inside'
    back.visible = mode.value !== 'front'
    for (const [name, model] of Object.entries(beds))
      model.visible = bedding.value === name && mode.value !== 'front'
    remember()
  }
  const reset = () => {
    controls.target.set(0, 1.1, 0)
    camera.position.fromArray(views[view.value]).normalize().multiplyScalar(10)
    camera.position.add(controls.target)
    camera.zoom = 1
    camera.updateProjectionMatrix()
    controls.update()
    remember()
  }
  const resize = () => {
    const width = Math.max(host.clientWidth, 1)
    const height = Math.max(host.clientHeight, 1)
    const aspect = width / height
    const span = 4.4 / Math.min(aspect, 1)
    camera.left = (-span * aspect) / 2
    camera.right = (span * aspect) / 2
    camera.top = span / 2
    camera.bottom = -span / 2
    camera.updateProjectionMatrix()
    renderer.setSize(width, height)
  }
  const observer = new ResizeObserver(resize)
  observer.observe(host)
  cleanup.push(() => observer.disconnect())
  mode.onchange = updateVisibility
  bedding.onchange = updateVisibility
  view.onchange = reset
  showGrid.onchange = () => {
    grid.visible = showGrid.checked
  }
  wireframe.onchange = () => {
    for (const material of materials) material.wireframe = wireframe.checked
  }
  el('reset').onclick = reset
  resize()
  reset()
  updateVisibility()
  renderer.setAnimationLoop(() => {
    controls.update()
    renderer.render(scene, camera)
  })
  status.textContent = '텐트를 불러왔습니다.'
  el<HTMLFieldSetElement>('controls').disabled = false
  document.body.dataset.ready = 'true'
}
