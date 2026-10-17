# 여성 기사 게임 적용 — 2026-10-14

캐릭터 생성에서 여성 기사를 선택하면 새 모듈형 여성 베이스와 기사 투구·상의·하의·장갑·부츠를 표시한다.
서버는 기존 `worn_plate_helmet`, `worn_breastplate`, `worn_plate_greaves`,
`worn_plate_gauntlets`, `worn_plate_boots`를 각 슬롯에 지급·장착한다.
기존 남성 기사와 같은 성능·거래 불가 기본 아이템이며 여성용 외형을 선택한다.
기존 여성 기사에게는 배포 중 서버와 NPC를 멈춘 뒤 `tools/grant-female-knight-starter-armor-20261014.py`로 1회 지급한다.
미리보기 후 `--apply --expected-preview`로 실행하며, 인벤토리에 없는 품목만 가방에 추가하고 기존 장착·강화는 보존한다. NPC 및 다른 여성 직업의 모델은 유지한다.

## 제작과 재현

`node tools/prepare-female-knight.mjs`로 `client/public/models/characters/modular_female/`을 만든다.
[입출력 해시](female-knight-runtime-sources.json)는 원본과 게임용 GLB를 연결한다.
보정 동작 `preview/animations.json`은 로컬에서 생성하므로 해시 대신 생성 입력을 기록한다.
기존 형상·UV·65본·유효 스킨 가중치와 가림 인덱스를 유지하고 텍스처를 WebP로 변환한다.
가중치가 0인 스킨 슬롯의 사용되지 않는 본 인덱스는 0으로 정리한다.
컬러는 최대 2048·WebP q94, 기타 텍스처는 최대 1024·WebP q90이며 속눈썹 텍스처는 보존한다.
원본 피팅 파일에 남은 참조 없는 accessor는 제거한다(2026-10-15, 7개 GLB 26.5 → 13.7MB).
원본이 미터 단위라서 좌표 변환 없이 그대로 쓴다(아래 [원본 미터 단위 전환](#원본-미터-단위-전환--2026-10-17)).
남성 모듈러와 같이 게임 루트 배율은 `(1, 1, 1)`이며 기존 표시 키를 유지한다. 손 소품에는 역배율을 적용하지 않는다.
기존 승인 동작을 우선 사용하고 나머지 게임 애니메이션은 같은 여성 리그에 미리 리타기팅한다.
리타기팅·접지 대상은 게임용 `base.glb`다. 2026-10-17 이전에는 제작 단위 리그에 미터 동작을 리타기팅한 뒤 1.8배를 다시 적용해, 리타기팅 동작의 Hips 이동이 1.8배였다(침대에 누운 몸이 0.93m 밀려나고, 승마 시 Hips가 0.9m 낮았다).
부츠 발 자세·접지 보정과 검 쥔 손가락 자세는 이 도구가 완성된 게임용 GLB를 다시 읽어 굽는다.
부츠 값은 `<클립>|femaleBoots` 보조 애니메이션(발 4본 회전, Hips 이동)에 넣고, 클라이언트는 이를 맨발 트랙과 짝지어 캐릭터마다 부츠 착용 여부로 하나를 고른다.
검 쥔 손가락 자세는 남성 모듈러처럼 무기와 관계없이 대기·걷기·달리기·전투 대기 클립에 넣는다.
앉기 보정과 피부·소매 가림은 개발 미리보기와 게임이 같은 함수를 사용한다.

이 작업은 기존 에셋의 로컬 변환이며 추가 유료 생성이나 새 원화를 사용하지 않았다.
원본 라이선스·구독 등급은 [여성 베이스](modular-human-female-01.md),
[헬멧](modular-female-knight-helmet.md), [상의](modular-female-knight-top.md),
[하의](modular-female-knight-bottom.md), [장갑](modular-female-knight-gloves.md),
[부츠](modular-female-knight-boots.md)의 출처 기록을 따른다.
헬멧·장갑 원화의 ImageGen 등급은 ChatGPT Pro 20x이며 Tripo 유료 API 결과를 재사용한다.

## 장비 교체와 검증

투구를 해제하면 단발 헤어를 복원하고, 장갑을 해제하면 소매를 복원한다.
피부 가림은 캐릭터별 복사본에 적용하여 다른 플레이어나 캐릭터 선택 슬롯에 영향을 주지 않는다.
갑옷을 전부 해제하면 원래 베이스로 돌아온다. 장비별 대체 외형은 아래 야만용사 복장 규칙을 따른다.
외형 커스터마이즈 UI는 기존 지원 범위를 유지한다.

기사 세트의 숨김 포함 삼각형은 66,017, 실제 표시 51,538이며 얼굴 4,604면을 유지한다.
숨긴 단발 헤어와 검·횃불·망토는 이 합계에 포함하지 않는다. 원본 예산 초과 상태에서 임의 감축하지 않았다.

- 서버 테스트: 여성 기사 기본 장비 5종의 수량·장착 슬롯·캐릭터 목록 장비 반환, 기존 남성 기사 지급.
- 런타임 테스트: 착탈과 가림 복원, 캐릭터 간 격리, 동작별 유한 변형·투구 강체 유지·부츠 보정.
- 배율 적용 전후 51개 동작의 256개 자세에서 메시 표본·전체 본 위치를 비교했다. 최대 월드 좌표 오차는 약 `1.8e-7 m`이며 키와 접지를 유지한다. 루트·손 본 배율 1과 손 소품 크기도 검사한다.
- 브라우저: 실제 CharacterCreateScene과 CharacterPreview의 여성 기사 표시, 성별 전환, 착탈 복원. 실제 PlayerModel에서 기본 검과 장비 착용 표시도 확인했다.
- 프런트엔드 타입·린트, Rust 형식·컴파일 검사.

게임용 GLB 16개 검사는 오류 0개다. 기존 몸체·부츠의 탄젠트 자동 생성 경고 3개는 유지하며 실제 WebGPU 표시를 확인했다.

## 여성 야만용사 적용 — 2026-10-16

여성 야만용사도 같은 모듈형 여성 베이스를 쓴다. 서버는 남성과 같은 `worn_barbarian_*` 5종을 지급·장착하고,
캐릭터 생성 화면은 뿔 투구까지 입힌 모습을 보여준다.
`prepare-female-knight.mjs`가 `barbarian_{top,bottom,boots,gloves,helmet,hair}.glb`를 함께 만든다.
`barbarian_hair`는 뿔 투구 아래에 맞춘 단발이며 투구를 쓰면 기본 단발 대신 표시된다.
부위마다 판금·야만용사 외형을 따로 고르므로 섞어 입을 수 있다. 야만용사 전용 장비와 가죽 소재 장비는 야만용사 외형으로 표시한다. 일반 가죽 방어구, 로그·순찰자·원시인 복장, 사제·음유시인의 가죽 부츠가 여기에 해당한다. 나머지 금속·천 장비는 판금 외형으로 대체한다. 남성의 장비 외형 선택에는 영향을 주지 않는다.

샌들과 기사 부츠는 발 회전은 같지만 밑창이 달라 접지 높이가 달리기에서 최대 약 4.8cm 차이 난다.
그래서 보정 동작을 부츠 부위별 `<클립>|femaleBoots:<부위>`로 굽고, 클라이언트는 [맨발, 기사 부츠, 샌들] 값 중 하나를 고른다.

모피 치마 4장의 `pelt_physics`는 미터 값과 `unit: 1.8`을 원본에 담는다.
`pelt-rig`의 내장 거리·중력은 튜닝 당시 1/1.8 크기 리그 기준이라 `unit`만큼 키운다. 게임은 `robe_physics`를 쓴다.
모피 파츠는 정점 위치를 직접 고쳐 쓰므로 인터리브하지 않고 저장한다.

원본 출처·라이선스는 [상의](modular-female-barbarian-top.md), [하의](modular-female-barbarian-bottom.md),
[샌들](modular-female-barbarian-boots.md), [손목 보호대](modular-female-barbarian-bracers.md),
[투구·헤어](modular-female-barbarian-helmet.md) 기록을 따른다. 추가 유료 생성은 없다.

기존 여성 야만용사에게는 배포 중 서버와 NPC를 멈춘 뒤 `tools/grant-female-barbarian-starter-armor-20261016.py`로 1회 지급한다.
사용법은 기사 지급 스크립트와 같다(미리보기 후 `--apply --expected-preview`, 가방에 없는 품목만 추가).

## 원본 미터 단위 전환 — 2026-10-17

여성 모듈러 원본을 리그 높이 1(Hips 높이 0.568)의 제작 단위에서 미터로 바꿨다.
남성 모듈러처럼 원본이 게임 단위를 쓰므로 `prepare-female-knight.mjs`의 1.8배 변환(`bakeDimensions`),
읽을 때의 동작 변환과 `meters_per_source_unit` 메타데이터를 없앴다. 현재 `rig_v1/female-base.glb`를 새 기준으로 고정했고,
리깅 이전 단계와 `tools/rig-female-base.py`는 보관용이다.

변환은 `tools/convert-female-sources-to-meters.py`(1회용, 변환 전 해시를 확인해 두 번 적용하지 않음)가 했다.
`bakeDimensions`와 같은 값(노드 이동, POSITION·모프 대상, 역바인드 이동, 애니메이션 이동, `pelt_physics` 기준점·길이·부착 깊이·충돌체)과
부츠 `heel_pose` 좌표를 1.8배하고 accessor·bufferView 배치는 바이트 단위로 유지했다.

- GLB 18개: 리그 `rig_v1/female-base.glb`, 헤어 `hair_female_knight_bob.glb`·`hair_female_knight.glb`와 두 헤어의 `hair-fitted-unskinned.glb`(리깅 입력),
  기사 상의 v3·하의 v42·장갑 v3·투구 v1·부츠 v5와 부츠 v4(`shape-female-knight-boots.py` 입력),
  야만용사 상의 v1·하의 v1·샌들 v3·손목 보호대 v1·투구 v1·투구용 헤어 2개.
- 보조 데이터(리그 좌표만, Tripo 원본 좌표 `source`는 유지): 부츠 v4·v5 `heel-pose.json`과 `fitting.json`의
  `posed_floor_offset`·`heel_pose`·높이 구간(v4는 `section_clearances[].height`도), 두 부츠의 `heel-animation-offsets.json`
  (`lift`·`hips`), `underwear_fit_v1/fitting.json`(`patch_centers`·반경)과 `source-influences.npz`(`positions`),
  `hair-cheek-coverage-anchors.json`(카메라·표적·깊이 허용치, 몸체 해시 갱신), `fit-data.npz`
  (장갑 v3 `*_positions`, 야만용사 상의 `source`·`fitted`·`depth`, 하의 `fitted`·`depth`, 샌들 `start`·`fitted`·`left_fitted`·`depth`),
  상의 v3 `sleeve-adjustment.npz`(`previous`·`source`·`points`).
- 가림 JSON은 삼각형 인덱스라 그대로 둔다. 기사 부츠 `body-occlusion.json`의 `cuff_heights`는 쓰지 않는 기록값으로 제작 단위에 남는다.

게임용 GLB 23개를 다시 만들어 전환 전 HF 파일과 수치로 비교했다. 메시 정점·노멀·UV·스킨·역바인드·노드·애니메이션 트랙은
비트 단위로 같고, `animations/offhand.glb`의 횃불 동작 Hips 이동만 최대 1.19e-7m 다르다(미터 리그에서 다시 계산한 보정 동작의 부동소수 오차).
메타데이터는 `meters_per_source_unit`이 빠지고 부츠 `heel_pose`의 좌표 기록값(런타임 미사용)이 미터가 됐다.
보정 동작 `preview/animations.json`은 회전 트랙이 같고 이동 트랙 차이는 1.19e-7m 이하다.

도구도 미터 기준으로 바꿨다. 상수를 1.8배하고 `METERS_PER_UNIT`·`CHARACTER_HEIGHT_M` 환산을 없앴다.

- 피팅: `fit-female-barbarian-{bracers,helmet,boots}.py`, `fit-female-knight-{boots,gloves,helmet}.py`,
  `shape-female-knight-boots.py`, `trim-female-barbarian-helmet-hair.py`,
  `outfits/{fit_female_knight_top_surface,repair_sandal_panel,female_boot_material,female_barbarian_top_occlusion}.py`.
  몸체 해시 확인은 전환 후 리그로 갱신했다.
  전환된 입력으로 다시 실행해 전환된 원본과 비교했다. 손목 보호대·두 투구·장갑·기사 부츠(v4→v5)는 위치 오차 1.2e-7m 이하,
  손목 보호대·야만용사 상의·기사 장갑의 가림 인덱스는 같다.
  샌들은 반복 피부 밀어내기가 입력의 float32 반올림에 민감해 최대 0.94mm, 투구용 헤어 트림은 잘림 경계 삼각형 몇 개가 다르다.
  같은 반올림만 준 입력을 전환 전 도구에 넣어도 같은 수준으로 달라진다.
  `fix-female-underwear-clipping.py`는 상수만 미터로 바꿨다. 입력 해시가 속옷 수정 전 리그라 다시 실행하지 않는다.
- Blender: 피팅 `fit_female_knight_{bob,hair}.py`·`fit_female_barbarian_top.py`와 이어지는 `rig-female-knight-{bob,hair,top-v2}.py`
  (`rig-female-knight-{bob,top-v2}.py`는 단위와 무관), 검수 `review_female_{barbarian_boots,barbarian_bottom,barbarian_bracers,barbarian_helmet,barbarian_top,knight_bob,knight_boots,knight_gloves,knight_hair,knight_helmet}.py`.
  전환 전 피팅 체인은 현재 원본을 그대로 재현했고, 미터 버전은 단발 2.4e-7m 이내로 같다. 긴 헤어는 정수리 9정점이 최대 4.3mm,
  야만용사 상의는 최대 7.7mm 다르다. 긴 헤어는 가장 가까운 몸체 삼각형이 가늘어 면 노멀이 float32 반올림에 따라 바뀌고,
  상의는 반올림만 준 리그를 전환 전 도구에 넣어도 같은 7.7mm 차이가 난다. 검수 스크립트는 카메라·조명 위치를 1.8배,
  조명 세기를 3.24배 했다. 10개 스크립트의 렌더 113장이 전환 전과 겹치고(Workbench), Cycles 렌더 밝기도 같다.
  단발·긴 헤어 검수는 `female-base.blend` 대신 리그 GLB를 연다.
- 동작: `lib/female-seated.mjs`(앉기 재계산이 저장된 `sit_idle`과 위치 6e-8m·회전 1.2e-7 이내로 일치), `animate-female-base.mjs` 손 오프셋.
- 검사: `validate-female-{seated,knight-boots,knight-bob,knight-hair,knight-helmet,knight-top-v2,preview}.mjs`,
  `validate-female-barbarian-{boots,bottom,bracers,helmet,helmet-hair,helmet-hair-coverage,top}.mjs`,
  `validate-female-barbarian-{boots-clearance,connector-clearance,ring-walls,panel-overlap,helmet-hair}.py`,
  `export-female-barbarian-boots-poses.mjs`. 전환 전 트리에서 같은 30개 명령을 실행해 비교했다. 통과·실패가 모두 같고
  (전체 샌들 끈 검사 2개와 왼발 뒤꿈치 끈 검사는 기록된 앞끈·뒤꿈치 끈 관통으로 전환 전부터 실패), 거리 값은 1.8배다.
  허용치 경계의 관통 표본 수가 시점별로 ±2개, 기사 부츠 밑창 폭 표본이 489 → 488쌍 달라진 것 외에 개수는 같다.
  전투 대기 뒤꿈치 끈의 피부 거리 최솟값 일부는 가장자리 표본 선택이 바뀌어 최대 0.044mm 다르다. 착용 자세 정점 차이는 1.7e-7m 이하다.
- 클라이언트: `female-boot-ground.ts` 표본 높이 0.144·0.324m, `female-seat.ts`는 카탈로그 상호작용 높이를 그대로 쓴다.
  개발 미리보기 `female-base.ts`는 손 소품에 `FEMALE_HAND_FITS`를 쓰고 카메라·바닥 값을 1.8배했다.
  전환 전후 미리보기를 같은 시점으로 렌더링해 겹쳐 보면 화면 크기가 같다.

보관용(전환 전 트리 `assets.lock` @ `1e291c68`에서만 재현): `rig-female-base.py`, `tune-female-{seated,catwalk}.mjs`,
`validate-female-rig.mjs`, 기사 하의 v1–v42 체인 단계 도구와 검사(`validate-female-knight-{bottom,front-clips,strap-surface,upper-straightness,strap-bend,rear-straps,rear-leather}.mjs`,
`validate-female-knight-*.py`), 야만용사 하의 수리 단계(`{fix,join,smooth}-female-barbarian-belt.py`,
`{stitch,weight}-female-barbarian-panels.py`, `fit-female-barbarian-{waistband,thigh-contact}.py`, `outfits/female_barbarian_bottom_occlusion.py`),
기사 상의 v2→v3 단계(`outfits/{export_female_knight_sleeves,assemble_female_knight_top,female_knight_top_occlusion}.py`),
`validate-female-underwear.py`, `rig-female-knight-rear-straps.py`, `tools/blender-scripts`의 기사 하의·기사 상의 v2→v3·야만용사 하의·리깅 이전 단계 스크립트와
`sync_female_underwear_weights.py`(머리 주석에 표시). 이 단계들은 이전 버전 파일과 비교하거나 고정 해시를 확인한다.

전환하지 않은 파일: 모든 `.blend` 편집본(Blender에서 열면 제작 단위), `catwalk-source.glb`(Mixamo 자체 단위, Hips 높이 비율로 리타기팅),
리깅 이전 GLB(`ear_normals_v2`, `eye_normals_v1` 등), 위에 적지 않은 이전 `fitted_vN`, `doc/assets`의 날짜별 피팅 기록.
검수 스크립트를 다시 실행하면 `*-fitted.blend`를 미터로 다시 저장한다.
