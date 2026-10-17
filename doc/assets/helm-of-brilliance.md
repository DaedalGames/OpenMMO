# 광휘의 투구 — 남녀 피팅·리깅

2026-10-17. 앞·뒤 두 장으로 생성한 Tripo 원본을 남녀 기준 몸체에 따로 맞췄다.
두 파일 모두 기존 65본을 사용하며 투구·수정·날개·목 보호대 전체를 **Head 100%**로 연결한다.
현재 남성은 피팅 v1, 여성은 원본 비율을 복원한 균일 축소 v3를 사용한다.
게임 장비 등록·조명·지능 효과는 후속 단계다.

## 여성 균일 축소 v3 — 현재

사용자 결정(2026-10-17): 부위별 변형을 없애고 전체를 같은 비율로 줄여 머리와의 큰 틈을 줄인다.
변형된 여성 v1·v2를 입력으로 쓰지 않고 **Tripo 원본에서 다시 제작**했다.

- 세 축 배율 **0.30 / 0.30 / 0.30**, 위치 **(0, 1.710, -0.015)m**.
  원본 노드 변환과 정면 방향 회전을 반영한 뒤 균일 스케일과 평행 이동만 적용한다.
  볼 보호대·돔·날개·수정에 별도 변형을 적용하지 않는다.
- 최초 여성 피팅과 비교해 전체 폭 약 25%, 높이·깊이 약 20% 축소.
  최초 피팅은 가로 배율이 달랐으므로 해당 파일을 균일 축소하는 대신 원본 비율부터 복원했다.
- 내보낸 전체 정점을 원본의 균일 변환 결과와 비교한 최대 오차는 **0.000000060m 미만**.
  원본 삼각형 인덱스·UV·내장 4K 텍스처 바이트를 그대로 유지했다.
- 실제 런타임 연결, 65본·기준 행렬, Head 100%, 14개 클립 × 33개 샘플과
  고개 회전을 포함한 467개 자세에서 강체 부착과 유한 좌표 검사를 통과했다.
- **제한:** 피부를 숨기지 않은 상태에서 귀·뒤통수 등 투구 안쪽 피부와의 교차가 남는다.
  FCL 검사는 467개 자세 모두에서 교차를 검출했다. 정면·측면·후면·사선의 착용 모습을
  검토했지만 전 자세 무관통 판정은 하지 않는다. 내부 교차를 없애려고 투구를 다시
  늘리거나 보호대를 찌그러뜨리지 않는다. 게임 적용 전 내부 피부 처리 검토가 필요하다.
- [여성 GLB](../../assets/items/helm_of_brilliance/tripo_v2/fitted_v3/female/helmet_brilliance.glb) · [Blender](../../assets/items/helm_of_brilliance/tripo_v2/fitted_v3/female/helm-brilliance-female-fitted.blend).
- [피팅 명세](../../assets/items/helm_of_brilliance/tripo_v2/fitted_v3/female/fitting.json) · [리깅·동작](../../assets/items/helm_of_brilliance/tripo_v2/fitted_v3/female/animation-validation.json) · [피부 교차](../../assets/items/helm_of_brilliance/tripo_v2/fitted_v3/female/skin-clearance-validation.json) · [브라우저 로딩·서빙 해시](../../assets/items/helm_of_brilliance/tripo_v2/fitted_v3/female/browser-validation.json).

![여성 균일 축소 착용](../../assets/items/helm_of_brilliance/tripo_v2/fitted_v3/female/review/head-angle.png)

## 제작 미리보기

- [남성 착용](https://localhost:10004/modular-character-preview.html?helmet=brilliance&camera=face&top=none&motion=idle1)
- [여성 착용 v3](https://localhost:10004/modular-character-preview.html?character=female&helmet=brilliance&camera=face&hair=none&motion=rest&fit=v3)

기존 제작 페이지의 투구 선택 목록에 광휘의 투구를 추가했다. 회전·확대·동작 재생으로 확인할 수 있다.
착용 중 헤어를 숨기며 탈착 후 선택한 헤어를 복원한다. 여성의 피부 가림 마스크는 비어 있다.
브라우저에서 실제 제공된 GLB의 해시와 로컬 v3 파일의 일치를 확인했다.

## 파일과 기준

| 구분 | 남성 | 여성 |
| --- | --- | --- |
| 기준 몸체 | `assets/modular_human_male_01/fitted/base.glb` | `assets/modular_human_female_01/rig_v1/female-base.glb` |
| 리그 ID | `human_male_01_mixamo_candidate_v2` | `human_female_01_local_v1` |
| 현재 피팅 | v1 | v3 균일 축소 |
| GLB | [남성](../../assets/items/helm_of_brilliance/tripo_v2/fitted_v1/male/helmet_brilliance.glb) | [여성](../../assets/items/helm_of_brilliance/tripo_v2/fitted_v3/female/helmet_brilliance.glb) |
| Blender | [남성](../../assets/items/helm_of_brilliance/tripo_v2/fitted_v1/male/helm-brilliance-male-fitted.blend) | [여성](../../assets/items/helm_of_brilliance/tripo_v2/fitted_v3/female/helm-brilliance-female-fitted.blend) |
| 피팅·몸체 해시 | [남성 명세](../../assets/items/helm_of_brilliance/tripo_v2/fitted_v1/male/fitting.json) | [여성 명세](../../assets/items/helm_of_brilliance/tripo_v2/fitted_v3/female/fitting.json) |

각 몸체의 본 계층·본 순서·inverse bind matrix를 복사한다. 남녀 파일은 리그 ID와 bind 기준이
다르므로 교환해서 사용하지 않는다. 새 Auto Rig나 천 시뮬레이션은 사용하지 않는다.
[남성 착용 이미지](../../assets/items/helm_of_brilliance/tripo_v2/fitted_v1/male/review/head-angle.png).
두 투구 모두 3,685 triangles다. 몸체와 투구의 합계는 남성 숨김 포함 17,576, 표시 16,999,
여성 25,860이다. 의상·무기·망토를 포함한 게임 최종 예산과 얼굴 배분은 장비 등록 단계에서 확인한다.

## 이전 피팅 기록

- 남성 v1: 방사형 머리 간격 탐색 후 아래 볼 보호대를 최대 3cm, 뒤 목 보호대를 최대 6cm
  들어 올렸다. 실제 정점 최대 이동은 4.97cm다. 남성 8개 클립, 총 269개 검사 자세의 피부 교차 0개.
  [리깅·동작](../../assets/items/helm_of_brilliance/tripo_v2/fitted_v1/male/animation-validation.json) · [피부 교차](../../assets/items/helm_of_brilliance/tripo_v2/fitted_v1/male/skin-clearance-validation.json).
- **[미사용] 여성 v1:** 비균일 초기 배율과 보호대 국소 변형을 사용했다. 467개 검사 자세의 교차는
  없었지만 사용자 검토에서 머리와 투구 사이 간격이 너무 컸다. `fitted_v1/female/fitting.json`에 수치·해시만 보존한다.
- **[미사용] 여성 v2:** 위쪽 폭·앞쪽 테두리·돔을 따로 줄인 시도.
  사용자가 볼 보호대의 찌그러짐과 여전히 큰 간격을 지적해 폐기했다.
  `fitted_v2/female/` 및 `rejected-radial/`의 `fitting.json`만 실패 이력으로 보존한다.
- [초기 교차·보정 이력](../../assets/items/helm_of_brilliance/tripo_v2/fitted_v1/fitting-history.json).

## 재현과 출처

현재 여성 피팅:

```sh
.venv/bin/python tools/fit-helm-of-brilliance.py female --uniform-scale 0.30 --offset 0 1.710 -0.015 --directory assets/items/helm_of_brilliance/tripo_v2/fitted_v3/female
node tools/validate-helm-of-brilliance.mjs female assets/items/helm_of_brilliance/tripo_v2/fitted_v3/female
.venv/bin/python tools/validate-helm-of-brilliance-clearance.py female --directory assets/items/helm_of_brilliance/tripo_v2/fitted_v3/female
blender -b --python-exit-code 1 -P tools/blender-scripts/review_helm_of_brilliance.py -- female --directory assets/items/helm_of_brilliance/tripo_v2/fitted_v3/female
```

피부 교차 도구는 보고서를 저장한 뒤 교차가 있으면 실패로 종료한다. 현재 v3의 알려진 제한에 해당한다.
이전 여성 보호대 보정·밀착 변형 도구를 v3에 다시 적용하지 않는다.
커밋 정리(2026-10-17): 실패 피팅의 GLB·Blender 복사본, 로그, 임시 스크린샷·렌더,
대용량 포즈 덤프를 삭제했다. 원본·현재 남녀 GLB와 Blender·제작 기록·검증 요약·문서 이미지는 남겼다.
피부 교차 보고서는 자세별 덤프를 제외한 요약이며 위 도구로 다시 생성할 수 있다.

Python은 프로젝트 `.venv`, 교차 검증은 `python-fcl 0.7.0.11`, 렌더는 Blender 5.2.0 LTS를 사용했다.
Blender에는 기준 몸체·공유 리그·피팅 투구·검토 자세와 숨겨진 원본 참조가 있다.

원본: Tripo API 유료 크레딧, `P2-20260801`, 생성일 2026-10-17,
작업 `bfe87055-a7ff-4539-8c67-8c98ffecc234`. [Tripo 이용 조건](https://developers.tripo3d.ai/en/terms) 적용.
원화: OpenAI Codex built-in ImageGen, **ChatGPT Pro 20x**, 2026-10-17, OpenAI 출력물 이용 조건 적용.
피팅·리깅·검토 렌더는 로컬 스크립트와 Blender로 제작했으며 추가 유료 생성은 없었다.
몸체의 출처는 [남성](modular-human-male-01.md)·[여성](modular-human-female-01.md) 기록을 따른다.
