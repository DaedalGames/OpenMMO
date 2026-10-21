import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js'
import { disposeObjects } from './dispose-objects'

const MOTIONS: [string, string][] = [
  ['Bind', '기준 자세'],
  ['Idle', '대기'],
  ['Attack', '오른팔 내려찍기'],
  ['AttackLeft', '왼팔 내려찍기'],
  ['Roar', '포효'],
  ['Hit', '피격'],
  ['Death', '사망'],
  ['Dead', '사망 후'],
]

// Game camera seen from a west-facing boss: orthographic, pitch atan(1/√2).
const VIEWS: Record<string, [number, number, number]> = {
  game: [1, 1, 1],
  angle: [-0.6, 0.35, 1],
  front: [0, 0.1, 1],
  side: [1, 0.1, 0],
  back: [0, 0.1, -1],
}

export async function showTerraclash(
  scene: THREE.Scene,
  resources: THREE.Object3D[],
  cleanup: (() => void)[],
  disposed: () => boolean
) {
  document.title = '테라클래시 · 캐릭터 미리보기'
  document.querySelector('h1')!.textContent = '테라클래시 미리보기'
  document.querySelector('header p:last-child')!.textContent =
    '9m 테라클래시의 리그와 동작, 잠든 바위 모습을 살펴보세요.'
  document
    .querySelector('nav[aria-label="광휘의 투구 착용 비교"]')
    ?.setAttribute('hidden', '')
  const status = document.getElementById('status')!
  const aside = document.querySelector('aside')!
  aside.replaceChildren(status)
  aside.insertAdjacentHTML(
    'beforeend',
    `<fieldset id="terraclash-controls" disabled>
      <legend>모델과 동작</legend>
      <label for="terraclash-state">상태</label>
      <select id="terraclash-state">
        <option value="awake">깨어남 · 리그</option>
        <option value="dormant">잠듦 · 바위</option>
      </select>
      <label for="terraclash-motion">동작</label>
      <select id="terraclash-motion">${MOTIONS.map(
        ([value, label]) => `<option value="${value}">${label}</option>`
      ).join('')}</select>
      <div class="buttons">
        <button id="terraclash-pause" type="button">일시정지</button>
        <button id="terraclash-replay" type="button">처음부터</button>
      </div>
      <label for="terraclash-scrub">재생 위치 <output id="terraclash-time">0.00 / 0.00초</output></label>
      <input id="terraclash-scrub" type="range" min="0" max="1" step="0.001" value="0" />
      <label for="terraclash-speed">재생 속도</label>
      <select id="terraclash-speed">
        <option value="0.25">0.25배</option>
        <option value="0.5">0.5배</option>
        <option value="1" selected>1배</option>
      </select>
      <label for="terraclash-view">시점</label>
      <select id="terraclash-view">
        <option value="game">게임 카메라</option>
        <option value="angle">사선</option>
        <option value="front">정면</option>
        <option value="side">측면</option>
        <option value="back">후면</option>
      </select>
      <label class="toggle"><input id="terraclash-reference" type="checkbox" checked /> 1.9m 플레이어와 크기 비교</label>
      <label class="toggle"><input id="terraclash-skeleton" type="checkbox" /> 뼈대 보기</label>
      <label class="toggle"><input id="terraclash-wireframe" type="checkbox" /> 와이어프레임</label>
      <button id="terraclash-reset" type="button">시점 초기화</button>
    </fieldset>
    <p id="terraclash-stats" class="details"></p>
    <p class="details">바닥 격자 한 칸은 1m입니다. 게임 카메라는 실제 게임과 같은 정사영 각도입니다.</p>`
  )
  const el = <T extends HTMLElement>(id: string) =>
    document.getElementById(`terraclash-${id}`) as T
  const fieldset = el<HTMLFieldSetElement>('controls')
  const state = el<HTMLSelectElement>('state')
  const motion = el<HTMLSelectElement>('motion')
  const view = el<HTMLSelectElement>('view')
  const referenceToggle = el<HTMLInputElement>('reference')
  const scrub = el<HTMLInputElement>('scrub')
  const speed = el<HTMLSelectElement>('speed')
  const pause = el<HTMLButtonElement>('pause')
  const replay = el<HTMLButtonElement>('replay')
  const time = el<HTMLOutputElement>('time')
  const params = new URLSearchParams(location.search)
  status.textContent = '테라클래시와 비교용 플레이어를 불러오는 중…'

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
  const [gltf, dormantGltf, player] = await Promise.all([
    load(new GLTFLoader(), '/__modular-character/parts/terraclash.glb'),
    load(new GLTFLoader(), '/models/monsters/terraclash_dormant.glb'),
    load(referenceLoader, '/__modular-character/parts/base.glb'),
  ])
  if (disposed()) return
  const model = gltf.scene
  const dormant = dormantGltf.scene
  const reference = player.scene
  reference.position.set(-1.5, 0, 6)
  reference.visible = params.get('reference') !== '0'
  referenceToggle.checked = reference.visible
  scene.add(model, dormant, reference)

  const triangles = (root: THREE.Object3D) => {
    let count = 0
    root.traverse((node) => {
      if (node instanceof THREE.Mesh)
        count +=
          (node.geometry.index?.count ??
            node.geometry.attributes.position.count) / 3
    })
    return count
  }
  const materials = new Set<THREE.MeshStandardMaterial>()
  for (const root of [model, dormant])
    root.traverse((node) => {
      if (!(node instanceof THREE.Mesh)) return
      for (const material of [node.material].flat())
        if (material instanceof THREE.MeshStandardMaterial)
          materials.add(material)
    })

  const skeleton = new THREE.SkeletonHelper(model)
  skeleton.visible = params.get('skeleton') === '1'
  skeleton.renderOrder = 10
  for (const material of [skeleton.material].flat()) {
    material.depthTest = false
    material.depthWrite = false
  }
  scene.add(skeleton)
  cleanup.push(() => skeleton.dispose())
  const skeletonToggle = el<HTMLInputElement>('skeleton')
  skeletonToggle.checked = skeleton.visible
  skeletonToggle.onchange = () => {
    skeleton.visible = skeletonToggle.checked && model.visible
  }
  el<HTMLInputElement>('wireframe').onchange = (event) => {
    const on = (event.target as HTMLInputElement).checked
    for (const material of materials) material.wireframe = on
  }

  const grid = new THREE.GridHelper(20, 20, '#57717a', '#30454e')
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
  const sun = new THREE.DirectionalLight('#fff1e0', 2.5)
  sun.position.set(-6, 12, 10)
  scene.add(sun)

  const perspective = new THREE.PerspectiveCamera(35, 1, 0.1, 200)
  const ortho = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 200)
  let camera: THREE.Camera = perspective
  const controls = new OrbitControls(perspective, renderer.domElement)
  controls.enableDamping = true
  cleanup.push(() => controls.dispose())
  const requestedView = params.get('camera') ?? ''
  if (Object.hasOwn(VIEWS, requestedView)) view.value = requestedView
  const requestedState = params.get('state') ?? ''
  if (requestedState === 'dormant') state.value = 'dormant'

  const resize = () => {
    const aspect = host.clientWidth / Math.max(host.clientHeight, 1)
    perspective.aspect = aspect
    perspective.updateProjectionMatrix()
    // The game frustum is 20m tall at default zoom.
    ortho.left = -10 * aspect
    ortho.right = 10 * aspect
    ortho.top = 10
    ortho.bottom = -10
    ortho.updateProjectionMatrix()
    renderer.setSize(host.clientWidth, host.clientHeight)
  }
  const reset = () => {
    const target = new THREE.Vector3(0, 4.5, 0)
    const dir = new THREE.Vector3().fromArray(VIEWS[view.value]).normalize()
    if (view.value === 'game') {
      camera = ortho
      controls.enabled = false
      ortho.position.copy(target).addScaledVector(dir, 60)
      ortho.lookAt(target)
    } else {
      camera = perspective
      controls.enabled = true
      controls.object = perspective
      controls.target.copy(target)
      perspective.position.copy(target).addScaledVector(dir, 26)
      controls.update()
    }
  }
  const remember = () => {
    const query = new URLSearchParams(location.search)
    query.set('state', state.value)
    query.set('motion', motion.value)
    query.set('camera', view.value)
    query.set('reference', reference.visible ? '1' : '0')
    history.replaceState(null, '', `?${query}`)
  }

  const mixer = new THREE.AnimationMixer(model)
  const clips = new Map(gltf.animations.map((clip) => [clip.name, clip]))
  let action: THREE.AnimationAction | undefined
  let paused = false
  const play = () => {
    mixer.stopAllAction()
    const clip = clips.get(motion.value)
    action = clip ? mixer.clipAction(clip).reset().play() : undefined
    paused = false
    pause.textContent = '일시정지'
    const awake = state.value === 'awake'
    pause.disabled = replay.disabled = scrub.disabled = !action || !awake
    motion.disabled = !awake
    scrub.value = '0'
    mixer.update(0)
    remember()
  }
  const applyState = () => {
    const awake = state.value === 'awake'
    model.visible = awake
    dormant.visible = !awake
    skeleton.visible = skeletonToggle.checked && awake
    const size = new THREE.Box3()
      .setFromObject(awake ? model : dormant)
      .getSize(new THREE.Vector3())
    el('stats').textContent =
      `${size.x.toFixed(1)} × ${size.y.toFixed(1)} × ${size.z.toFixed(1)}m · ` +
      `${Math.round(triangles(awake ? model : dormant)).toLocaleString()}삼각형`
    play()
  }
  state.onchange = applyState
  motion.onchange = play
  replay.onclick = play
  view.onchange = () => {
    reset()
    remember()
  }
  referenceToggle.onchange = () => {
    reference.visible = referenceToggle.checked
    remember()
  }
  el('reset').onclick = reset
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
  const requestedMotion = params.get('motion')
  if (
    requestedMotion &&
    (clips.has(requestedMotion) || requestedMotion === 'Bind')
  )
    motion.value = requestedMotion
  else motion.value = 'Idle'

  const observer = new ResizeObserver(resize)
  observer.observe(host)
  cleanup.push(() => observer.disconnect())
  resize()
  applyState()
  reset()
  let previous = performance.now()
  renderer.setAnimationLoop((now) => {
    const dt = Math.min((now - previous) / 1000, 0.05)
    previous = now
    if (!paused) mixer.update(dt * Number(speed.value))
    if (action) scrub.value = String(action.time / action.getClip().duration)
    time.textContent = `${(action?.time ?? 0).toFixed(2)} / ${(action?.getClip().duration ?? 0).toFixed(2)}초`
    if (controls.enabled) controls.update()
    renderer.render(scene, camera)
  })
  cleanup.push(() => {
    mixer.stopAllAction()
    mixer.uncacheRoot(model)
  })
  fieldset.disabled = false
  status.textContent =
    '테라클래시를 불러왔습니다. 상태와 동작, 시점을 골라 보세요.'
  document.body.dataset.ready = 'true'
}
