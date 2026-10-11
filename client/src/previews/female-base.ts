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
    '여성 기본 체형의 자세와 동작을 살펴보세요.'
  const status = document.getElementById('status')!
  const aside = document.querySelector('aside')!
  aside.replaceChildren(status)
  aside.insertAdjacentHTML(
    'beforeend',
    `
    <fieldset id="female-controls" disabled>
      <legend>모델 살펴보기</legend>
      <label for="female-motion">동작</label>
      <select id="female-motion">
        <option value="rest">기본 A 포즈</option>
        <option value="idle1">대기</option>
        <option value="walk">걷기</option>
        <option value="run">달리기</option>
        <option value="jump">점프</option>
        <option value="combat_idle">전투 대기</option>
        <option value="slash1">베기</option>
        <option value="dying">쓰러지기</option>
        <option value="sit_idle">앉기</option>
      </select>
      <label for="female-equipment">장착 상태</label>
      <select id="female-equipment">
        <option value="unarmed">맨손</option>
        <option value="armed">강철 장검</option>
      </select>
      <p class="details">대기와 걷기에서 장착 상태에 따라 손 모양이 바뀝니다.</p>
      <button id="female-pause" type="button">일시정지</button>
      <label for="female-time">동작 시점</label>
      <input id="female-time" type="range" min="0" max="1" step="0.001" value="0" />
      <label for="female-camera">시점</label>
      <select id="female-camera">
        <option value="face">얼굴 확대</option>
        <option value="full">전신 정면</option>
        <option value="side">전신 측면</option>
        <option value="back">전신 후면</option>
        <option value="feet">발 확대</option>
        <option value="right-hand">오른손 확대</option>
        <option value="left-hand">왼손 확대</option>
      </select>
      <label class="toggle"><input id="female-wireframe" type="checkbox" /> 와이어프레임</label>
      <label class="toggle"><input id="female-skeleton" type="checkbox" /> 뼈대 보기</label>
      <button id="female-reset" type="button">시점 초기화</button>
    </fieldset>
    <p id="female-stats" class="details"></p>
    <p class="details">여성 체형에 맞춘 뼈대와 동작을 확인할 수 있습니다. 복장 교체는 준비 중입니다.</p>`
  )
  status.textContent = '여성 베이스를 불러오는 중…'
  const loader = new GLTFLoader()
  const [{ scene: model, animations }, { scene: weapon }] = await Promise.all([
    loader.loadAsync('/__modular-character/parts/female_base.glb'),
    loader.loadAsync('/models/weapons/steel_longsword.glb'),
  ])
  const hand = model.getObjectByName('RightHand')
  if (!hand) throw new Error('검을 장착할 오른손 본을 찾지 못했습니다.')
  weapon.name = 'femaleSteelLongsword'
  weapon.scale.setScalar(1 / 1.8)
  weapon.position.set(0.028, 0.064, 0.011)
  weapon.rotation.z = 0.2
  hand.add(weapon)
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
  const bones: THREE.Bone[] = []
  model.traverse((node) => {
    if (node instanceof THREE.Bone) bones.push(node)
  })
  const rest = bones.map((bone) => ({
    bone,
    position: bone.position.clone(),
    quaternion: bone.quaternion.clone(),
    scale: bone.scale.clone(),
  }))
  const mixer = new THREE.AnimationMixer(model)
  let action: THREE.AnimationAction | undefined
  let paused = false
  const motion = document.getElementById('female-motion') as HTMLSelectElement
  const equipment = document.getElementById(
    'female-equipment'
  ) as HTMLSelectElement
  const pause = document.getElementById('female-pause') as HTMLButtonElement
  const time = document.getElementById('female-time') as HTMLInputElement
  const handPose = (clipName: string) => {
    const clip = animations.find((entry) => entry.name === clipName)
    if (!clip) throw new Error(`손 자세를 찾지 못했습니다: ${clipName}`)
    return clip.tracks
      .filter((track) =>
        /^RightHand(Thumb|Index|Middle|Ring|Pinky)[123]\.quaternion$/.test(
          track.name
        )
      )
      .map((track) => {
        const bone = model.getObjectByName(track.name.split('.')[0])
        if (!bone) throw new Error(`손가락 본을 찾지 못했습니다: ${track.name}`)
        return {
          bone,
          rotation: new THREE.Quaternion().fromArray(track.values),
        }
      })
  }
  const handPoses = {
    unarmed: handPose('idle1'),
    armed: handPose('idle_armed'),
  }
  const updateAnimation = (delta: number) => {
    mixer.update(delta)
    if (!['idle1', 'walk'].includes(motion.value)) return
    const pose =
      equipment.value === 'armed' ? handPoses.armed : handPoses.unarmed
    for (const { bone, rotation } of pose) bone.quaternion.copy(rotation)
  }
  const setPaused = (value: boolean) => {
    paused = value
    pause.textContent = paused ? '재생' : '일시정지'
  }
  const play = () => {
    mixer.stopAllAction()
    for (const state of rest) {
      state.bone.position.copy(state.position)
      state.bone.quaternion.copy(state.quaternion)
      state.bone.scale.copy(state.scale)
    }
    weapon.visible = equipment.value === 'armed'
    const clip = animations.find((entry) => entry.name === motion.value)
    action = clip ? mixer.clipAction(clip).reset().play() : undefined
    if (action) {
      action.setLoop(
        ['jump', 'slash1', 'dying'].includes(motion.value)
          ? THREE.LoopOnce
          : THREE.LoopRepeat,
        Infinity
      )
      action.clampWhenFinished = true
    }
    time.value = '0'
    time.disabled = pause.disabled = !action
    setPaused(false)
    updateAnimation(0)
    if (select.value.endsWith('-hand')) reset()
    status.textContent = ['idle1', 'walk'].includes(motion.value)
      ? `${motion.selectedOptions[0].textContent} · ${equipment.selectedOptions[0].textContent}`
      : motion.selectedOptions[0].textContent
    updateStats()
  }
  motion.onchange = play
  equipment.onchange = () => {
    const fraction = action ? action.time / action.getClip().duration : 0
    const wasPaused = paused
    play()
    if (action) {
      action.time = fraction * action.getClip().duration
      time.value = String(fraction)
      updateAnimation(0)
      setPaused(wasPaused)
    }
    if (select.value.endsWith('-hand')) reset()
  }
  pause.onclick = () => {
    if (action && action.time >= action.getClip().duration) {
      action.reset().play()
      time.value = '0'
      setPaused(false)
    } else {
      setPaused(!paused)
    }
  }
  mixer.addEventListener('finished', () => {
    setPaused(true)
    pause.textContent = '다시 재생'
  })
  time.oninput = () => {
    if (!action) return
    setPaused(true)
    action.paused = false
    action.time = Number(time.value) * action.getClip().duration
    updateAnimation(0)
    if (select.value.endsWith('-hand')) reset()
  }
  const skeleton = new THREE.SkeletonHelper(model)
  const skeletonToggle = document.getElementById(
    'female-skeleton'
  ) as HTMLInputElement
  skeleton.visible = skeletonToggle.checked =
    new URLSearchParams(location.search).get('skeleton') === '1'
  for (const material of Array.isArray(skeleton.material)
    ? skeleton.material
    : [skeleton.material]) {
    material.depthTest = false
  }
  skeleton.renderOrder = 10
  scene.add(skeleton)
  skeletonToggle.onchange = () => {
    skeleton.visible = skeletonToggle.checked
  }
  cleanup.push(() => {
    mixer.stopAllAction()
    mixer.uncacheRoot(model)
    scene.remove(skeleton)
    skeleton.dispose()
  })
  let triangles = 0
  let weaponTriangles = 0
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
  weapon.traverse((node) => {
    if (node instanceof THREE.Mesh)
      weaponTriangles +=
        (node.geometry.index?.count ??
          node.geometry.attributes.position.count) / 3
  })
  const updateStats = () => {
    const visibleTriangles = triangles - (weapon.visible ? 0 : weaponTriangles)
    document.getElementById('female-stats')!.textContent =
      `${visibleTriangles.toLocaleString()}삼각형 · ${bones.length}개 본 · ${animations.length}가지 동작`
  }
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
    'right-hand': {
      target: [-0.12, 0.48, 0.015],
      position: [-0.45, 0.49, 0.13],
    },
    'left-hand': {
      target: [0.145, 0.48, -0.01],
      position: [0.475, 0.49, 0.105],
    },
  }
  const select = document.getElementById('female-camera') as HTMLSelectElement
  const requested = new URLSearchParams(location.search).get('camera')
  select.value =
    requested && Object.hasOwn(views, requested) ? requested : 'full'
  const reset = () => {
    const view = views[select.value]
    const aspect = host.clientWidth / host.clientHeight
    controls.target.fromArray(view.target)
    camera.position.fromArray(view.position)
    camera.position
      .sub(controls.target)
      .multiplyScalar(Math.max(1, 1 / aspect))
      .add(controls.target)
    if (select.value.endsWith('-hand')) {
      model.updateMatrixWorld(true)
      const side = select.value === 'right-hand' ? 'Right' : 'Left'
      const wrist = model
        .getObjectByName(`${side}Hand`)!
        .getWorldPosition(new THREE.Vector3())
      const tip = model
        .getObjectByName(`${side}HandMiddle4`)!
        .getWorldPosition(new THREE.Vector3())
      const target = wrist.add(tip).multiplyScalar(0.5)
      camera.position.add(target.clone().sub(controls.target))
      controls.target.copy(target)
    }
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
  const params = new URLSearchParams(location.search)
  const requestedMotion = params.get('motion') ?? 'idle1'
  equipment.value =
    params.get('equipment') === 'armed' || requestedMotion === 'idle_armed'
      ? 'armed'
      : 'unarmed'
  motion.value =
    requestedMotion === 'idle_armed'
      ? 'idle1'
      : requestedMotion === 'rest' ||
          animations.some((clip) => clip.name === requestedMotion)
        ? requestedMotion
        : 'idle1'
  play()
  const requestedTime = Number(params.get('time'))
  if (params.has('time') && Number.isFinite(requestedTime) && action) {
    time.value = String(THREE.MathUtils.clamp(requestedTime, 0, 1))
    time.dispatchEvent(new Event('input'))
  }
  let previousTime = performance.now()
  renderer.setAnimationLoop((now) => {
    const delta = Math.min((now - previousTime) / 1000, 0.05)
    previousTime = now
    if (!paused && action) {
      updateAnimation(delta)
      time.value = String(action.time / action.getClip().duration)
    }
    controls.update()
    renderer.render(scene, camera)
  })
  const fieldset = document.getElementById(
    'female-controls'
  ) as HTMLFieldSetElement
  fieldset.disabled = false
  document.body.dataset.ready = 'true'
}
