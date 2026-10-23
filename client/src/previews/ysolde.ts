import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js'
import { disposeObjects } from './dispose-objects'

export let ysoldePreview:
  | {
      model: THREE.Group
      mixer: THREE.AnimationMixer
      currentAction: () => THREE.AnimationAction | undefined
    }
  | undefined

export async function showYsolde(
  scene: THREE.Scene,
  resources: THREE.Object3D[],
  cleanup: (() => void)[],
  disposed: () => boolean
) {
  document.title = '이졸데 · 캐릭터 미리보기'
  document.querySelector('h1')!.textContent = '이졸데 미리보기'
  document.querySelector('header p:last-child')!.textContent =
    '고고학자 이졸데의 외형과 대기·걷기·달리기를 살펴보세요.'
  document
    .querySelector('nav[aria-label="광휘의 투구 착용 비교"]')
    ?.setAttribute('hidden', '')
  const status = document.getElementById('status')!
  const aside = document.querySelector('aside')!
  aside.replaceChildren(status)
  aside.insertAdjacentHTML(
    'beforeend',
    `<fieldset id="ysolde-controls" disabled>
      <legend>모델과 동작</legend>
      <label for="ysolde-motion">동작</label>
      <select id="ysolde-motion">
        <option value="Bind">기준 자세 · A포즈</option>
        <option value="idle1" selected>대기</option>
        <option value="walk">걷기</option>
        <option value="run">달리기</option>
      </select>
      <div class="buttons">
        <button id="ysolde-pause" type="button">일시정지</button>
        <button id="ysolde-replay" type="button">처음부터</button>
      </div>
      <label for="ysolde-scrub">재생 위치 <output id="ysolde-time">0.00 / 0.00초</output></label>
      <input id="ysolde-scrub" type="range" min="0" max="1" step="0.001" value="0" />
      <label for="ysolde-speed">재생 속도</label>
      <select id="ysolde-speed">
        <option value="0.25">0.25배</option>
        <option value="0.5">0.5배</option>
        <option value="1" selected>1배</option>
      </select>
      <label for="ysolde-view">시점</label>
      <select id="ysolde-view">
        <option value="angle">전체 · 사선</option>
        <option value="front">정면</option>
        <option value="side">측면</option>
        <option value="back">후면</option>
        <option value="face">얼굴 확대</option>
        <option value="hand">오른손 확대</option>
      </select>
      <label class="toggle"><input id="ysolde-skeleton" type="checkbox" /> 뼈대 보기</label>
      <label class="toggle"><input id="ysolde-wireframe" type="checkbox" /> 와이어프레임</label>
      <button id="ysolde-reset" type="button">시점 초기화</button>
    </fieldset>
    <p id="ysolde-stats" class="details"></p>
    <p class="details">바닥 격자 한 칸은 1m입니다.</p>`
  )
  const el = <T extends HTMLElement>(id: string) =>
    document.getElementById(`ysolde-${id}`) as T
  const motion = el<HTMLSelectElement>('motion')
  const view = el<HTMLSelectElement>('view')
  const pause = el<HTMLButtonElement>('pause')
  const replay = el<HTMLButtonElement>('replay')
  const scrub = el<HTMLInputElement>('scrub')
  const speed = el<HTMLSelectElement>('speed')
  const params = new URLSearchParams(location.search)
  status.textContent = '이졸데를 불러오는 중…'
  const gltf = await new GLTFLoader().loadAsync(
    '/__modular-character/parts/ysolde.glb'
  )
  resources.push(gltf.scene)
  if (disposed()) {
    disposeObjects([gltf.scene])
    return
  }
  const model = gltf.scene
  scene.add(model)
  const bounds = new THREE.Box3().setFromObject(model)
  const materials = new Set<THREE.MeshStandardMaterial>()
  const meshes: THREE.SkinnedMesh[] = []
  let triangles = 0
  model.traverse((node) => {
    if (!(node instanceof THREE.Mesh)) return
    triangles +=
      (node.geometry.index?.count ?? node.geometry.attributes.position.count) /
      3
    for (const material of [node.material].flat())
      if (material instanceof THREE.MeshStandardMaterial)
        materials.add(material)
    if (node instanceof THREE.SkinnedMesh) meshes.push(node)
  })
  el('stats').textContent =
    `기준 높이 ${bounds.getSize(new THREE.Vector3()).y.toFixed(2)}m · ${triangles.toLocaleString()}삼각형 · ${meshes[0].skeleton.bones.length}본`
  const skeleton = new THREE.SkeletonHelper(model)
  skeleton.visible = false
  for (const material of [skeleton.material].flat()) {
    material.depthTest = false
    material.depthWrite = false
  }
  scene.add(skeleton)
  cleanup.push(() => skeleton.dispose())
  el<HTMLInputElement>('skeleton').onchange = (event) => {
    skeleton.visible = (event.target as HTMLInputElement).checked
  }
  el<HTMLInputElement>('wireframe').onchange = (event) => {
    for (const material of materials)
      material.wireframe = (event.target as HTMLInputElement).checked
  }
  const grid = new THREE.GridHelper(10, 10, '#57717a', '#30454e')
  grid.position.y = -0.003
  scene.add(grid)
  cleanup.push(() => grid.dispose())
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
  scene.environmentIntensity = 0.75
  cleanup.push(() => environment.dispose())
  scene.add(new THREE.HemisphereLight('#e1ecf2', '#62716b', 2))
  const key = new THREE.DirectionalLight('#fff1e0', 2.5)
  key.position.set(-3, 6, 5)
  scene.add(key)
  const camera = new THREE.PerspectiveCamera(35, 1, 0.01, 100)
  const controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.minDistance = 0.12
  controls.maxDistance = 12
  cleanup.push(() => controls.dispose())
  const views: Record<string, [number, number, number]> = {
    angle: [0.5, 0.15, 1],
    front: [0, 0.05, 1],
    side: [1, 0.05, 0],
    back: [0, 0.05, -1],
    face: [0, 0.05, 1],
    hand: [-1, 0.25, 1],
  }
  if (Object.hasOwn(views, params.get('camera') ?? ''))
    view.value = params.get('camera')!
  const remember = () => {
    const query = new URLSearchParams(location.search)
    query.set('motion', motion.value)
    query.set('camera', view.value)
    history.replaceState(null, '', `?${query}`)
  }
  const reset = () => {
    const sphere = bounds.getBoundingSphere(new THREE.Sphere())
    if (view.value === 'face' || view.value === 'hand') {
      model.updateMatrixWorld(true)
      const name = view.value === 'face' ? 'Head' : 'RightHand'
      model.getObjectByName(name)!.getWorldPosition(sphere.center)
      sphere.center.y += view.value === 'face' ? 0.05 : -0.04
      sphere.radius = view.value === 'face' ? 0.25 : 0.17
    }
    const halfFov = Math.atan(
      Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) *
        Math.min(camera.aspect, 1)
    )
    controls.target.copy(sphere.center)
    camera.position
      .fromArray(views[view.value])
      .normalize()
      .multiplyScalar((sphere.radius * 1.1) / Math.sin(halfFov))
      .add(sphere.center)
    controls.update()
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
  view.onchange = () => {
    reset()
    remember()
  }
  el('reset').onclick = reset
  const mixer = new THREE.AnimationMixer(model)
  cleanup.push(() => {
    mixer.stopAllAction()
    mixer.uncacheRoot(model)
    ysoldePreview = undefined
  })
  const clips = new Map(gltf.animations.map((clip) => [clip.name, clip]))
  let action: THREE.AnimationAction | undefined
  let paused = false
  const play = () => {
    mixer.stopAllAction()
    for (const mesh of meshes) mesh.skeleton.pose()
    const clip = clips.get(motion.value)
    action = clip ? mixer.clipAction(clip).reset().play() : undefined
    paused = false
    pause.textContent = '일시정지'
    pause.disabled = replay.disabled = scrub.disabled = !action
    mixer.update(0)
    remember()
  }
  const requested = params.get('motion') ?? 'idle1'
  if (requested === 'Bind' || clips.has(requested)) motion.value = requested
  motion.onchange = () => {
    play()
    reset()
  }
  replay.onclick = play
  pause.onclick = () => {
    paused = !paused
    pause.textContent = paused ? '재생' : '일시정지'
  }
  scrub.oninput = () => {
    if (!action) return
    paused = true
    pause.textContent = '재생'
    action.time = Math.min(
      Number(scrub.value) * action.getClip().duration,
      action.getClip().duration - 1e-6
    )
    mixer.update(0)
  }
  play()
  reset()
  ysoldePreview = { model, mixer, currentAction: () => action }
  let previous = performance.now()
  renderer.setAnimationLoop((now) => {
    const dt = Math.min((now - previous) / 1000, 0.1)
    previous = now
    if (!paused) mixer.update(dt * Number(speed.value))
    controls.update()
    const duration = action?.getClip().duration ?? 0
    const time = action?.time ?? 0
    scrub.value = String(duration ? time / duration : 0)
    el('time').textContent = `${time.toFixed(2)} / ${duration.toFixed(2)}초`
    renderer.render(scene, camera)
  })
  status.textContent = '이졸데를 불러왔습니다.'
  el<HTMLFieldSetElement>('controls').disabled = false
  document.body.dataset.ready = 'true'
}
