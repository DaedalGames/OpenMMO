# 여성 바바리안 가죽 하이힐 샌들 — 2026-10-15

여성 바바리안 원화에서 신발을 분리해 Tripo로 생성하고 여성 공통 몸체에 피팅했다.
현재 **피팅 v3**를 여성 미리보기에 연결했다. 장비 등록은 하지 않았다.
신발의 뒤꿈치 방향을 맞춘 저장 시점이며, 일부 동작의 앞끈 관통은 추가 피팅이 필요하다.

![앞·옆·뒤 원화](../../assets/items/female_barbarian_boots/concept_v1/sheet.png)

## 출처와 생성

- 디자인: [여성 바바리안 원화](../../client/public/character_concepts/female_barbarian.webp).
  굽 형태는 [여성 기사 판금 부츠](modular-female-knight-boots.md)를 참조했다.
- 원화 제작: OpenAI Codex built-in ImageGen(`codex exec`, codex-cli 0.162.1),
  **ChatGPT Pro 20x**, 2026-10-15. OpenAI 출력물 이용 조건을 따른다.
  참조 원화의 출처는 [캐릭터 문서](characters.md)에 있다.
- [프롬프트](../../assets/items/female_barbarian_boots/concept_v1/prompt.txt),
  [참조·분리 영역·해시 기록](../../assets/items/female_barbarian_boots/concept_v1/sources.json).
  앞·옆·뒤 입력은 같은 배율의 800×800 흰 정사각형으로 분리했다.
- Tripo API 유료 크레딧, 모델 `P2-20260801`, 텍스처 `v3.5-20260815`, detailed PBR,
  입력 조명 제거, 한 짝 목표 1,500 triangles, seed 101502.
  [API 문서](https://developers.tripo3d.ai/en/docs/generation-multiview-to-model/p),
  [이용 조건](https://developers.tripo3d.ai/en/terms).
- 작업 ID `a4ac552f-032f-4822-9978-fad40d1ff10e`, **120크레딧 사용**.
  [제작 명세](../../assets/items/female_barbarian_boots/tripo_v1/build.json),
  [요청·비용·작업 기록](../../assets/items/female_barbarian_boots/tripo_v1/generation.json).
  추가 유료 생성 없이 기존 결과를 사용했다.

착용자 오른쪽 한 짝을 생성했다. 앞이 트인 갈색 가죽 샌들, 발목 고리 세 줄,
리벳·버클, 넓은 앞끈과 가는 스틸레토 굽으로 구성한다. 폴더 이름은 장비 슬롯(`boots`)에 맞췄다.
원본은 메시 1개, **1,664 triangles**, 4K 컬러·노멀·ORM 텍스처다.
연결 성분 9개, 경계선 3개, 퇴화 면·UV 붕괴 0개로 진단했다.

![Tripo 원본 검토](../../assets/items/female_barbarian_boots/tripo_v1/review/strip.png)

| 보존 원본 | 파일 |
| --- | --- |
| Tripo GLB | [model_url.glb](../../assets/items/female_barbarian_boots/tripo_v1/source/model_url.glb) |
| 원본 Blender | [source.blend](../../assets/items/female_barbarian_boots/tripo_v1/source.blend) |
| 생성 미리보기 | [rendered_image_url.png](../../assets/items/female_barbarian_boots/tripo_v1/source/rendered_image_url.png) |
| 원본 진단 | [review.json](../../assets/items/female_barbarian_boots/tripo_v1/review.json), [재현 스크립트](../../assets/items/female_barbarian_boots/tripo_v1/review_source.py) |

## 현재 피팅 v3

기준 몸체는 `assets/modular_human_female_01/rig_v1/female-base.glb`,
리그는 `human_female_01_local_v1` 65본이다. 몸체·공통 발 코드·애니메이션 파일을 유지한다.
기존 기사 부츠와 같은 `tools/outfits/female_boot_pose.py`의 굽 자세(Foot +30°, ToeBase −30°)에서 피팅한다.

- 신발을 기존 Foot→ToeBase 방향에서 바깥쪽으로 **7°** 더 회전해 뒤꿈치가 밑창 중심에 맞게 했다.
  최종 각도는 착용자 오른쪽 **−17.954°**, 왼쪽 **+17.954°**다.
  길이·폭 정렬도 이 좌표계에서 다시 계산하고 발목 고리와 끈을 재피팅했다.
- 왼발은 같은 각도를 유지한 채 밑창·굽을 발의 가로축을 따라 바깥쪽으로
  **0.0055 source unit(9.9mm)** 옮겨 발 중심선에 맞췄다. 발목 고리까지 이동량을
  부드럽게 줄여 고리 위치를 유지했다.
- 왼발은 각도·가로축 정렬을 유지하며 밑창·굽을 뒤꿈치 방향으로
  **0.003 source unit(5.4mm)** 옮겼다. 발목 고리는 유지하고 앞끈의 피부 여유를
  다시 확보했다. 이 조정에서 오른쪽 신발의 형상·웨이트는 그대로다.
- 오른쪽 밑창 앞끝은 발가락 아래에 가까워지도록 정지 기준 최대 **5.4mm** 들어 올렸다.
  앞끝으로 갈수록 완만하게 높이고, 밑창 윗면의 정점·면 내부 표본에서 피부까지의
  수직 여유를 계산해 피부와 틈이 남도록 들림을 제한했다.
  발볼 접지·뒤꿈치·발목 고리와 왼쪽 신발은 유지했다.
- 오른쪽 앞끝에만 기존 발가락 동작을 최대 **0.45** 비율로 추가 전사했다.
  발가락이 들릴 때 앞 밑창도 함께 올라가며 발볼 접지는 Foot을 유지한다.
  과하게 말린 앞끝을 완화하도록 정지 들림을 7.2→5.4mm, 동작 전사를 0.55→0.45로 줄였다.
- 앞끝 들림과 발가락 웨이트는 이차 곡선으로 점진적으로 증가시켜 밑창의 급한 꺾임을 줄였다.
  오른쪽 발등 스트랩 윗부분은 최대 **7.2mm** 올리고, 밑창에 닿는 부분까지 이동량을
  부드럽게 줄여 연결을 유지했다. 피부 표면 방향으로 최대 **1.8mm** 여유도 추가했다.
- 발목 고리의 각도는 고리 자체 중심에서 계산한 뒤 다리 피부에 맞춘다.
  오른발 형상을 대칭한 후 왼발 피부에서 별도로 피팅하고 웨이트를 전사한다.
- Tripo에서 빠진 뒤쪽 세로 연결끈을 두께 있는 메시로 추가했다.
  한 짝 148 triangles 증가, 두 짝 **3,624 triangles**다. 기존 굽의 가죽 UV 영역을 재사용한다.
- 발목은 피부의 Leg/Foot 비율을 공간상 0.004 source unit 반경에서 다듬고,
  버클은 주변 고리 평균을 쓴다. 뒤꿈치 끈은 Foot에서 아래 고리로 점진적으로 전환한다.
  뒤 세로 연결끈의 웨이트는 0.008 source unit 반경으로 다듬는다.
- 앞끈의 ToeBase 영향은 밑창 위 높이에 따라 최대 0.35다.
  오른쪽 앞끝을 제외한 밑창·굽은 Foot을 유지한다.
  v2에서 추가했던 `fixed_toe_quaternions`와 공통 런타임의 전용 처리를 제거했다.
  발가락 본은 원래 애니메이션에 기존 공통 굽 오프셋만 적용한다.
- 밑창 가장자리가 굽 끝의 바닥 높이 아래로 내려가지 않게 고정했다.
  정지 자세 루트 보정은 기사 부츠와 같은 **0.0302733 source unit**이다.
- 양쪽의 실제 피팅 형상으로 발바닥 아래 86면만 가리는 가역 마스크를 사용한다. 발목 고리 사이와 발등은 유지하며
  장비를 벗거나 로딩에 실패하면 원래 피부를 복원한다.

좌표는 정규화된 여성 몸체의 source unit이다. 실제 1.8m 캐릭터에서는 거리 값에 1.8을 곱한다.
`clearance_m`에는 변환한 값을 기록한다. 새 연결끈은 기존 Tripo 텍스처를 쓰는 직접 제작 메시로
원본과 같은 출처·라이선스를 따른다.

![현재 피팅](../../assets/items/female_barbarian_boots/tripo_v1/fitted_v3/review/strip.png)

| 현재 파일 | 경로 |
| --- | --- |
| 신발 GLB | [boots_female_barbarian.glb](../../assets/items/female_barbarian_boots/tripo_v1/fitted_v3/boots_female_barbarian.glb) |
| 편집용 Blender | [female-barbarian-boots-fitted.blend](../../assets/items/female_barbarian_boots/tripo_v1/fitted_v3/female-barbarian-boots-fitted.blend) |
| 피부 가림 | [body-occlusion.json](../../assets/items/female_barbarian_boots/tripo_v1/fitted_v3/body-occlusion.json) |
| 피팅·리깅 기록 | [modular-female-barbarian-boots-fitting-v3.json](modular-female-barbarian-boots-fitting-v3.json) |
| 후속 검사용 형상·웨이트 | [fit-data.npz](../../assets/items/female_barbarian_boots/tripo_v1/fitted_v3/fit-data.npz) |
| 동작별 굽 보정 | [heel-animation-offsets.json](../../assets/items/female_barbarian_boots/tripo_v1/fitted_v3/heel-animation-offsets.json) |

현재 몸체 22,175 + 단발 2,436 + 샌들 3,624 = 전체 **28,235 triangles**,
발바닥 가림 후 **28,149 triangles**다. 얼굴 앞면은 속눈썹을 포함해 **4,604 triangles**다.
기존 몸체만으로 모듈형 목표 예산을 넘는 상태이며 이번 작업에서 임의로 축소하지 않았다.

## 검증과 남은 작업

- [리그·동작 검사](../../assets/items/female_barbarian_boots/tripo_v1/fitted_v3/runtime-validation.json):
  14동작 × 61시점. 65본 bind 일치, 정규화 웨이트, 반대쪽 다리 영향 없음,
  피부 가림 복원, 원래 발가락 애니메이션 유지, 발 자세 누적 없음, 굽 접지 검사를 통과했다.
  접지 평면은 굽 끝과 Foot에 고정된 발볼로 검사해 움직이는 앞끝을 제외한다.
- [브라우저 기록](../../assets/items/female_barbarian_boots/tripo_v1/fitted_v3/browser-review.json):
  오류 없음, 착탈 반복 시 24,611 ↔ 28,149 triangles로 복원됨을 확인했다.
- [오른쪽 발등 스트랩 검사](../../assets/items/female_barbarian_boots/tripo_v1/fitted_v3/instep-idle-validation.json):
  정지 자세와 대기 동작의 전체 61시점에서 스트랩의 정점·면 중심·모서리 중간 지점을 검사했다.
- [오른발 끈 검사](../../assets/items/female_barbarian_boots/tripo_v1/fitted_v3/clearance-validation.json),
  [왼발 끈 검사](../../assets/items/female_barbarian_boots/tripo_v1/fitted_v3/clearance-left-validation.json):
  각 171시점에서 발목·뒤 연결끈은 관통이 없지만 **앞끈은 미완료**다.
  오른발은 공격, 왼발은 횃불 달리기에서 원래 발가락 동작을 따라가지 못하는 표본이 남았다.
  왼발은 메시·피부 가림이 이전 검사와 완전히 같음을 확인하고 검사 결과를 재사용했다.
  발을 바꾸지 않고 신발 쪽을 추가 피팅할 과제다.
- 끈 검사는 정점·면 중심·모서리 중간 지점과 가리지 않은 피부 삼각형을 비교한다.
  밑창 내부 접촉이나 모든 연속 시점의 무관통을 보장하지 않는다.
- Tripo 텍스처의 넓은 금속색 얼룩도 남아 있다. 장비 등록과 프로덕션 적용은 하지 않았다.

## 이전 후보와 정리

- **[미사용] v1**: 정면 축 기준 피팅, 3,328 triangles. 발목 고리 방향 계산과 뒤 연결끈 누락이 남았다.
  [피팅 기록](modular-female-barbarian-boots-fitting-v1.json)을 보존한다.
- **[미사용] v2**: 고리·연결끈과 접지를 보정했지만 발가락 자세 고정을 사용했다.
  사용자 지시에 따라 v3에서 이를 제거했다. [피팅 기록](modular-female-barbarian-boots-fitting-v2.json)을 보존한다.
- **[미사용] 앞 밑창 전체 ToeBase 전사 시도**: 밑창 모양과 늘어남이 악화되어 채택하지 않았다.
- v1/v2 피팅 바이너리, 중간 Blender, ARAP 캐시, 임시 몸체 GLB, 개별 렌더와 브라우저 비교 이미지는 삭제했다.
  현재 v3 GLB·Blender·후속 검사용 fit-data, 원화·입력·생성 원본·출처와 검증 기록,
  이 문서에서 사용하는 원본/현재 검토 스트립은 보존했다.
- 이번 중간 저장에서는 추가 피팅의 비교 이미지·후보 백업·임시 스크립트와 로그
  **251개(약 300MiB)**를 정리하고 현재 피팅과 원본·검증 기록을 보존했다.

## 미리보기와 재현

`/modular-character-preview.html?character=female&camera=feet&boots=barbarian&motion=idle1`에서 확인한다.
Python 의존성은 프로젝트 `.venv`의 NumPy, SciPy, trimesh 5.1.1, rtree 1.4.1이다.
저장소 루트에서 실행한다.

```bash
.venv/bin/python tools/fit-female-barbarian-boots.py
node tools/validate-female-barbarian-boots.mjs
node tools/export-female-barbarian-boots-poses.mjs
node tools/export-female-barbarian-boots-poses.mjs assets/items/female_barbarian_boots/tripo_v1/fitted_v3 left
.venv/bin/python tools/validate-female-barbarian-boots-clearance.py --stride 5
.venv/bin/python tools/validate-female-barbarian-boots-clearance.py --side left --stride 5
.venv/bin/python tools/validate-female-barbarian-boots-clearance.py --motions rest idle1 --output instep-idle-validation.json
blender -b --python-exit-code 1 --python tools/blender-scripts/review_female_barbarian_boots.py
```

현재 끈 관통 검사는 앞끈 문제를 검출하면 실패 종료한다. 피팅 재실행은 검증 기록을 새 후보로 갱신하므로
작업 후 리그 검사와 끈 검사를 다시 실행해야 한다. 임시 포즈 추출·렌더 파일은 재현 후 정리한다.
