# 여성 바바리안 상의 — 2026-10-14

[여성 바바리안 원화](../../client/public/character_concepts/female_barbarian.webp)의 상의를
모듈형 파츠용 앞뒤 원화로 옮기고 Tripo로 3D 원본을 생성해 여성 기준 몸체에 피팅했다.
여성 미리보기에 연결했으며 장비 등록은 아직 하지 않았다.

![여성 바바리안 상의 원화](../../assets/items/female_barbarian_top/concept_v1/sheet.png)

## 출처

- 원화: OpenAI Codex built-in ImageGen(`codex exec`, codex-cli 0.162.1), **ChatGPT Pro 20x**, 2026-10-14.
  OpenAI 출력물 이용 조건을 따른다. 참조 원화의 출처는 [캐릭터 문서](characters.md)에 있다.
- 참조 입력은 원본을 흰 바탕에 합성해 `[260,250,520,400]`을 FFmpeg로 자른
  [reference-crop.png](../../assets/items/female_barbarian_top/concept_v1/reference-crop.png)이다.
- [앞뒤 원화](../../assets/items/female_barbarian_top/concept_v1/sheet.png),
  [앞면](../../assets/items/female_barbarian_top/concept_v1/front.png) `[0,128,768,690]`,
  [뒷면](../../assets/items/female_barbarian_top/concept_v1/back.png) `[768,128,768,690]`,
  [프롬프트](../../assets/items/female_barbarian_top/concept_v1/prompt.txt),
  [출처·해시](../../assets/items/female_barbarian_top/concept_v1/sources.json).

## 범위

- 상의: 리벳 철판 컵, 가운데 파란 보석과 청동 고리, 컵 아래 철띠, 등의 X자 가죽끈·버클,
  착용자 오른쪽 어깨에만 가시 견갑.
- 제외: 초커(떨어진 고리라 단일 메시 파츠에 부적합), 손목 보호대(장갑 슬롯), 벨트·모피 하의.

## Tripo 생성

- Tripo API 유료 크레딧, 모델 `P2-20260801`, 텍스처 `v3.5-20260815`, detailed PBR,
  입력 조명 제거, 삼각형 목표 3,000, seed 101401. [API 문서](https://developers.tripo3d.ai/en/docs/generation-multiview-to-model/p),
  [이용 조건](https://developers.tripo3d.ai/en/terms).
- 입력은 원화의 앞·뒤 영역을 그대로 자른 두 장이다.
- 작업 ID `1733c4c6-0730-4606-b020-a94c31b01984`, **120크레딧 사용**, 잔액 920 → 800.
- [제작 명세](../../assets/items/female_barbarian_top/tripo_v1/build.json),
  [요청·비용·작업 기록](../../assets/items/female_barbarian_top/tripo_v1/generation.json).
  재제출하지 않고 `tools/outfits/tripo.py`로 기존 작업을 조회·회수한다.

![Tripo 원본 앞·뒤·옆·사선](../../assets/items/female_barbarian_top/tripo_v1/review/strip.png)

| 용도 | 파일 |
| --- | --- |
| Tripo 원본 | [model_url.glb](../../assets/items/female_barbarian_top/tripo_v1/source/model_url.glb) |
| 원본 Blender | [source.blend](../../assets/items/female_barbarian_top/tripo_v1/source.blend) |
| 원본 진단 | [review.json](../../assets/items/female_barbarian_top/tripo_v1/review.json), [재현 스크립트](../../assets/items/female_barbarian_top/tripo_v1/review_source.py) |

원본은 메시 1개, **2,983 triangles**, 4K 컬러·노멀·ORM 텍스처다.
UV 이음만 임시 용접한 진단에서 연결 성분 1개, 경계선 241개, 퇴화 면·UV 붕괴 0개였다.
컵은 두께 없는 한 겹 면이라 뒤에서 보면 앞면 텍스처(보석의 파란색 포함)가 그대로 보인다.
착용하면 몸에 가려지지만, 피팅 때 안쪽 면 처리를 확인한다.

## 피팅 v1 — 2026-10-14

![착용 앞·옆·뒤·사선](../../assets/items/female_barbarian_top/tripo_v1/fitted_v1/review/strip.png)

기준 몸체 `assets/modular_human_female_01/rig_v1/female-base.glb`, 리그 `human_female_01_local_v1` 65본.
몸체·동작은 변경하지 않았다. 삼각형 2,983개, UV·텍스처는 Tripo 원본 그대로다.

- 정렬: 배율 0.21, Z −90°, 이동 `(-0.028, 0.003, 0.779)`(Blender 좌표). 앞쪽 컵 영역을 폭 1.18배, 깊이 1.27배로 키웠다.
- 몸 표면 맞춤: 몸에 닿는 안쪽 정점을 피부 표면 + 간격 + 원래 층 두께 위치로 고정하고 ARAP로 나머지를 따라오게 했다.
  간격은 컵·밴드 6mm, 컵 위 끈 2mm다. 가슴골 가운데(폭 약 5cm)만 바깥으로 밀기만 해서 가로지르게 하고,
  컵 가장자리·끈·밴드는 피부로 당긴다. 마지막에 피부 1mm 안쪽으로 들어간 정점을 밖으로 민다.
- 견갑은 피부 밖 6mm, 가운데 보석판은 3mm까지 형상을 그대로 둔 강체로 옮겼다. 고리는 보석판에 걸린 윗점을 축으로
  뒤로 젖혀 밑띠 위에 얹었다. 휴지 자세 관통 0, 최소 간격 1mm.
- 웨이트: 컵은 아래 피부 웨이트를 매끈하게 다듬어 따른다(평균 `Spine1 0.73, Spine2 0.07, Spine 0.07, 양 Shoulder 0.05`).
  처음에는 컵을 척추 평균 하나로 고정한 강체로 했으나, 팔을 내린 대기 자세에서 가슴 바깥 피부가 어깨를 따라 움직여
  컵 윗가장자리와 끈이 떠 보였다. 가운데 보석·고리는 `Spine1 0.9 + Spine2 0.1` 강체,
  견갑은 `RightShoulder` 단독 강체다. 견갑을 두 본에 섞으면 베기에서 판이 34% 찌그러졌고,
  `RightArm` 단독은 관통이 더 많았다. 끈·밴드는 피부 웨이트를 옮겼다. 보석·견갑에서 2.5cm 안쪽만 16회 스무딩해
  연결부 늘어남을 막고, 그 밖은 피부 웨이트를 그대로 써 피부와 같이 움직인다. 반대쪽 어깨·팔 영향은 없다.
- 가림: 기본 상의·리본 2,488면, 컵 안쪽 피부 92면. 컵이 1.2cm 안으로 덮고 가장자리에서 2cm 이상 안쪽인 피부만 숨긴다.
  가슴골처럼 컵이 피부에서 떨어진 곳은 옆에서 비스듬히 보면 숨긴 자리가 빈틈으로 보여 남긴다(사용자 검수 2026-10-14).
  견갑·끈 아래 피부는 동작 중 판과 따로 움직여 구멍이 드러날 수 있으므로 숨기지 않는다.

### 미리보기

개발 서버의 `/modular-character-preview.html?character=female&camera=upper&top=barbarian`에서 연다.
`상의`에서 `야만전사 가죽 철갑`을 고르면 처음 선택할 때 불러오고 기사 갑옷과 바꿔 입힐 수 있다.
장갑 소매 가림은 기사 상의에만 적용한다. Headless Chrome(SwiftShader)에서 착용 화면과
기사 상의·장갑 조합이 그대로인 것을 확인했다.

### 검증

`bindModularPart`로 결합해 9동작 × 121시점을 검사했다. 본·inverse bind 일치, 웨이트 정규화,
반대쪽 팔 영향 없음, 견갑 변형 0, 보석 모서리 길이 변화 최대 0.8%(jump). 컵은 피부를 따라 변형되며 길이 변화를 기록만 한다.
관통(휴지 자세보다 2mm 이상 깊어진 정점, 가장 가까운 피부 정점 기준 근사)은 대기·걷기 0,
jump 44개·최대 1.5cm, slash1 96개·최대 3.2cm, dying 55개·최대 2.6cm. 모서리 최대 늘어남은 slash1 3.3배다.
동작 렌더에서 확인한 주원인은
팔이 가슴 앞을 지나는 동작과 팔을 든 자세에서 상완이 견갑 아래로 들어가는 것이다.

### 끈 밀착 보정 — 2026-10-14

사용자 검수에서 착용자 왼쪽 앞 어깨끈이 버클 근처에서 꺾여 보이고, 옆에서 보면 몸에서 떠 있었다.
처음 피팅은 가슴골을 가로지르게 하려는 "밀기만" 규칙이 컵 위 끈과 컵 가장자리까지 덮었고,
끈 웨이트를 40회 스무딩해 컵의 척추 웨이트가 끈까지 번졌고, 강체 컵은 팔을 내리면 가슴 바깥 피부와 어긋났다.
위 규칙과 웨이트로 고쳐 대기 자세에서 컵 위쪽·끈 정점과 피부 사이 간격이 상위 10% 1.17cm → 0.85cm,
최대 1.64cm → 1.27cm로 줄었다.
버클 고리가 끈 방향과 조금 비틀린 모양은 Tripo 원본 형상이다.
가슴이 커서 끈은 어깨에서 컵 윗가장자리까지 일부 공중을 지난다.

### 가운데 고리·밑띠 밀착 — 2026-10-15

사용자 검수에서 밑에서 올려다보면 가운데 고리와 그 양옆 밑띠가 명치에서 떠 보였다.
보석판 윗모서리가 가슴골 안쪽 피부에 6mm로 걸려 판 전체가 앞으로 밀려 있었고, 고리는 판 아래에 앞으로 매달려 있었다.

- 보석판 간격을 6mm → 3mm로 줄였다. 판 전체를 기울이면 윗모서리가 다시 걸려 효과가 없었다.
- 고리(보석판 마스크 중 구릿빛 정점)를 판에 걸린 윗점을 축으로 피부 3mm까지 뒤로 젖혔다.
- 가운데(|x| < 4.5cm) 밑띠 아래쪽 가장자리를 갈비뼈 쪽으로 붙였다. 위쪽은 가슴 밑면에 걸려 있어 띠가 접힌 곳을 따라 기운다.
- 밑띠(높이 0.70 아래)의 피부 간격을 6mm → 끈과 같은 2mm로 줄였다. 컵 아랫가장자리까지 줄이면 성긴 컵 면 사이로 피부가 비쳐
  0.70–0.715 구간에서 6mm로 되돌린다.

앞에서 수평으로 잰 피부까지 거리는 고리 평균 1.51 → 0.98cm(최대 2.74 → 2.33cm),
가운데 밑띠 평균 1.28 → 0.97cm다. 고리 아래끝은 명치에서 3mm로 닿아 고리는 더 붙일 수 없다.
바뀐 정점은 밑띠와 가운데 보석판·고리뿐이고 컵 윗부분·끈·견갑은 그대로다.
동작 관통 수는 jump만 37 → 38이고 나머지는 그대로다.
남은 틈은 보석판 폭이 가슴골보다 넓어 판이 가슴골을 가로지르기 때문이다. 판을 좁히거나 아래로 내리면 더 붙지만 디자인이 바뀐다.

![가운데 밀착 전후: 위 밑에서, 아래 옆에서 / 왼쪽 전, 오른쪽 후](../../assets/items/female_barbarian_top/tripo_v1/fitted_v1/review/center-before-after.png)

피팅 스크립트의 ARAP 강성 색은 원래부터 몸체 텍스처(첫 `Color_` 이미지)를 읽는다.
상의 텍스처로 바꾸면 검수된 컵 형상이 최대 4mm 움직여 그대로 두고, 고리 판별에만 상의 텍스처를 쓴다.

### 남은 문제

- 기본 몸체 피부에 구워져 있던 속옷 자국은 2026-10-14에 제거했다
  ([기본 몸체 문서](modular-human-female-01.md#피부-텍스처의-속옷-자국-제거--2026-10-14)). 위 렌더는 수정 후다.
- 뒤에서 보면 컵 안쪽 면이 옆구리에 밝게 보일 수 있다.
- 컵 확대로 리벳이 약간 늘어났다. 컵이 피부를 따르므로 팔을 크게 움직이면 겨드랑이 쪽 가장자리가 접힌다.

| 용도 | 파일 |
| --- | --- |
| 상의 | [top_female_barbarian.glb](../../assets/items/female_barbarian_top/tripo_v1/fitted_v1/top_female_barbarian.glb) |
| 가림 명세 | [body-occlusion.json](../../assets/items/female_barbarian_top/tripo_v1/fitted_v1/body-occlusion.json) |
| 피팅 기록 | [modular-female-barbarian-top-fitting-v1.json](modular-female-barbarian-top-fitting-v1.json) |
| 동작 검사 | [modular-female-barbarian-top-animation-v1.json](modular-female-barbarian-top-animation-v1.json) |

### 재현

```bash
blender -b --python-exit-code 1 -P tools/blender-scripts/fit_female_barbarian_top.py
.venv/bin/python tools/rig-female-knight-top-v2.py assets/items/female_barbarian_top/tripo_v1/fitted_v1 top_female_barbarian doc/assets/modular-female-barbarian-top-fitting-v1.json 1
.venv/bin/python tools/outfits/female_barbarian_top_occlusion.py
node tools/validate-female-barbarian-top.mjs
blender -b --python-exit-code 1 -P tools/blender-scripts/review_female_barbarian_top.py
```
