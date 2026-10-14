import * as THREE from 'three'
import { disposeObjects } from './dispose-objects'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js'
import { femaleSeat, femaleSeatOffset } from './female-seat'
import { femaleTorchMotions, mirroredSwordGrip } from './female-torch'
import { poseOffHandProp } from '../lib/utils/handProps'
import { bindModularPart } from '../lib/utils/modularCharacter'
import { femaleOutfitMask } from '../lib/utils/female-outfit-mask'
import { femaleBootGround } from '../lib/utils/female-boot-ground'

export async function showFemaleBase(
  scene: THREE.Scene,
  resources: THREE.Object3D[],
  cleanup: (() => void)[],
  disposed: () => boolean
) {
  document.title = '여성 베이스 · 캐릭터 미리보기'
  document.querySelector('h1')!.textContent = '여성 베이스 미리보기'
  document.querySelector('header p:last-child')!.textContent =
    '여성 체형에 맞춘 의상과 헤어, 동작을 살펴보세요.'
  const status = document.getElementById('status')!
  const aside = document.querySelector('aside')!
  aside.replaceChildren(status)
  aside.insertAdjacentHTML(
    'beforeend',
    `
    <fieldset id="female-controls" disabled>
      <legend>모델 살펴보기</legend>
      <label for="female-hair">헤어</label>
      <select id="female-hair">
        <option value="bob">금발 단발</option>
        <option value="none">없음</option>
        <option value="knight">긴 금발 (보관본)</option>
      </select>
      <a href="?asset=female-knight-bob">단발 원본 단독 보기</a>
      <label for="female-helmet">투구</label>
      <select id="female-helmet">
        <option value="none">없음</option>
        <option value="knight">은빛 기사 투구</option>
      </select>
      <p class="details">투구를 쓰면 헤어를 숨기고, 벗으면 선택한 헤어를 복원합니다.</p>
      <label for="female-top">상의</label>
      <select id="female-top">
        <option value="none">없음</option>
        <option value="knight">은빛 기사 갑옷</option>
        <option value="barbarian">야만전사 가죽 철갑</option>
      </select>
      <label for="female-bottom">하의</label>
      <select id="female-bottom">
        <option value="none">없음</option>
        <option value="knight">은빛 기사 골반 갑옷</option>
        <option value="barbarian">야만전사 모피 허리치마</option>
      </select>
      <label for="female-boots">신발</label>
      <select id="female-boots">
        <option value="none">없음</option>
        <option value="knight">은빛 기사 판금 부츠</option>
      </select>
      <label for="female-gloves">장갑</label>
      <select id="female-gloves">
        <option value="none">없음</option>
        <option value="knight">은빛 기사 판금 장갑</option>
      </select>
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
        <option value="torch">왼손 횃불</option>
        <option value="armed-torch">강철 장검 + 횃불</option>
        <option value="shield">왼손 나무 방패</option>
        <option value="armed-shield">강철 장검 + 나무 방패</option>
      </select>
      <p class="details">대기와 걷기에서 장착 상태에 따라 손 모양이 바뀝니다.</p>
      <p class="details">횃불을 장착하면 대기·걷기·달리기·전투 대기에서 왼손에 횃불을 듭니다.</p>
      <button id="female-pause" type="button">일시정지</button>
      <label for="female-time">동작 시점</label>
      <input id="female-time" type="range" min="0" max="1" step="0.001" value="0" />
      <label for="female-camera">시점</label>
      <select id="female-camera">
        <option value="face">얼굴 확대</option>
        <option value="upper">상의 확대</option>
        <option value="lower">하의 확대</option>
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
    <p class="details">투구·상의·하의·장갑·신발·헤어를 바꿔 착용 상태와 동작을 확인할 수 있습니다.</p>`
  )
  status.textContent = '미리보기 에셋을 준비하는 중…'
  const loader = new GLTFLoader(new THREE.LoadingManager())
  const hairSelect = document.getElementById('female-hair') as HTMLSelectElement
  const requestedHair = new URLSearchParams(location.search).get('hair')
  hairSelect.value =
    requestedHair && ['bob', 'knight', 'none'].includes(requestedHair)
      ? requestedHair
      : 'bob'
  const initialHair = hairSelect.value
  loader.manager.onProgress = (_url, loaded, total) => {
    if (!disposed())
      status.textContent = `미리보기 에셋을 불러오는 중… (${loaded}/${total})`
  }
  const [
    base,
    { scene: weapon },
    { scene: chair },
    { scene: torch },
    { scene: shield },
    prepared,
    initialHairAsset,
  ] = await Promise.all([
    loader.loadAsync('/__female-preview/base.glb'),
    loader.loadAsync('/models/weapons/steel_longsword.glb'),
    loader.loadAsync(`/models/${femaleSeat.chair.model}`),
    loader.loadAsync('/models/weapons/torch.glb'),
    loader.loadAsync('/models/armor/shield_wooden.glb'),
    fetch('/__female-preview/animations.json').then(async (response) => {
      if (!response.ok) throw new Error('여성 동작을 불러오지 못했습니다.')
      return (await response.json()) as {
        clips: ReturnType<typeof THREE.AnimationClip.toJSON>[]
      }
    }),
    initialHair === 'none'
      ? null
      : loader.loadAsync(`/__female-preview/${initialHair}.glb`),
  ])
  const { scene: model, animations } = base
  loader.manager.onProgress = () => {}
  for (const data of prepared.clips) {
    const clip = THREE.AnimationClip.parse(data)
    const index = animations.findIndex((entry) => entry.name === clip.name)
    if (index === -1) animations.push(clip)
    else animations[index] = clip
  }
  const hairOptions: Record<string, THREE.SkinnedMesh[]> = { none: [] }
  if (initialHairAsset)
    hairOptions[initialHair] = bindModularPart(model, initialHairAsset.scene)
  const pendingHair = new Map<string, Promise<THREE.SkinnedMesh[]>>()
  const loadHair = (name: string): Promise<THREE.SkinnedMesh[]> => {
    if (hairOptions[name]) return Promise.resolve(hairOptions[name])
    const pending = pendingHair.get(name)
    if (pending) return pending
    const promise = loader
      .loadAsync(`/__female-preview/${name}.glb`)
      .then(({ scene: source }) => {
        if (disposed()) {
          disposeObjects([source])
          return []
        }
        const meshes = bindModularPart(model, source)
        for (const mesh of meshes) mesh.visible = false
        hairOptions[name] = meshes
        return meshes
      })
      .finally(() => pendingHair.delete(name))
    pendingHair.set(name, promise)
    return promise
  }
  let helmetEquipped = false
  const updateHair = () => {
    for (const [name, meshes] of Object.entries(hairOptions))
      for (const mesh of meshes)
        mesh.visible = !helmetEquipped && hairSelect.value === name
  }
  updateHair()
  const swordGrip = animations.find((clip) => clip.name === 'idle_armed')
  const catwalk = animations.find((clip) => clip.name === 'walk')
  const combatIdle = animations.find((clip) => clip.name === 'combat_idle')
  if (!swordGrip || !catwalk || !combatIdle)
    throw new Error('검을 쥐는 손 자세 또는 걷기 동작을 찾지 못했습니다.')
  chair.scale.setScalar(1 / femaleSeat.characterHeight)
  chair.visible = false
  resources.push(chair)
  const hand = model.getObjectByName('RightHand')
  if (!hand) throw new Error('검을 장착할 오른손 본을 찾지 못했습니다.')
  weapon.name = 'femaleSteelLongsword'
  weapon.scale.setScalar(1 / 1.8)
  weapon.position.set(0.028, 0.064, 0.011)
  weapon.rotation.z = 0.2
  hand.add(weapon)
  const leftHand = model.getObjectByName('LeftHand')
  if (!leftHand) throw new Error('횃불을 장착할 왼손 본을 찾지 못했습니다.')
  torch.name = 'femaleTorch'
  torch.visible = false
  torch.scale.setScalar(1 / femaleSeat.characterHeight)
  torch.position.set(-0.004, 0.049, 0.009)
  torch.rotation.set(0, Math.PI, 0.2)
  leftHand.add(torch)
  shield.name = 'femaleWoodenShield'
  shield.visible = false
  shield.scale.setScalar(1 / femaleSeat.characterHeight)
  poseOffHandProp(shield, 'armor/shield_wooden.glb')
  shield.position.set(-0.004, 0.031, -0.008)
  leftHand.add(shield)
  const shieldGrip = mirroredSwordGrip(model, swordGrip).map((track) => ({
    bone: model.getObjectByName(track.name.split('.')[0])!,
    rotation: new THREE.Quaternion().fromArray(track.values),
  }))
  resources.push(model)
  if (disposed()) {
    disposeObjects([model, chair])
    return
  }
  scene.add(model)
  scene.add(chair)
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
  let bootGround: ReturnType<typeof femaleBootGround> | undefined
  let bootsEquipped = false
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
    bootGround?.restore()
    mixer.update(delta)
    if (shield.visible && motion.value !== 'rest') {
      for (const { bone, rotation } of shieldGrip)
        bone.quaternion.copy(rotation)
    }
    if (
      !['idle1', 'walk'].includes(motion.value) &&
      !(
        ['armed-torch', 'armed-shield'].includes(equipment.value) &&
        motion.value === 'run'
      )
    )
      return
    const pose = ['armed', 'armed-torch', 'armed-shield'].includes(
      equipment.value
    )
      ? handPoses.armed
      : handPoses.unarmed
    for (const { bone, rotation } of pose) bone.quaternion.copy(rotation)
  }
  const setPaused = (value: boolean) => {
    paused = value
    pause.textContent = paused ? '재생' : '일시정지'
  }
  const updateStatus = () => {
    status.textContent = ['idle1', 'walk', 'run', 'combat_idle'].includes(
      motion.value
    )
      ? `${motion.selectedOptions[0].textContent} · ${equipment.selectedOptions[0].textContent}`
      : motion.selectedOptions[0].textContent
  }
  const play = () => {
    bootGround?.restore()
    mixer.stopAllAction()
    chair.visible = motion.value === 'sit_idle'
    model.position.y = chair.visible ? femaleSeatOffset : 0
    for (const state of rest) {
      state.bone.position.copy(state.position)
      state.bone.quaternion.copy(state.quaternion)
      state.bone.scale.copy(state.scale)
    }
    weapon.visible = ['armed', 'armed-torch', 'armed-shield'].includes(
      equipment.value
    )
    shield.visible = ['shield', 'armed-shield'].includes(equipment.value)
    torch.visible =
      ['torch', 'armed-torch'].includes(equipment.value) &&
      !!femaleTorchMotions[motion.value]
    const clipName =
      torch.visible && weapon.visible && motion.value === 'idle1'
        ? 'torch_sword_idle1'
        : torch.visible
          ? femaleTorchMotions[motion.value]
          : motion.value
    const clip = animations.find((entry) => entry.name === clipName)
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
    if (select.value === 'full' || select.value.endsWith('-hand')) reset()
    updateStatus()
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
  const materials = new Set<THREE.MeshStandardMaterial>()
  const collectMaterials = (root: THREE.Object3D) => {
    root.traverse((node) => {
      if (!(node instanceof THREE.Mesh)) return
      for (const material of Array.isArray(node.material)
        ? node.material
        : [node.material])
        if (material instanceof THREE.MeshStandardMaterial)
          materials.add(material)
    })
  }
  collectMaterials(model)
  const outfitMask = femaleOutfitMask(base)
  let glovesEquipped = false
  let sleeveMaskRegistered = false
  const updateGround = () => {
    bootGround?.restore()
    model.position.y = chair.visible ? femaleSeatOffset : 0
    if (bootsEquipped && bootGround) {
      const lift = bootGround.apply(
        chair.visible ? femaleSeatOffset : undefined,
        motion.value
      )
      if (!chair.visible) model.position.y = lift
    }
  }
  cleanup.push(() => outfitMask.dispose())
  const outfitSlots = ['top', 'bottom', 'boots', 'gloves', 'helmet']
  const outfitUpdates = outfitSlots.map((slot) => {
    const select = document.getElementById(
      `female-${slot}`
    ) as HTMLSelectElement
    const outfits = [...select.options]
      .map((option) => option.value)
      .filter((value) => value !== 'none')
    const requestedOutfit = new URLSearchParams(location.search).get(slot)
    select.value =
      requestedOutfit && outfits.includes(requestedOutfit)
        ? requestedOutfit
        : 'none'
    const loaded = new Map<
      string,
      { meshes?: THREE.SkinnedMesh[]; pending?: Promise<void> }
    >()
    const maskName = (outfit: string) => `${slot}-${outfit}`
    const load = (outfit: string) => {
      const entry = loaded.get(outfit) ?? {}
      loaded.set(outfit, entry)
      if (!entry.pending) {
        let source: THREE.Object3D | undefined
        // Glove sleeve cutouts only exist for the knight top.
        const sleeves = slot === 'top' && outfit === 'knight'
        entry.pending = (async () => {
          const response = await fetch(
            `/__modular-character/female-${outfit}-${slot}-occlusion.json`
          )
          if (!response.ok)
            throw new Error('의상 가림 정보를 불러오지 못했습니다.')
          const mask: unknown = await response.json()
          let sleeveMask: unknown
          if (sleeves) {
            const response = await fetch(
              '/__modular-character/female-knight-gloves-top-occlusion.json'
            )
            if (!response.ok)
              throw new Error('장갑과 소매의 가림 정보를 불러오지 못했습니다.')
            sleeveMask = await response.json()
          }
          const asset = await loader.loadAsync(
            `/__modular-character/parts/female_${outfit}_${slot}.glb`
          )
          source = asset.scene
          if (disposed()) {
            disposeObjects([source])
            return
          }
          outfitMask.register(maskName(outfit), mask)
          const meshes = (entry.meshes = bindModularPart(model, source))
          if (sleeves) {
            outfitMask.register('glove-sleeves', sleeveMask, meshes[0])
            sleeveMaskRegistered = true
            outfitMask.setEquipped('glove-sleeves', glovesEquipped)
          }
          if (slot === 'boots') {
            let body: THREE.SkinnedMesh | undefined
            model.traverse((node) => {
              const association = base.parser.associations.get(node)
              if (
                node instanceof THREE.SkinnedMesh &&
                association?.meshes === 0 &&
                association.primitives === 0
              )
                body = node
            })
            if (!body) throw new Error('부츠의 기준 몸체를 찾지 못했습니다.')
            bootGround = femaleBootGround(
              model,
              body,
              meshes,
              source.userData.heel_pose
            )
          }
          for (const mesh of meshes) {
            mesh.visible = false
            if (slot === 'gloves' || slot === 'helmet')
              mesh.frustumCulled = false
            collectMaterials(mesh)
          }
          resources.push(source)
          for (const material of materials)
            material.wireframe = wireframe.checked
        })().catch((error: unknown) => {
          outfitMask.unregister(maskName(outfit))
          if (sleeves) {
            outfitMask.unregister('glove-sleeves')
            sleeveMaskRegistered = false
          }
          for (const mesh of entry.meshes ?? []) mesh.removeFromParent()
          if (source) disposeObjects([source])
          loaded.delete(outfit)
          throw error
        })
      }
      return entry.pending
    }
    const show = (outfit: string) => {
      for (const [name, entry] of loaded) {
        if (!entry.meshes) continue
        outfitMask.setEquipped(maskName(name), name === outfit)
        for (const mesh of entry.meshes) mesh.visible = name === outfit
      }
    }
    const update = async () => {
      const requested = select.value
      try {
        if (requested !== 'none' && !loaded.get(requested)?.meshes) {
          status.textContent = '갑옷을 불러오는 중…'
          await load(requested)
        }
        if (disposed() || select.value !== requested) return
        const equipped = requested !== 'none'
        if (slot === 'boots') bootsEquipped = equipped
        if (slot === 'helmet') {
          helmetEquipped = equipped
          updateHair()
          if (
            (document.getElementById('female-camera') as HTMLSelectElement)
              .value === 'face'
          )
            reset()
        }
        if (slot === 'gloves') {
          glovesEquipped = equipped
          if (sleeveMaskRegistered)
            outfitMask.setEquipped('glove-sleeves', equipped)
        }
        show(requested)
        updateGround()
        updateStats()
        updateStatus()
      } catch {
        if (disposed() || select.value !== requested) return
        select.value = 'none'
        if (slot === 'boots') bootsEquipped = false
        if (slot === 'helmet') {
          helmetEquipped = false
          updateHair()
          if (
            (document.getElementById('female-camera') as HTMLSelectElement)
              .value === 'face'
          )
            reset()
        }
        if (slot === 'gloves') {
          glovesEquipped = false
          if (sleeveMaskRegistered)
            outfitMask.setEquipped('glove-sleeves', false)
        }
        show('none')
        updateGround()
        updateStats()
        status.textContent = '갑옷을 불러오지 못했습니다. 다시 선택해 주세요.'
      }
    }
    select.onchange = update
    return update
  })
  const updateStats = () => {
    let triangles = 0
    model.traverseVisible((node) => {
      if (node instanceof THREE.Mesh)
        triangles +=
          (node.geometry.index?.count ??
            node.geometry.attributes.position.count) / 3
    })
    document.getElementById('female-stats')!.textContent =
      `${triangles.toLocaleString()}삼각형 · ${bones.length}개 본 · ${animations.length}가지 동작`
  }
  let appliedHair = hairSelect.value
  hairSelect.onchange = async () => {
    const requested = hairSelect.value
    try {
      const meshes = await loadHair(requested)
      if (disposed()) return
      for (const mesh of meshes) collectMaterials(mesh)
      for (const material of materials) material.wireframe = wireframe.checked
      if (hairSelect.value !== requested) return
      appliedHair = requested
      updateHair()
      updateStats()
      updateStatus()
    } catch {
      if (disposed() || hairSelect.value !== requested) return
      hairSelect.value = appliedHair
      status.textContent = '헤어를 불러오지 못했습니다. 다시 선택해 주세요.'
    }
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
    upper: { target: [0, 0.76, 0], position: [0, 0.78, 0.8] },
    lower: { target: [0, 0.52, 0], position: [0, 0.55, 0.8] },
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
    if (select.value === 'face' && helmetEquipped) {
      controls.target.set(0, 0.971, 0)
      camera.position.set(0, 0.981, 0.48)
    }
    if (select.value === 'full' && torch.visible) {
      controls.target.y = 0.6
      camera.position.set(0, 0.65, 2.3)
    }
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
  const requestedEquipment = params.get('equipment') ?? ''
  equipment.value = [
    'unarmed',
    'armed',
    'torch',
    'armed-torch',
    'shield',
    'armed-shield',
  ].includes(requestedEquipment)
    ? requestedEquipment
    : requestedMotion === 'idle_armed'
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
    updateGround()
    renderer.render(scene, camera)
  })
  const fieldset = document.getElementById(
    'female-controls'
  ) as HTMLFieldSetElement
  fieldset.disabled = false
  await Promise.all(outfitUpdates.map((update) => update()))
  if (disposed()) return
  document.body.dataset.ready = 'true'
}
