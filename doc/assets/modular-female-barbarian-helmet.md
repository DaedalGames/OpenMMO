# 여성 바바리안 뿔 투구 — 2026-10-15

[여성 바바리안 원화](../../client/public/character_concepts/female_barbarian.webp)의 투구를
앞·옆·뒤 3면 원화로 옮기고 Tripo로 생성해 여성 공통 몸체의 머리에 피팅했다.
여성 미리보기의 투구 칸에 연결했다. 장비 등록은 하지 않았다.

![앞·옆·뒤 원화](../../assets/items/female_barbarian_helmet/concept_v1/sheet.png)

## 출처

- 원화: OpenAI Codex built-in ImageGen(`codex exec`, codex-cli 0.162.1), **ChatGPT Pro 20x**, 2026-10-15.
  OpenAI 출력물 이용 조건을 따른다. 참조 원화의 출처는 [캐릭터 문서](characters.md)에 있다.
- [프롬프트](../../assets/items/female_barbarian_helmet/concept_v1/prompt.txt),
  [참조·분리 영역·해시 기록](../../assets/items/female_barbarian_helmet/concept_v1/sources.json).
  참조는 원화의 머리 부분을 흰 배경에 잘라 3배 확대했다.

## 원화 v1

어두운 단조 철 두개모에 리벳 박힌 세로 띠 세 줄, 이마 가운데가 짧게 뾰족한 이마 띠,
얼굴을 가리지 않는 긴 볼가리개, 리벳 고리에 박힌 굽은 소뿔 한 쌍으로 구성한다.
뒤쪽은 띠가 목덜미에서 모이고 짧은 목가리개로 끝난다. 원래 원화에서 보이지 않는 부분이라 새로 정했다.
옆면에서는 앞쪽 뿔이 반대쪽 뿔을 가린다.

| 보기 | 파일 |
| --- | --- |
| 앞 | [front.png](../../assets/items/female_barbarian_helmet/concept_v1/front.png) |
| 옆(얼굴 쪽이 왼쪽) | [side.png](../../assets/items/female_barbarian_helmet/concept_v1/side.png) |
| 뒤 | [back.png](../../assets/items/female_barbarian_helmet/concept_v1/back.png) |

각 보기는 시트의 자기 열만 남겨 같은 배율로 900×900 흰 정사각형 가운데에 놓았다.

## Tripo 원본

Tripo API 유료 크레딧, 모델 `P2-20260801`, 텍스처 `v3.5-20260815`, detailed PBR, 입력 조명 제거,
목표 2,500 triangles(기사 투구 2,000에 뿔 몫 추가).
[API 문서](https://developers.tripo3d.ai/en/docs/generation-multiview-to-model/p),
[이용 조건](https://developers.tripo3d.ai/en/terms). 두 번 생성해 **240크레딧**을 썼다(잔액 440 → 200).

### v1 — **[미사용]**

앞·옆·뒤 3장, seed 101504, 작업 ID `9c2d2ed5-c194-4d5b-905f-c25dde1a51d9`, 120크레딧.
뒤쪽이 앞면을 복제해 이마 뾰족 끝·볼가리개·얼굴 구멍이 뒤통수에도 생겼다. 원본은 기록용으로 보존했다.
[제작 명세](../../assets/items/female_barbarian_helmet/tripo_v1/build.json),
[작업 기록](../../assets/items/female_barbarian_helmet/tripo_v1/generation.json),
[검토 렌더](../../assets/items/female_barbarian_helmet/tripo_v1/review/strip.png).

### v2 — 현재

사용자 결정으로 옆면을 빼고 앞·뒤 2장으로 다시 생성했다(기사 투구와 같은 방식). seed 101505,
작업 ID `58d0c136-f714-4e60-bc2f-aed24abf3901`, 120크레딧.
[제작 명세](../../assets/items/female_barbarian_helmet/tripo_v2/build.json),
[요청·비용·작업 기록](../../assets/items/female_barbarian_helmet/tripo_v2/generation.json).

메시 1개, **2,179 triangles**, 4K 컬러·노멀·ORM 텍스처다. 정면은 원본 +X, 뿔은 ±Z 방향이다.
뒤쪽은 원화대로 띠가 모이고 목가리개로 닫힌다. 리벳 등 작은 조각을 포함해 연결 성분 57개,
열린 경계 417개이며 퇴화 면·UV 붕괴는 0개다. 밀폐된 솔리드로 판정하지 않는다.

| 보존 원본 | 파일 |
| --- | --- |
| Tripo GLB | [model_url.glb](../../assets/items/female_barbarian_helmet/tripo_v2/source/model_url.glb) |
| 원본 Blender | [source.blend](../../assets/items/female_barbarian_helmet/tripo_v2/source.blend) |
| 생성 미리보기 | [rendered_image_url.png](../../assets/items/female_barbarian_helmet/tripo_v2/source/rendered_image_url.png) |
| 원본 진단 | [review.json](../../assets/items/female_barbarian_helmet/tripo_v2/review.json), [재현 스크립트](../../assets/items/female_barbarian_helmet/tripo_v2/review_source.py) |

## 피팅 v1

[`tools/fit-female-barbarian-helmet.py`](../../tools/fit-female-barbarian-helmet.py)로 만든다.
기준 몸체는 `assets/modular_human_female_01/rig_v1/female-base.glb`, 리그는 `human_female_01_local_v1` 65본이다.

- 원본 +X 정면을 +Z로 돌린다(`[-z, y, x]`).
- 이마 뾰족 끝을 눈썹 사이 높이(y 0.951)에 고정하고, 축별 배율(축 간 비율 1.12 이내)과 앞뒤 위치를 탐색했다.
  머리 중심에서 쏜 광선 1,422개 중 투구에 닿는 947개에서 머리·목 피부와 **3mm** 이상 떨어지는 가장 작은 크기를 골랐다.
- 결과 배율 `[0.1775, 0.16, 0.175]`, 이동 `[0, 0.9648, -0.006]`(몸체 높이 1 기준 좌표).
  피부와의 간격은 최소 **3.2mm**, 중앙값 18mm다.
- 모든 정점을 **Head 100%**로 연결한다. 뿔·볼가리개를 포함해 투구 전체가 머리와 함께 움직인다.
- 원본 삼각형·UV·4K 텍스처 바이트를 유지하고 노멀·탄젠트를 다시 계산했다.
- 피부는 가리지 않는다. 뿔 투구 아래로 보이는 헤어는 남기고, 은빛 기사 투구는 기존처럼 헤어를 숨긴다.
- [피팅 기록](modular-female-barbarian-helmet-fitting-v1.json),
  [동작 검사](../../assets/items/female_barbarian_helmet/tripo_v2/fitted_v1/animation-validation.json)
  ([`tools/validate-female-barbarian-helmet.mjs`](../../tools/validate-female-barbarian-helmet.mjs)),
  [리뷰 렌더 스크립트](../../tools/blender-scripts/review_female_barbarian_helmet.py).

### 동작 검사

런타임 `bindModularPart`로 붙인 뒤 Head 기준 공간에서 몸체 정점을 검사했다. 투구 면 뒤로 7.2mm 이내에 있고
머리 중심에서 그 정점까지의 선분이 투구를 지나는 경우를 관통으로 센다. 띠처럼 바깥 면만 있는 열린 부분 때문에
법선 부호만으로는 오검출이 생겨 선분 조건을 더했다. 정지 자세는 전체 정점을, 미리보기 클립 14개는 Head에 완전히
묶이지 않은 정점(목·어깨·팔·손 등)을 33프레임씩 검사했다.

- 정지 자세와 14개 클립 모두에서 관통 **0**이다.
- 검사 감도: 투구를 머리 중심 기준 3% 줄이면 관통 0, 5% 줄이면 1.4mm 관통 1건이 잡힌다. 최소 간격 3.2mm와 일치한다.
- 7.2mm보다 깊이 뚫고 나간 경우는 잡지 못한다. 낚시·승마 등 런타임 전용 클립은 검사하지 않았다.

### 투구 아래 헤어

투구를 썼을 때 헤어 전체가 사라지던 처리를 바꿨다. 투구의 아래 테두리를 180개 각도 구간으로 따라가며
가려지는 윗부분을 잘라낸 전용 헤어를 쓴다. 단발은 옆머리와 뒷머리를 남기며, 보관된 긴 헤어도 지원한다.
볼가리개의 아래 끝을 귀 뒤까지 연장해 자르지 않는다. 귀 뒤쪽은 두개모·목가리개의 경계 아래까지 복원하고,
투영 삼각형이 실제로 겹치는 곳만 연속적인 좌우 축소로 볼가리개 안쪽에 맞춘다.
사선에서 피부가 보이던 볼가리개 아래 다발도 복원했다. 복원 범위의 앞쪽 한계를 몸체 좌표 z=0.025까지 넓혔다.
정면에 가까운 각도에서 남은 볼가리개 끝의 틈은 y=0.887 아래의 다발만 z=0.04까지 추가 복원했다.
겹쳐 있는 머리카락 면들은 같은 축소장을 공유하며, UV 이음새도 같은 위치를 유지한다.
경계 정점의 UV·노멀·탄젠트·웨이트를 보간하고 원래 텍스처 바이트를 유지했다.
잘라낸 원본 면 내부의 불필요한 분할선은 합쳐 다시 삼각형으로 연결했다.
기존 [금발 헤어](modular-female-knight-hair.md)의 파생본이며 해당 원본의 출처·이용 조건을 따른다.

- [단발 GLB](../../assets/items/female_barbarian_helmet/tripo_v2/fitted_v1/hair_bob_barbarian_helmet.glb): **1,805 triangles**.
- [긴 헤어 GLB](../../assets/items/female_barbarian_helmet/tripo_v2/fitted_v1/hair_knight_barbarian_helmet.glb): **3,707 triangles**.
- [Blender 편집본](../../assets/items/female_barbarian_helmet/tripo_v2/fitted_v1/female-barbarian-helmet-hair-fitted.blend):
  원래 몸체·투구와 공유 리그에 연결한 두 헤어를 포함한다. 긴 헤어는 숨긴 상태로 보존한다.
- [절단·해시 기록](../../assets/items/female_barbarian_helmet/tripo_v2/fitted_v1/hair-trim.json),
  [재현 스크립트](../../tools/trim-female-barbarian-helmet-hair.py). NumPy·SciPy·Shapely 2.1·trimesh가 필요하다.
- 투구를 벗으면 원래 헤어로 복원하고, 헤어 없음·단발·긴 헤어 전환에도 선택을 유지한다.
  원본 헤어 GLB와 투구 GLB는 수정하지 않았다.

```bash
.venv/bin/python tools/trim-female-barbarian-helmet-hair.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 node tools/validate-female-barbarian-helmet-hair.mjs
node tools/validate-female-barbarian-helmet-hair-coverage.mjs
blender -b --python-exit-code 1 --python tools/blender-scripts/save_female_barbarian_helmet_hair.py
```

검사는 실제 `bindModularPart`와 미리보기 동작을 사용해 머리 본의 기준 공간에서 헤어와 투구의 간격 및
양방향 모서리→면 교차를 확인한다. 단발처럼 머리 본에 고정된 형상은 상대 좌표 일치를 확인하고 정지 검사를 재사용한다.
관절의 영향으로 움직이는 긴 헤어는 동작별 형상을 검사한다. 생성한 포즈 버퍼는 검사 종료 시 삭제한다.

[검사 결과](../../assets/items/female_barbarian_helmet/tripo_v2/fitted_v1/hair-animation-validation.json)는
각 헤어의 정지 자세와 14개 클립 총 **239시점**에서 교차 **0건**이며, 최소 표본 간격은 단발 **1.19mm**,
긴 헤어 **0.68mm**다. 연속 시점 전체나 검사하지 않은 런타임 전용 동작까지 보장하지 않는다.
브라우저 검사에서
뿔 투구·기사 투구·투구 없음과 헤어 변경 시 선택·복원·표시 수를 확인했다.
기본 몸체와 뿔 투구만 착용하면 단발은 **26,159 triangles**, 긴 헤어는 **28,061 triangles**다.

사선 노출 검사는
표시 영역 주변의 696개 광선을 실제 몸체·헤어·투구에 쏘아 비교했다. 원래 헤어가 덮어야 하지만 피부가 먼저 보이던
38곳이 모두 헤어로 덮였으며, 남은 피부 노출은 0곳이다.
[회귀 검사](../../assets/items/female_barbarian_helmet/tripo_v2/fitted_v1/hair-cheek-coverage-validation.json)는
그 38개 몸체 지점과 같은 카메라·대기 시작 자세를 런타임에서 재현한다.

정면에 가까운 각도에서는 900개 광선으로 끝부분을 비교해, 안쪽 면만 남거나 피부가 보이던 다발의
83개 표면 지점을 추가로 보존했다. 이 지점은 헤어가 먼저 보이는지와 함께 복원된 겉면 위치에서 0.001 몸체 단위
이내 깊이인지 검사한다. 안쪽 헤어가 구멍을 가린 것처럼 판정되는 일을 방지한다.
직전 수정본은 기존 38개 지점만 통과하고 새 83개 지점은 실패하며, 현재는 **121/121개** 모두 통과한다.
이 검사는 두 카메라의 대기 시작 자세를 대상으로 하며 모든 각도·동작의 피부 노출을 보장하지 않는다.
