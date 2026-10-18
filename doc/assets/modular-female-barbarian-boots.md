# 여성 바바리안 가죽 하이힐 샌들

[여성 바바리안 원화](../../client/public/character_concepts/female_barbarian.webp)의 신발을 Tripo로 만들어
여성 공통 몸체(`human_female_01_local_v1`, 65본)에 피팅한 신발 슬롯 파츠다. 앞이 트인 갈색 가죽 샌들,
세 줄 발목 고리, 리벳·버클, 넓은 앞끈, 스틸레토 굽으로 구성한다.
게임에서는 `barbarian_boots.glb`로 표시된다(적용 범위는 [여성 기사 게임 적용](female-knight-runtime.md#여성-야만용사-적용--2026-10-16)).
채택본은 `tripo_v1/fitted_v3`이며 원본 좌표는 미터 단위다.

![앞·옆·뒤 원화](../../assets/items/female_barbarian_boots/concept_v1/sheet.png)

## 최종 파일

| 용도 | 파일 |
| --- | --- |
| 신발 GLB | [boots_female_barbarian.glb](../../assets/items/female_barbarian_boots/tripo_v1/fitted_v3/boots_female_barbarian.glb) |
| 편집용 Blender | [female-barbarian-boots-fitted.blend](../../assets/items/female_barbarian_boots/tripo_v1/fitted_v3/female-barbarian-boots-fitted.blend) |
| 피부 가림 | [body-occlusion.json](../../assets/items/female_barbarian_boots/tripo_v1/fitted_v3/body-occlusion.json) |
| 검사용 형상·웨이트 | [fit-data.npz](../../assets/items/female_barbarian_boots/tripo_v1/fitted_v3/fit-data.npz) |
| 동작별 굽 보정 | [heel-animation-offsets.json](../../assets/items/female_barbarian_boots/tripo_v1/fitted_v3/heel-animation-offsets.json) |
| 리그·동작 검사 | [runtime-validation.json](../../assets/items/female_barbarian_boots/tripo_v1/fitted_v3/runtime-validation.json) |
| 피팅·리깅 기록 | [modular-female-barbarian-boots-fitting-v3.json](modular-female-barbarian-boots-fitting-v3.json) |
| 게임용 | `client/public/models/characters/modular_female/barbarian_boots.glb` |

- 양발 **3,624 triangles**. 오른쪽 한 짝을 생성해 대칭한 뒤 왼발 피부에 따로 피팅했다.
- 기사 부츠와 같은 굽 자세(`tools/outfits/female_boot_pose.py`, Foot +30°, ToeBase −30°)에서 피팅하고,
  신발을 Foot→ToeBase 방향에서 바깥으로 7° 더 돌렸다(오른쪽 −17.954°, 왼쪽 +17.954°).
- Tripo에 없던 뒤 세로 연결끈을 직접 추가했다(한 짝 148 triangles, 기존 굽 가죽 UV 영역 재사용).
- 발가락 본은 원래 애니메이션에 공통 굽 오프셋만 적용한다. 앞끈의 ToeBase 영향은 최대 0.35, 오른쪽 앞끝은 발가락 동작을 0.45 비율로 따른다.
- 발바닥 아래 피부 91면을 가리고, 장비를 벗거나 로딩에 실패하면 복원한다.

## 재현

저장소 루트에서 실행한다. Python은 `.venv`의 NumPy, SciPy, trimesh 5.1.1, rtree 1.4.1, Shapely 2.1.2를 쓴다.

```bash
.venv/bin/python tools/fit-female-barbarian-boots.py
node tools/validate-female-barbarian-boots.mjs
node tools/export-female-barbarian-boots-poses.mjs
node tools/export-female-barbarian-boots-poses.mjs assets/items/female_barbarian_boots/tripo_v1/fitted_v3 left
.venv/bin/python tools/validate-female-barbarian-boots-clearance.py --stride 5
.venv/bin/python tools/validate-female-barbarian-connector-clearance.py
.venv/bin/python tools/validate-female-barbarian-ring-walls.py --ring middle
.venv/bin/python tools/validate-female-barbarian-panel-overlap.py
blender -b --python-exit-code 1 --python tools/blender-scripts/review_female_barbarian_boots.py
```

- 검사 도구는 `--side left`로 왼발을 검사한다. `ring-walls`는 `--ring middle|lower|front|front-side`(`front-side`는 `--panel 0|1`),
  `boots-clearance`는 `--regions ankle front connector heel`, `--motions`로 범위를 고른다.
- 피팅을 다시 실행하면 `fitting-v3.json`과 GLB가 새 후보로 바뀌므로 리그·끈 검사를 다시 돌린다.
  미터 입력으로 재실행하면 반복 피부 밀어내기가 float32 반올림에 민감해 위치가 최대 0.94mm 달라진다.
- 끈 검사는 앞끈 관통을 검출하면 실패 종료한다. 포즈 추출·렌더 임시 파일은 재현 후 정리한다.
- 미리보기: `/modular-character-preview.html?character=female&camera=feet&boots=barbarian&motion=idle1`.

## 출처·라이선스

- 원화: OpenAI Codex built-in ImageGen(`codex exec`, codex-cli 0.162.1), **ChatGPT Pro 20x**, 2026-10-15.
  OpenAI 출력물 이용 조건을 따른다. 참조 원화의 출처는 [캐릭터 문서](characters.md)에 있다.
  - [앞·옆·뒤 원화](../../assets/items/female_barbarian_boots/concept_v1/sheet.png),
    [프롬프트](../../assets/items/female_barbarian_boots/concept_v1/prompt.txt),
    [참조·분리 영역·해시](../../assets/items/female_barbarian_boots/concept_v1/sources.json).
  - 참조 입력: 원화 잘라낸 [reference-crop.png](../../assets/items/female_barbarian_boots/concept_v1/reference-crop.png),
    [여성 기사 판금 부츠](modular-female-knight-boots.md) 렌더에서 자른 굽 참조
    [heel-reference.png](../../assets/items/female_barbarian_boots/concept_v1/heel-reference.png)(프로젝트 자체 렌더).
- 3D: Tripo API 유료 크레딧, 2026-10-15. 모델 `P2-20260801`, 텍스처 `v3.5-20260815`, detailed PBR,
  입력 조명 제거, 한 짝 목표 1,500 triangles, seed 101502.
  [API 문서](https://developers.tripo3d.ai/en/docs/generation-multiview-to-model/p),
  [이용 조건](https://developers.tripo3d.ai/en/terms).
  - 작업 ID `a4ac552f-032f-4822-9978-fad40d1ff10e`, **120크레딧 사용**. 추가 유료 생성은 없다.
  - 입력: 같은 배율의 800×800 흰 정사각형
    [앞](../../assets/items/female_barbarian_boots/tripo_v1/inputs/front.png)·
    [옆](../../assets/items/female_barbarian_boots/tripo_v1/inputs/side.png)·
    [뒤](../../assets/items/female_barbarian_boots/tripo_v1/inputs/back.png).
  - [제작 명세](../../assets/items/female_barbarian_boots/tripo_v1/build.json),
    [요청·비용·작업 기록](../../assets/items/female_barbarian_boots/tripo_v1/generation.json).
  - 원본: [model_url.glb](../../assets/items/female_barbarian_boots/tripo_v1/source/model_url.glb)
    (메시 1개, 1,664 triangles, 4K 컬러·노멀·ORM),
    [rendered_image_url.png](../../assets/items/female_barbarian_boots/tripo_v1/source/rendered_image_url.png),
    [source.blend](../../assets/items/female_barbarian_boots/tripo_v1/source.blend),
    [원본 진단](../../assets/items/female_barbarian_boots/tripo_v1/review.json)
    ([재현 스크립트](../../assets/items/female_barbarian_boots/tripo_v1/review_source.py)).
- 직접 추가한 연결끈은 기존 Tripo 텍스처를 쓰므로 원본과 같은 출처·라이선스를 따른다.

## 제한

- 일부 동작에서 앞끈이 피부를 관통한다(오른발 공격·달리기, 왼발 걷기·횃불 달리기).
- 왼발 뒤꿈치 옆 끈은 855시점 중 73시점에서 관통이 남는다.
- Tripo 텍스처의 넓은 금속색 얼룩이 남아 있다.
