# 여성 바바리안 손목대 — 2026-10-15

[여성 바바리안 원화](../../client/public/character_concepts/female_barbarian.webp)의 손목대를
착용자 오른쪽 한 짝의 3면 원화로 옮기고 Tripo로 생성해 여성 공통 몸체의 양 팔뚝에 피팅했다.
여성 미리보기의 장갑 칸에 연결했다. 장비 등록은 하지 않았다.
은빛 기사 갑옷과 함께 착용하면 기사 소매를 유지한다. 소매 가림은 은빛 기사 판금 장갑을 선택할 때만 적용한다.

![등쪽·옆·손바닥쪽 원화](../../assets/items/female_barbarian_bracers/concept_v1/sheet.png)

## 출처

- 디자인: [여성 바바리안 원화](../../client/public/character_concepts/female_barbarian.webp).
- 원화: OpenAI Codex built-in ImageGen(`codex exec`, codex-cli 0.162.1), **ChatGPT Pro 20x**, 2026-10-15.
  OpenAI 출력물 이용 조건을 따른다. 참조 원화의 출처는 [캐릭터 문서](characters.md)에 있다.
- [프롬프트](../../assets/items/female_barbarian_bracers/concept_v1/prompt.txt),
  [참조·분리 영역·해시 기록](../../assets/items/female_barbarian_bracers/concept_v1/sources.json).
  참조는 원화의 오른쪽(주)·왼쪽(보조) 손목을 흰 배경에 잘라 4배 확대했다.

## 원화 v1

위에서부터 등쪽·옆·손바닥쪽이며 모두 손목 입구가 왼쪽이다. 손목에서 팔꿈치로 넓어지는 갈색 가죽 통,
양 끝의 리벳 가죽 띠, 등쪽을 덮는 철판(가운데 능선, 말린 테두리, 원형·마름모 징, 양 끝 고정쇠)으로 구성한다.
손바닥쪽은 버클 달린 가죽끈 두 줄로 여민다. 원래 원화에서 보이지 않는 부분이라 새로 정했다.

이미지 생성 결과라 투시가 약간 남아 있고, 팔꿈치 쪽이 원화보다 더 벌어진다.
3D 피팅 때 팔 단면에 맞춰 줄인다.

| 보기 | 파일 |
| --- | --- |
| 등쪽 | [dorsal.png](../../assets/items/female_barbarian_bracers/concept_v1/dorsal.png) |
| 옆 | [side.png](../../assets/items/female_barbarian_bracers/concept_v1/side.png) |
| 손바닥쪽 | [volar.png](../../assets/items/female_barbarian_bracers/concept_v1/volar.png) |

각 보기는 시트의 자기 행만 남겨 같은 배율로 1100×1100 흰 정사각형 가운데에 놓았다.

## Tripo 원본

- Tripo API 유료 크레딧, 모델 `P2-20260801`, 텍스처 `v3.5-20260815`, detailed PBR,
  입력 조명 제거, 한 짝 목표 1,500 triangles, seed 101503.
  [API 문서](https://developers.tripo3d.ai/en/docs/generation-multiview-to-model/p),
  [이용 조건](https://developers.tripo3d.ai/en/terms).
- 작업 ID `717bfa61-3371-4695-957b-9d90f20f8520`, 2026-10-15, **120크레딧 사용**.
  [제작 명세](../../assets/items/female_barbarian_bracers/tripo_v1/build.json),
  [요청·비용·작업 기록](../../assets/items/female_barbarian_bracers/tripo_v1/generation.json).
- 입력은 원화 3면을 반시계 방향으로 90° 돌려 긴 축을 세운 것이다(손목 입구가 아래).
  등쪽=front, 옆=right, 손바닥쪽=back.

원본은 메시 1개, **1,704 triangles**, 4K 컬러·노멀·ORM 텍스처다. 연결 성분 1개, 경계선 0개,
비다양체 모서리 10개, 퇴화 면·UV 붕괴 0개다. 안쪽 벽이 있는 속 빈 통이며 양 끝이 열려 있다.
철판은 원본 +X 쪽에 있다. 손바닥쪽 버클은 생성 결과에서 뚜렷하지 않다.

| 보존 원본 | 파일 |
| --- | --- |
| Tripo GLB | [model_url.glb](../../assets/items/female_barbarian_bracers/tripo_v1/source/model_url.glb) |
| 원본 Blender | [source.blend](../../assets/items/female_barbarian_bracers/tripo_v1/source.blend) |
| 생성 미리보기 | [rendered_image_url.png](../../assets/items/female_barbarian_bracers/tripo_v1/source/rendered_image_url.png) |
| 원본 진단 | [review.json](../../assets/items/female_barbarian_bracers/tripo_v1/review.json), [재현 스크립트](../../assets/items/female_barbarian_bracers/tripo_v1/review_source.py) |

## 피팅 v1

[`tools/fit-female-barbarian-bracers.py`](../../tools/fit-female-barbarian-bracers.py)로 만든다.
기준 몸체는 `assets/modular_human_female_01/rig_v1/female-base.glb`, 리그는 `human_female_01_local_v1` 65본이다.

- 원본 안쪽 벽을 높이·각도별로 실제 팔뚝 단면 48개에 맞추고, 피부에서 **4mm** 띄운다.
  안쪽 벽 위의 철판·띠·리벳 높이는 길이 배율 그대로 유지한다. 단면 표본 구간에서는 팔 둘레를 따르고, 양 끝 약 15mm는 원본의 벌어짐을 유지한다.
- 손목 관절에서 팔꿈치 쪽으로 **11.7–164.7mm** 구간(팔뚝 길이 약 235mm의 65%)에 놓는다.
  처음에는 7.2mm에서 시작했으나 손목을 굽힐 때 손등 피부가 입구에 최대 4.4mm 파고들어 4.5mm 올렸다.
- 철판은 손등 방향을 향한다. 왼쪽은 같은 맞춤을 왼팔 뼈에서 거울 좌표로 다시 계산하고 면 방향을 뒤집었다.
- 각 손목대는 자기 `ForeArm`에 100% 연결한다. 원본 삼각형·UV·내장 텍스처를 유지하며 쌍은 **3,408 triangles**다.
- [몸체 가림](../../assets/items/female_barbarian_bracers/tripo_v1/fitted_v1/body-occlusion.json)은
  손목대 안쪽 팔뚝 피부 208 triangles이며 양쪽 입구에서 7.2mm 안쪽까지만 가린다. 손은 가리지 않는다.
- [피팅 기록](modular-female-barbarian-bracers-fitting-v1.json),
  [동작 검사](../../assets/items/female_barbarian_bracers/tripo_v1/fitted_v1/animation-validation.json)
  ([`tools/validate-female-barbarian-bracers.mjs`](../../tools/validate-female-barbarian-bracers.mjs)),
  [리뷰 렌더 스크립트](../../tools/blender-scripts/review_female_barbarian_bracers.py).

단일 검수 프레임 14개는 정리하고 원본·피팅 원본 Blender, 최종 GLB, 검증 기록과 문서용 합본 이미지는 보존했다.
기사 갑옷과 손목대를 처음 함께 불러오거나 장갑·상의를 교체해도 소매 720 triangles가 유지되는지 브라우저에서 확인했다.

### 동작 검사

런타임 `bindModularPart`로 붙이고 몸체 가림을 적용한 뒤, 정지 자세와 미리보기 클립 14개를 33프레임씩 표본으로 잡아
보이는 몸체 정점이 손목대 안으로 들어가는지 검사했다.
낚시·승마·대검·강화·소셜·단검 등 런타임 전용 클립은 검사하지 않았다.

- 같은 팔(팔뚝·손) 피부의 관통은 모든 클립에서 **0**이다.
- `walk`는 33프레임 중 32프레임에서 손목대가 엉덩이·허벅지에 최대 **3.7mm** 겹친다.
  맨팔 상태에서도 이 동작의 팔뚝–허벅지 피부 간격이 1.1mm까지 줄어들어 두께가 있는 손목대로는 피할 수 없다.
  `sit_idle`(맨팔 간격 8.9mm, 겹침 2.3mm)과 `dying`(4.0mm, 2.4mm)도 간격이 손목대 두께보다 좁다.
  해결하려면 해당 동작의 팔 위치를 조정해야 한다.
