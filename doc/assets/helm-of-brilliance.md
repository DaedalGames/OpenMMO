# 광휘의 투구

이마의 발광 수정, 황동 테두리·날개 장식, 강철 외피와 가죽 안감을 갖춘 개방형 투구다. 게임 등록·지능 +1·조명 규칙과
런타임 파일은 [아이템 문서](items.md#helm-of-brilliance--광휘의-투구)에 있다.
Tripo v2 원본을 남녀 기준 몸체에 각각 균일 축소로 맞춘 `tripo_v2/fitted_v3/{male,female}`를 쓴다.
두 파일 모두 3,685 triangles, 원본 삼각형·UV·내장 4K 텍스처를 유지하고 투구 전체를 **Head 100%**로 연결한다.

![정면·측면·후면 3면도](../../assets/items/helm_of_brilliance/turnaround_v2_strict_side/sheet.png)

## 최종 파일

| 구분 | 남성 | 여성 |
| --- | --- | --- |
| 기준 몸체 | `assets/modular_human_male_01/fitted/base.glb` | `assets/modular_human_female_01/rig_v1/female-base.glb` |
| 리그 ID | `human_male_01_mixamo_candidate_v2` | `human_female_01_local_v1` |
| GLB | [helmet_brilliance.glb](../../assets/items/helm_of_brilliance/tripo_v2/fitted_v3/male/helmet_brilliance.glb) | [helmet_brilliance.glb](../../assets/items/helm_of_brilliance/tripo_v2/fitted_v3/female/helmet_brilliance.glb) |
| Blender | [helm-brilliance-male-fitted.blend](../../assets/items/helm_of_brilliance/tripo_v2/fitted_v3/male/helm-brilliance-male-fitted.blend) | [helm-brilliance-female-fitted.blend](../../assets/items/helm_of_brilliance/tripo_v2/fitted_v3/female/helm-brilliance-female-fitted.blend) |
| 피팅·몸체 해시 | [fitting.json](../../assets/items/helm_of_brilliance/tripo_v2/fitted_v3/male/fitting.json) | [fitting.json](../../assets/items/helm_of_brilliance/tripo_v2/fitted_v3/female/fitting.json) |
| 귀 보정 | [ear-fitting.json](../../assets/items/helm_of_brilliance/tripo_v2/fitted_v3/male/ear-fitting.json), [body-occlusion.json](../../assets/items/helm_of_brilliance/tripo_v2/fitted_v3/male/body-occlusion.json) | [ear-fitting.json](../../assets/items/helm_of_brilliance/tripo_v2/fitted_v3/female/ear-fitting.json), [body-occlusion.json](../../assets/items/helm_of_brilliance/tripo_v2/fitted_v3/female/body-occlusion.json) |
| 검사 | [리깅·동작](../../assets/items/helm_of_brilliance/tripo_v2/fitted_v3/male/animation-validation.json), [피부 교차](../../assets/items/helm_of_brilliance/tripo_v2/fitted_v3/male/skin-clearance-validation.json) | [리깅·동작](../../assets/items/helm_of_brilliance/tripo_v2/fitted_v3/female/animation-validation.json), [피부 교차](../../assets/items/helm_of_brilliance/tripo_v2/fitted_v3/female/skin-clearance-validation.json) |

각 파일은 해당 몸체의 본 계층·순서·inverse bind matrix를 복사하므로 남녀 파일을 바꿔 쓰지 않는다.

## 남성 균일 축소 v3 — 현재

- 세 축 배율 **0.33**, 위치 **(0, 1.800, -0.015)m**. 원본 균일 변환과 출력 정점의 최대 오차는 0.000000060m 미만이다.
- 귀 보정: 양쪽 귀 뒤쪽 524개 정점을 안쪽으로 압축한다. 삼각형·UV·Head/Neck 가중치는 그대로이며 벗으면 원래 머리로 돌아간다.
  기준 남성 얼굴에만 적용하고 rugged/ranger 대체 얼굴에는 적용하지 않는다.
- 8개 클립과 고개 회전을 포함한 269개 자세에서 강체 부착 검사를 통과했다.

## 여성 균일 축소 v3 — 현재

- 세 축 배율 **0.30**, 위치 **(0, 1.710, -0.015)m**. 최대 오차는 남성과 같다.
- 귀 보정: 양쪽 귀 위·뒤쪽 736개 정점을 안쪽으로 접힘 없이 압축하고, 모든 피부 삼각형을 유지한다. 벗으면 원래 정점·노멀·삼각형으로 돌아간다.
- 착용 중 헤어를 숨기고 벗으면 선택한 헤어를 복원한다.
- 14개 클립 × 33개 표본과 고개 회전을 포함한 467개 자세에서 강체 부착·유한 좌표 검사를 통과했다.

## 재현

`<sex>`는 `male` 또는 `female`이며, 검사 도구는 `fitted_v3/<sex>`를 기본으로 읽는다.

```sh
.venv/bin/python tools/fit-helm-of-brilliance.py male --uniform-scale 0.33 --offset 0 1.800 -0.015 --directory assets/items/helm_of_brilliance/tripo_v2/fitted_v3/male
.venv/bin/python tools/fit-helm-of-brilliance.py female --uniform-scale 0.30 --offset 0 1.710 -0.015 --directory assets/items/helm_of_brilliance/tripo_v2/fitted_v3/female
.venv/bin/python tools/fit-helm-of-brilliance-ears.py <sex>
node tools/validate-helm-of-brilliance.mjs <sex>
.venv/bin/python tools/validate-helm-of-brilliance-clearance.py <sex>
blender -b --python-exit-code 1 -P tools/blender-scripts/review_helm_of_brilliance.py -- <sex>
```

피부 교차 도구는 보고서를 저장한 뒤 교차가 있으면 실패로 끝난다(아래 제한). 교차 검사는 `python-fcl 0.7.0.11`, 렌더는 Blender 5.2.0 LTS를 썼다.

## 출처·라이선스

- 원화: OpenAI Codex built-in ImageGen, **ChatGPT Pro 20x**, 2026-10-17. OpenAI 출력물 이용 조건 적용, 별도 CC 라이선스 없음.
  NetHack의 아이템 이름과 지능 보너스에서 착안한 새 디자인이며 원작 이미지·모델은 쓰지 않았다.
  아래 순서로 앞 이미지를 편집 원본으로 삼았다.
  1. [concept_v1](../../assets/items/helm_of_brilliance/concept_v1/concept.png): 첫 원화.
     [프롬프트](../../assets/items/helm_of_brilliance/concept_v1/prompt.txt) · [생성 기록](../../assets/items/helm_of_brilliance/concept_v1/generation.json).
  2. [concept_v2_wings](../../assets/items/helm_of_brilliance/concept_v2_wings/concept.png): 귀 양옆에 황동 깃털 날개 추가.
     [프롬프트](../../assets/items/helm_of_brilliance/concept_v2_wings/prompt.txt) · [생성 기록](../../assets/items/helm_of_brilliance/concept_v2_wings/generation.json).
  3. [turnaround_v1](../../assets/items/helm_of_brilliance/turnaround_v1/sheet.png): 정면·오른쪽 측면·후면 3면도. 후면은 원화에 없는 구조를 보완했다.
     [프롬프트](../../assets/items/helm_of_brilliance/turnaround_v1/prompt.txt) · [생성 기록](../../assets/items/helm_of_brilliance/turnaround_v1/generation.json).
  4. [turnaround_v2_strict_side](../../assets/items/helm_of_brilliance/turnaround_v2_strict_side/sheet.png): 측면에서 반대편 내부가 보이지 않게 고친 3면도.
     [프롬프트](../../assets/items/helm_of_brilliance/turnaround_v2_strict_side/prompt.txt) · [생성 기록](../../assets/items/helm_of_brilliance/turnaround_v2_strict_side/generation.json) ·
     [분리 영역](../../assets/items/helm_of_brilliance/turnaround_v2_strict_side/split.json)(재생성·리사이즈 없이 512×800으로 잘라 Tripo 입력으로 씀).
- 3D: Tripo API 유료 크레딧, 모델 `P2-20260801`, 텍스처 `v3.5-20260815`, detailed PBR, 입력 조명 제거, seed `101701`,
  목표 4,000 triangles, 2026-10-17. [API 문서](https://developers.tripo3d.ai/en/docs/generation-multiview-to-model/p),
  [이용 조건](https://developers.tripo3d.ai/en/terms). 두 번 생성해 **240크레딧**을 썼다.
- **v2(채택)**: 앞·뒤 2장, 작업 ID `bfe87055-a7ff-4539-8c67-8c98ffecc234`, 120크레딧(사용자 충전 후 잔액 1,080 → 960).
  결과 3,685 triangles, 컬러·노멀·ORM 각 4096×4096.
  [제작 명세·입력 해시](../../assets/items/helm_of_brilliance/tripo_v2/build.json) ·
  [요청·작업·비용 기록](../../assets/items/helm_of_brilliance/tripo_v2/generation.json) ·
  [잔액 확인](../../assets/items/helm_of_brilliance/tripo_v2/preflight.json) ·
  [입력](../../assets/items/helm_of_brilliance/tripo_v2/inputs/) ·
  [Tripo GLB](../../assets/items/helm_of_brilliance/tripo_v2/source/model_url.glb) ·
  [원본 Blender](../../assets/items/helm_of_brilliance/tripo_v2/source.blend) ·
  [형상 진단](../../assets/items/helm_of_brilliance/tripo_v2/review.json)([스크립트](../../assets/items/helm_of_brilliance/tripo_v2/review_source.py)).
- **[미사용] v1**: 앞·옆·뒤 3장, 작업 ID `0c5ee49d-ff5b-437c-962d-ea478a3c7aa2`, 120크레딧(잔액 200 → 80), 결과 3,705 triangles.
  뒤통수에 이마 수정과 얼굴 구멍이 복제되어 쓰지 않는다. 생성 원본으로 보존한다.
  [제작 명세·입력 해시](../../assets/items/helm_of_brilliance/tripo_v1/build.json) ·
  [요청·작업·비용 기록](../../assets/items/helm_of_brilliance/tripo_v1/generation.json) ·
  [입력](../../assets/items/helm_of_brilliance/tripo_v1/inputs/) ·
  [Tripo GLB](../../assets/items/helm_of_brilliance/tripo_v1/source/model_url.glb) ·
  [원본 Blender](../../assets/items/helm_of_brilliance/tripo_v1/source.blend) ·
  [형상 진단](../../assets/items/helm_of_brilliance/tripo_v1/review.json)([스크립트](../../assets/items/helm_of_brilliance/tripo_v1/review_source.py)).
- 피팅·리깅·검토 렌더는 로컬 스크립트와 Blender로 만들었고 추가 유료 생성은 없다.
  몸체 출처는 [남성](modular-human-male-01.md)·[여성](modular-human-female-01.md) 기록을 따른다.

## 제한

- 귀·뒤통수 등 투구 안쪽 피부와의 교차가 남는다. 귀 보정 전 FCL 검사는 남성 269개·여성 467개 자세 모두에서 교차를 검출했으며
  전 자세 무관통 판정은 하지 않는다. 투구를 키우거나 보호대를 변형해 없애지 않는다.
- 여성의 뒤통수 등 귀 외 내부 피부는 추가 검토가 필요하다.
