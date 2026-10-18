import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js'
import { disposeObjects } from './dispose-objects'
import { getMonsterDef, parseWeaponRotation } from '../lib/data/monsterDefs'
import { withBarkanRuneGrip } from '../lib/utils/barkanRuneGrip'

export let barkanPreview:
  | {
      model: THREE.Group
      reference: THREE.Group
      weapon: THREE.Group
      mixer: THREE.AnimationMixer
      currentAction: () => THREE.AnimationAction | undefined
    }
  | undefined

export async function showBarkan(
  scene: THREE.Scene,
  resources: THREE.Object3D[],
  cleanup: (() => void)[],
  disposed: () => boolean
) {
  document.title = '바르칸 · 캐릭터 미리보기'
  document.querySelector('h1')!.textContent = '바르칸 미리보기'
  document.querySelector('header p:last-child')!.textContent =
    '2.5m 바르칸의 룬 블레이드 파지와 날개, 몸의 움직임을 살펴보세요.'
  document
    .querySelector('nav[aria-label="광휘의 투구 착용 비교"]')
    ?.setAttribute('hidden', '')
  const status = document.getElementById('status')!
  const aside = document.querySelector('aside')!
  aside.replaceChildren(status)
  aside.insertAdjacentHTML(
    'beforeend',
    `<fieldset id="barkan-controls" disabled>
      <legend>모델과 동작</legend>
      <label for="barkan-motion">동작</label>
      <select id="barkan-motion">
        <option value="Bind">기준 자세 · T포즈</option>
        <option value="Idle">대기</option>
        <option value="Walk">걷기</option>
        <option value="WingFold">날개 접기·펼치기</option>
      </select>
      <div class="buttons">
        <button id="barkan-pause" type="button">일시정지</button>
        <button id="barkan-replay" type="button">처음부터</button>
      </div>
      <label for="barkan-scrub">재생 위치 <output id="barkan-time">0.00 / 0.00초</output></label>
      <input id="barkan-scrub" type="range" min="0" max="1" step="0.001" value="0" />
      <label for="barkan-speed">재생 속도</label>
      <select id="barkan-speed">
        <option value="0.25">0.25배</option>
        <option value="0.5">0.5배</option>
        <option value="1" selected>1배</option>
      </select>
      <label for="barkan-view">시점</label>
      <select id="barkan-view">
        <option value="angle">전체 · 사선</option>
        <option value="front">정면</option>
        <option value="side">측면</option>
        <option value="back">후면</option>
        <option value="wings">날개 확대</option>
        <option value="weapon">룬 블레이드 확대</option>
      </select>
      <label class="toggle"><input id="barkan-weapon" type="checkbox" checked /> 룬 블레이드 장착</label>
      <label class="toggle"><input id="barkan-reference" type="checkbox" checked /> 1.9m 플레이어와 크기 비교</label>
      <label class="toggle"><input id="barkan-skeleton" type="checkbox" /> 뼈대 보기</label>
      <label class="toggle"><input id="barkan-wireframe" type="checkbox" /> 와이어프레임</label>
      <button id="barkan-reset" type="button">시점 초기화</button>
    </fieldset>
    <p id="barkan-stats" class="details"></p>
    <p class="details">바닥 격자 한 칸은 1m입니다. 기준 자세는 발바닥부터 가장 높은 뿔·날개 끝까지 2.5m입니다.</p>
    <p class="details">바르칸은 이동할 때 걷기만 사용합니다.</p>`
  )
  const el = <T extends HTMLElement>(id: string) =>
    document.getElementById(`barkan-${id}`) as T
  const fieldset = el<HTMLFieldSetElement>('controls')
  const motion = el<HTMLSelectElement>('motion')
  const view = el<HTMLSelectElement>('view')
  const referenceToggle = el<HTMLInputElement>('reference')
  const weaponToggle = el<HTMLInputElement>('weapon')
  const scrub = el<HTMLInputElement>('scrub')
  const speed = el<HTMLSelectElement>('speed')
  const pause = el<HTMLButtonElement>('pause')
  const replay = el<HTMLButtonElement>('replay')
  const time = el<HTMLOutputElement>('time')
  const params = new URLSearchParams(location.search)
  status.textContent = '바르칸과 비교용 플레이어를 불러오는 중…'
  const load = async (loader: GLTFLoader, url: string) => {
    const gltf = await loader.loadAsync(url)
    resources.push(gltf.scene)
    if (disposed()) {
      disposeObjects([gltf.scene])
      throw new Error('Preview closed')
    }
    return gltf
  }
  const referenceLoader = new GLTFLoader().register(() => ({
    name: 'reference-material',
    loadMaterial: async () =>
      new THREE.MeshStandardMaterial({ color: '#7f9daa', roughness: 1 }),
  }))
  const definition = getMonsterDef('barkan')!
  const [gltf, player, sword] = await Promise.all([
    load(new GLTFLoader(), '/__modular-character/parts/barkan.glb'),
    load(referenceLoader, '/__modular-character/parts/base.glb'),
    load(new GLTFLoader(), `/models/${definition.weapon}`),
  ])
  if (disposed()) return
  const model = gltf.scene
  const reference = player.scene
  reference.position.x = -1.75
  reference.visible = params.get('reference') !== '0'
  referenceToggle.checked = reference.visible
  scene.add(model, reference)
  scene.updateMatrixWorld(true)
  const modelBounds = new THREE.Box3().setFromObject(model)
  const weapon = sword.scene
  weapon.name = 'BarkanRuneBlade'
  weapon.position.set(
    definition.weaponOffsetX ?? 0,
    definition.weaponOffset ?? 0,
    definition.weaponOffsetZ ?? 0
  )
  weapon.rotation.set(...parseWeaponRotation(definition.weaponRotation))
  weapon.visible = params.get('weapon') !== '0'
  weaponToggle.checked = weapon.visible
  const hand = model.getObjectByName(definition.weaponBone ?? 'RightHand')
  if (!hand) throw new Error('Barkan weapon hand is missing')
  hand.add(weapon)
  const playerHeight = new THREE.Box3()
    .setFromObject(reference)
    .getSize(new THREE.Vector3()).y
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
  el('stats').textContent =
    `기준 높이 ${modelBounds.getSize(new THREE.Vector3()).y.toFixed(2)}m · 비교 플레이어 ${playerHeight.toFixed(2)}m · ${triangles.toLocaleString()}삼각형`
  const skeleton = new THREE.SkeletonHelper(model)
  skeleton.visible = params.get('skeleton') === '1'
  skeleton.renderOrder = 10
  for (const material of Array.isArray(skeleton.material)
    ? skeleton.material
    : [skeleton.material]) {
    material.depthTest = false
    material.depthWrite = false
  }
  scene.add(skeleton)
  cleanup.push(() => skeleton.dispose())
  const skeletonToggle = el<HTMLInputElement>('skeleton')
  skeletonToggle.checked = skeleton.visible
  skeletonToggle.onchange = () => {
    skeleton.visible = skeletonToggle.checked
  }
  const wireframe = el<HTMLInputElement>('wireframe')
  wireframe.onchange = () => {
    for (const material of materials) material.wireframe = wireframe.checked
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
  const fill = new THREE.DirectionalLight('#b1cbe8', 1.6)
  fill.position.set(3, 3, -3)
  scene.add(key, fill)
  const camera = new THREE.PerspectiveCamera(35, 1, 0.02, 100)
  const controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.minDistance = 0.4
  controls.maxDistance = 15
  cleanup.push(() => controls.dispose())
  const views: Record<string, [number, number, number]> = {
    angle: [3, 1.2, 6],
    front: [0, 0.1, 1],
    side: [1, 0.1, 0],
    back: [0, 0.1, -1],
    wings: [0, 0.1, -1],
    weapon: [1, 0.5, 1],
  }
  const requestedView = params.get('camera') ?? ''
  if (Object.hasOwn(views, requestedView)) view.value = requestedView
  const remember = () => {
    const query = new URLSearchParams(location.search)
    query.set('motion', motion.value)
    query.set('camera', view.value)
    query.set('reference', reference.visible ? '1' : '0')
    query.set('weapon', weapon.visible ? '1' : '0')
    history.replaceState(null, '', `?${query}`)
  }
  const reset = () => {
    model.updateWorldMatrix(true, true)
    const bounds = modelBounds.clone()
    if (weapon.visible) bounds.union(new THREE.Box3().setFromObject(weapon))
    if (reference.visible && !['wings', 'weapon'].includes(view.value))
      bounds.union(new THREE.Box3().setFromObject(reference))
    const sphere = bounds.getBoundingSphere(new THREE.Sphere())
    if (view.value === 'wings') {
      sphere.center.set(0, 2, -0.8)
      sphere.radius = 1.35
    }
    if (view.value === 'weapon')
      new THREE.Box3().setFromObject(weapon).getBoundingSphere(sphere)
    const halfFov = Math.atan(
      Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) *
        Math.min(camera.aspect, 1)
    )
    controls.target.copy(sphere.center)
    camera.position
      .fromArray(views[view.value])
      .normalize()
      .multiplyScalar((sphere.radius * 1.12) / Math.sin(halfFov))
      .add(sphere.center)
    controls.update()
  }
  view.onchange = () => {
    reset()
    remember()
  }
  referenceToggle.onchange = () => {
    reference.visible = referenceToggle.checked
    reset()
    remember()
  }
  weaponToggle.onchange = () => {
    weapon.visible = weaponToggle.checked
    play()
    reset()
    remember()
  }
  el('reset').onclick = reset
  const mixer = new THREE.AnimationMixer(model)
  let action: THREE.AnimationAction | undefined
  let paused = false
  const clips = new Map(gltf.animations.map((clip) => [clip.name, clip]))
  const play = () => {
    mixer.stopAllAction()
    const originalClip = clips.get(motion.value)
    const clip =
      originalClip &&
      (weapon.visible ? withBarkanRuneGrip(originalClip) : originalClip)
    action = clip ? mixer.clipAction(clip).reset().play() : undefined
    paused = false
    pause.textContent = '일시정지'
    pause.disabled = replay.disabled = scrub.disabled = !action
    scrub.value = '0'
    mixer.update(0)
    remember()
  }
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
  const requestedMotion =
    params.get('motion') === 'Run' ? 'Walk' : params.get('motion')
  if (requestedMotion && clips.has(requestedMotion))
    motion.value = requestedMotion
  const resize = () => {
    camera.aspect = host.clientWidth / Math.max(host.clientHeight, 1)
    camera.updateProjectionMatrix()
    renderer.setSize(host.clientWidth, host.clientHeight)
  }
  const observer = new ResizeObserver(resize)
  observer.observe(host)
  cleanup.push(() => observer.disconnect())
  resize()
  play()
  reset()
  let previous = performance.now()
  renderer.setAnimationLoop((now) => {
    const dt = Math.min((now - previous) / 1000, 0.05)
    previous = now
    if (!paused) mixer.update(dt * Number(speed.value))
    if (action) scrub.value = String(action.time / action.getClip().duration)
    time.textContent = `${(action?.time ?? 0).toFixed(2)} / ${(action?.getClip().duration ?? 0).toFixed(2)}초`
    controls.update()
    renderer.render(scene, camera)
  })
  barkanPreview = {
    model,
    reference,
    weapon,
    mixer,
    currentAction: () => action,
  }
  cleanup.push(() => {
    mixer.stopAllAction()
    mixer.uncacheRoot(model)
    barkanPreview = undefined
  })
  fieldset.disabled = false
  status.textContent = '바르칸을 불러왔습니다. 동작과 시점을 선택해 보세요.'
  document.body.dataset.ready = 'true'
}
