# 여성 로그 부츠

현재 프리뷰는 아래 **발목 재리깅 v5**를 사용한다.

[여성 로그 원화](../../client/public/character_concepts/female_rogue.webp)의 검은 허벅지 높이 가죽 부츠를
Tripo 입력용 정면·후면 원화로 옮겼다. 빨간 밑창의 v2를 2026-10-26 Tripo 생성 입력으로 사용했다.

![여성 로그 부츠 정면·후면 원화](../../assets/items/female_rogue_boots/concept_v2/sheet.png)

- 같은 한쪽 부츠를 정면과 후면에서 그렸다. 사용자의 요청에 따라 측면 시점은 포함하지 않는다.
- 몸에 붙는 긴 가죽 몸통, 무릎·발목 주름, 좁은 앞코와 슬림한 굽을 유지했다.
  앞 윗단의 작은 은색 장식은 정면에만 있고, 뒤에는 세로 봉제선이 있다.
- v2에서 사용자 요청에 따라 밑창과 아치 아래 바닥을 빨간색으로 바꿨다. 가죽 몸통과 굽 기둥은 검은색이다.
- 다리·발·마네킹을 넣지 않은 독립 부츠다. 원화에서 부츠 위에 있는 별도 가터와 치마 연결 끈은 제외했다.
- 같은 크기로 정렬한 두 시점을 각각 흰 배경의 1024×1024 입력 이미지로 분리했다.
  이후 3D 생성에는 합본 시트 대신 각 입력 이미지를 사용한다.
  한쪽 부츠 생성 후 반대쪽 대칭 복제와 현재 여성 몸체 피팅은 후속 단계다.

[Tripo 정면 입력](../../assets/items/female_rogue_boots/concept_v2/front.png),
[Tripo 후면 입력](../../assets/items/female_rogue_boots/concept_v2/back.png),
[밑창 색상 수정 프롬프트](../../assets/items/female_rogue_boots/concept_v2/prompt.txt),
[출처·해시·입력 추출 좌표](../../assets/items/female_rogue_boots/concept_v2/sources.json),
[참조 원화 부분](../../assets/items/female_rogue_boots/concept_v1/reference-crop.png).

**[미사용]** [검은 밑창 v1](../../assets/items/female_rogue_boots/concept_v1/sheet.png)은 색상 수정의 원본으로 보관한다.
사용하지 않은 v1 정면·후면 분리본과 중복 검수 렌더는 정리했다. 원본 시트와 추출 좌표는 보존한다.

## Tripo 생성 v1 — 2026-10-26

- 정면과 후면 PNG를 각각 업로드하고 `inputs: [{front: ...}, {back: ...}]`로 전달했다.
  합본 시트와 측면 이미지는 생성 요청에 포함하지 않았다.
- `P2-20260801`, 삼각형 출력, 한쪽 2,000 triangles 목표로 요청했다.
  텍스처는 `v3.5-20260815`, detailed PBR, 입력 조명 제거를 사용했다.
  모델·텍스처 seed는 `102601`이다. 양쪽으로 복제하면 약 4,000 triangles를 배분하는 설정이다.
- 작업 ID: `60a1d01f-d65d-4c7e-8331-e54787dee39c`.
  생성 원본 검수 단계이며 현재 몸체에 대한 피팅·리깅·반대쪽 복제는 후속 단계다.
- 생성은 성공했고 **120크레딧**을 사용했다. 잔액은 1,040 → 920이며 동결 잔액은 0이다.
  결과는 한쪽 2,106 triangles, 대칭 복제 시 4,212 triangles다. 4K base color·normal·ORM 텍스처와 UV가 포함됐다.
- 원본의 빨간 밑창과 검은 굽 기둥을 확대 렌더로 확인했다.
  용접 진단에서 퇴화 면 후보 1개, 경계 변 34개가 기록됐다. 생성 원본은 수정하지 않았으며
  열린 윗단과 작은 은색 장식을 포함한 메시 정리·두께 확인은 피팅 단계에서 진행한다.

[제작 명세·입력 해시](../../assets/items/female_rogue_boots/tripo_v1/build.json),
[요청·작업·비용 기록](../../assets/items/female_rogue_boots/tripo_v1/generation.json),
[Tripo 원본 GLB](../../assets/items/female_rogue_boots/tripo_v1/source/model_url.glb),
[텍스처를 포함한 Blender 원본](../../assets/items/female_rogue_boots/tripo_v1/source.blend),
[메시·UV·텍스처 진단](../../assets/items/female_rogue_boots/tripo_v1/review.json),
[검수 재현 스크립트](../../assets/items/female_rogue_boots/tripo_v1/review_source.py),
[빨간 밑창 확대](../../assets/items/female_rogue_boots/tripo_v1/review/sole.png).

![Tripo 부츠 생성 결과](../../assets/items/female_rogue_boots/tripo_v1/review/angle.png)

## 피팅·리깅 v1 — 2026-10-26

현재 여성 캐릭터 프리뷰의 신발 목록에 **로그 빨간 밑창 가죽 부츠**로 연결했다.
[프리뷰](https://localhost:64297/modular-character-preview.html?character=female&top=rogue&bottom=rogue&boots=rogue&hair=none&camera=full&fit=rogue-boots-v1)에서 상의·치마와 함께 볼 수 있다.

- 현재 여성 몸체 `female-base.glb`를 기준으로 발목·무릎·허벅지 단면을 맞췄다.
  기본 윗단 높이는 기준 좌표에서 약 0.765m다. 오른쪽을 대칭 복제한 뒤 왼쪽 다리에도 따로 여유와 가중치를 맞췄다.
  원본 UV·4K PBR 텍스처와 빨간 밑창은 보존했다. 원본의 퇴화 면 1개씩만 제거해 양쪽 합계는 **4,210 triangles**다.
- 기존 65본 계층·bind 행렬에 연결하고 미터 단위, 오브젝트·런타임 배율 1을 유지한다.
  다리 피부의 가중치를 전사하고 반대쪽 다리 영향은 제거했다. 발·밑창·굽은 Foot에 고정하고
  발목에서 종아리·허벅지 가중치로 부드럽게 이어진다.
- 기존 30도 하이힐 발 자세와 접지 보정을 사용한다. 앉기에서는 `pose_sit_idle` 모프로 윗단이 40mm 내려가
  치마와 간격을 확보한다. 다른 동작에서는 모프가 0이다.
  앉은 손이 가죽에 묻히지 않도록 로그 부츠 착용 시에만 양손을 40mm 올리는 팔 IK도 적용한다.
  부츠를 벗거나 동작을 바꾸면 원래 자세로 복원한다.
- 실제 프리뷰 14개 동작을 각각 61시점에서 검사했다. 동일한 65본 연결·정규화된 네 가중치·유한 변형을 확인했고,
  밑창과 굽의 최대 변 길이 오차는 약 0.0003%다. 발 접지는 기존 동작의 바닥 기준을 유지하며,
  기존 걷기의 약 1.1mm 바닥 편차는 그대로다.
  윗단의 보이는 허벅지 피부에 대한 1mm 초과 관통 샘플은 0개다. 검사 범위와 미세한 접촉 수치는 통합 기록에 남겼다.
- 부츠를 교체할 때 캐시된 부츠의 접지 설정도 함께 전환하도록 프리뷰를 수정했다.
  브라우저에서 대기·걷기·달리기·앉기 각 5시점, 일시정지 중 기사 부츠와의 교체,
  반복 착탈 3회의 가림·발·팔 자세 복원을 확인했다. 페이지 오류와 리소스 로드 실패는 없다.
- 몸체·로그 상의·치마·양쪽 부츠 합계는 숨김 포함 **32,846 triangles**, 가림 적용 후 **25,238 triangles**다.
  머리 가중치가 있는 삼각형 5,057개, 앞 얼굴 추정 3,489개를 유지하며 헤어·무기는 포함하지 않는다.
  편집용 Blender에는 이 조합과 14개 동작의 검수 포즈를 함께 저장했다.

[피팅·리깅 GLB](../../assets/items/female_rogue_boots/tripo_v1/fitted_v1/boots_female_rogue.glb),
[편집용 Blender](../../assets/items/female_rogue_boots/tripo_v1/fitted_v1/female-rogue-boots-fitted.blend),
[피팅·동작·간격·브라우저 검사 통합 기록](../../assets/items/female_rogue_boots/tripo_v1/fitted_v1/fitting.json),
[가림 정보](../../assets/items/female_rogue_boots/tripo_v1/fitted_v1/body-occlusion.json),
[정면 검수](../../assets/items/female_rogue_boots/tripo_v1/fitted_v1/review/detail-front.png),
[측면 검수](../../assets/items/female_rogue_boots/tripo_v1/fitted_v1/review/detail-side.png),
[앉기 검수](../../assets/items/female_rogue_boots/tripo_v1/fitted_v1/review/detail-seated.png),
[빨간 밑창과 굽](../../assets/items/female_rogue_boots/tripo_v1/fitted_v1/review/detail-sole.png).

![로그 의상과 부츠 조합](../../assets/items/female_rogue_boots/tripo_v1/fitted_v1/review/detail-full.png)

```bash
.venv/bin/python tools/fit-female-rogue-boots.py
node tools/validate-female-rogue-boots.mjs assets/items/female_rogue_boots/tripo_v1/fitted_v1
blender -b --python-exit-code 1 -P tools/blender-scripts/review_female_rogue_boots.py
```

## [미사용] 밑창 옆 테두리 검은색 보정 v2 — 2026-10-26

- 사용자의 요청에 따라 옆에서 보이는 얇은 빨간 밑창 테두리를 위쪽 가죽과 같은 검은색으로 바꿨다.
  밑에서 보이는 바닥·아치·굽 끝은 기존 빨간색을 유지한다. v3는 여기에 굽 안쪽 면의 빨간색을 추가했다.
- 기준 발 자세에서 아래를 향한 면과 옆면을 구분했다. 한쪽 335개 테두리 면의 색상·ORM만
  기존 검은 가죽 영역에서 가져온다. 밑면 90개 면의 색상 좌표와 원본 PBR 이미지 바이트는 보존했다.
  새 텍스처 생성이나 유료 요청은 없다.
- 색상 경계에서 정점 296개씩을 복제하고 두 번째 UV 채널을 추가했다.
  모든 삼각형의 위치·방향, 노멀·기존 UV·가중치·앉기 모프는 원본 정점과 정확히 같다.
  양쪽 합계 4,210 triangles, 65본 리그, 접지·하이힐·앉기 손 보정 설정, 몸체 가림 인덱스도 유지했다.
- 실제 런타임의 14개 동작을 각각 61시점에서 재검사했다.
  브라우저에서 옆면과 바닥 색상을 확인하고 대기·걷기·달리기·앉기 각 5시점,
  신발 교체와 반복 착탈 시 가림·동작 상태 복원을 확인했다. 페이지 오류·리소스 실패는 0개다.
  조합은 숨김 포함 32,846 triangles, 가림 적용 후 25,238 triangles이며 머리·얼굴 배분은 v1과 같다.

v2 중간 GLB·Blender·가림·접지 파일은 v3 확정 후 삭제했다. 검사 기록과 문서 이미지는 보존한다.

[색상·동작 검사 기록](../../assets/items/female_rogue_boots/tripo_v1/fitted_v2/fitting.json),
[빨간 밑면 검수](../../assets/items/female_rogue_boots/tripo_v1/fitted_v2/review/underside.png).

![검은 밑창 옆 테두리](../../assets/items/female_rogue_boots/tripo_v1/fitted_v2/review/side.png)

```bash
.venv/bin/python tools/recolor-female-rogue-boot-rim.py
node tools/validate-female-rogue-boots.mjs assets/items/female_rogue_boots/tripo_v1/fitted_v2
blender -b --python-exit-code 1 -P tools/blender-scripts/sync_female_rogue_boot_rim.py
```

## 굽 안쪽 면 빨간색 보정 v3 — 2026-10-26

- 굽 기둥에서 앞코와 아치를 향하는 안쪽 면을 빨간색으로 맞췄다.
  각 부츠의 안쪽 면 24개만 기존 빨간 밑창 영역을 사용하며, 굽 옆면·뒷면은 검은색이다.
  이 색상 보정 결과는 현재 발목 재리깅 v5에도 유지한다.
- v2와 삼각형 모서리별로 비교해 안쪽 면 밖의 색상·ORM 좌표가 정확히 같음을 확인했다.
  빨간 바닥·아치·굽 끝과 검은 밑창 테두리를 유지한다. 형상·노멀·스킨 가중치·앉기 모프,
  원본 PBR 이미지와 기존 4,210 triangles, 몸체 가림·접지 설정도 유지했다. 새 생성 요청은 없다.
- 14개 동작 각각 61시점의 기존 런타임 검사를 통과했다.
  실제 프리뷰에서 아래·옆·뒤 시점을 확인했고 페이지 오류·리소스 실패는 0개다.
  조합 삼각형 수와 머리·얼굴 배분은 v2와 같다.

[v3 GLB](../../assets/items/female_rogue_boots/tripo_v1/fitted_v3/boots_female_rogue.glb),
[편집용 Blender](../../assets/items/female_rogue_boots/tripo_v1/fitted_v3/female-rogue-boots-fitted.blend),
[색상·검사 기록](../../assets/items/female_rogue_boots/tripo_v1/fitted_v3/fitting.json),
[검은 밑창 옆면](../../assets/items/female_rogue_boots/tripo_v1/fitted_v3/review/side.png),
[검은 굽 뒷면](../../assets/items/female_rogue_boots/tripo_v1/fitted_v3/review/back.png).

![빨간 굽 안쪽 면과 밑창](../../assets/items/female_rogue_boots/tripo_v1/fitted_v3/review/underside.png)

```bash
.venv/bin/python tools/recolor-female-rogue-boot-rim.py --red-inner-heel
node tools/validate-female-rogue-boots.mjs
blender -b --python-exit-code 1 -P tools/blender-scripts/sync_female_rogue_boot_rim.py -- assets/items/female_rogue_boots/tripo_v1/fitted_v3
```

## 이전 발목 보정 v4 — [미사용]

2026-10-26. 발목 둘레를 늘리고 Foot/Leg 전환을 넓혀 단면적을 보완했으나,
사용자 검수에서 발목 위가 계속 접히는 문제가 확인됐다. 단면적 증가와 기존 유한 변형 검사는
관절이 잘못된 구간에서 휘는 문제를 검출하지 못했다. 이 버전은 프리뷰에서 제외했다.

## 발목 재리깅 v5 — 2026-10-26

발목 위 종아리까지 Foot 가중치를 강제로 넣은 것이 원인이었다.
발목 관절을 회전시킬 때 원래 종아리 방향을 유지해야 할 구간까지 함께 당겨져
발목 위가 꺾였다. v4의 두께 보정은 이를 해결하지 못했다.

- v3의 하이힐 착용 형태를 기준으로 여성 몸체의 실제 발목 피부에서 가중치를 다시 옮겼다.
  발등의 단단한 부분과 밑창·굽은 Foot을 따르고, 발목 위 종아리는 Leg를 따른다.
  높이 170–270mm의 종아리에 남은 Foot 가중치는 0이다.
- 본 위치·계층·65본 inverse bind와 30도 하이힐 보정은 일치했다. 이 값을 바꾸지 않고
  새 가중치에 맞춰 메시와 노멀을 공통 bind로 역변환했다.
  기준 하이힐 착용 자세의 형태는 기존 v3와 0.002mm 이내로 일치하며, 셰이더 노멀 방향도 유지한다.
- 밑창·굽과 위쪽 부츠 몸통, 기존 UV·PBR 이미지·앉기 윗단 모프를 보존했다.
  삼각형은 양쪽 합계 4,210개이며 조립 캐릭터의 이전 삼각형 예산은 변하지 않는다.
- 발 본만 ±30도·±60도 돌리는 검사를 추가했다. 기존 v3는 종아리 정점이 최대 약 9.7mm 움직였으나,
  v5의 같은 구간은 움직이지 않는다. 실제 런타임 14개 동작 × 61시점도 검사한다.
  걷기·달리기의 발목 단면은 자기 기준 착용 자세의 97% 이상을 유지해야 한다.
- 가죽 변 길이는 실제 하이힐 착용 자세를 기준으로 비교한다. 역바인딩한 맨발 bind에서
  압축된 변 길이를 분모로 쓰면 착용 자세의 정상적인 복원이 과도한 늘어남으로 집계될 수 있었다.
  65본 bind 일치, 가중치 정규화, 굽·밑창 강체 길이, 반복 자세 복원 검사는 별도로 유지한다.
- 출처는 위 Tripo v1과 여성 공통 몸체를 그대로 따른다. 신규 AI 생성·유료 요청은 없다.

[현재 GLB](../../assets/items/female_rogue_boots/tripo_v1/fitted_v5/boots_female_rogue.glb),
[Blender 편집본](../../assets/items/female_rogue_boots/tripo_v1/fitted_v5/female-rogue-boots-fitted.blend),
[재리깅 기록](../../assets/items/female_rogue_boots/tripo_v1/fitted_v5/fitting.json),
[발목 검사](../../assets/items/female_rogue_boots/tripo_v1/fitted_v5/ankle-validation.json),
[동작 검사](../../assets/items/female_rogue_boots/tripo_v1/fitted_v5/runtime-validation.json),
[브라우저 검사](../../assets/items/female_rogue_boots/tripo_v1/fitted_v5/browser-validation.json).

![발목 재리깅 후 걷기](../../assets/items/female_rogue_boots/tripo_v1/fitted_v5/review/walk-after.png)

```bash
.venv/bin/python tools/rerig-female-rogue-boot-ankles.py
node tools/validate-female-rogue-boots.mjs
.venv/bin/python tools/validate-female-rogue-boot-ankles.py
blender -b --python-exit-code 1 -P tools/blender-scripts/sync_female_rogue_boot_rim.py -- assets/items/female_rogue_boots/tripo_v1/fitted_v5
```

## 걷기 각도 보정 철회 — 2026-10-27

앞꿈치의 기준 각도를 보정하고 회전 범위를 제한한 시도는 사용자 검수에서 더 부자연스럽다고 판단됐다.
추가한 걷기·횃불 걷기 각도 보정과 클립 제작·Blender 자세 변경을 되돌렸다.
현재 프리뷰는 발목 재리깅 v5와 그 직후의 원래 걷기 회전을 사용한다.

커밋 전 실패한 v4의 GLB·Blender·중복 검사 출력과 폐기한 걷기 각도의 비교 이미지를 삭제했다.
최종 v5와 문서용 착용 이미지, 원본·출처 기록을 보존한다.
v3 GLB는 재리깅 입력이며, v1 Blender는 최종 편집 장면을 재현하는 입력이므로 유지한다.
