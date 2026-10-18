# 여성 바바리안 하의 — 2026-10-15

2026-10-17: 하의 GLB와 `fit-data.npz`(`fitted`·`depth`)의 좌표를 미터로 바꿨다. 모피 4판의 `pelt_physics`는 미터 값과
`unit: 1.8`(pelt-rig 내장 거리·힘을 튜닝 당시 크기로 유지)을 원본에 담고, 게임용 `robe_physics`는 전과 같다.
수리 단계 폴더(`belt_*`, `panel_*` 등)와 그 도구는 제작 단위로 남는 보관용이다. 아래 높이 값은 당시 제작 단위다.
[전환 기록](female-knight-runtime.md#원본-미터-단위-전환--2026-10-17).

[여성 바바리안 원화](../../client/public/character_concepts/female_barbarian.webp)의 하의를
모듈형 파츠용 앞뒤 원화로 옮기고 Tripo로 3D 원본을 생성해 여성 기준 몸체에 피팅했다.
여성 미리보기에 연결했으며 장비 등록은 아직 하지 않았다.

![여성 바바리안 하의 원화](../../assets/items/female_barbarian_bottom/concept_v1/sheet.png)

## 출처

- 원화: OpenAI Codex built-in ImageGen(`codex exec`, codex-cli 0.162.1), **ChatGPT Pro 20x**, 2026-10-15.
  OpenAI 출력물 이용 조건을 따른다. 참조 원화의 출처는 [캐릭터 문서](characters.md)에 있다.
- 참조 입력은 원본을 흰 바탕에 합성해 `[290,560,440,380]`을 FFmpeg로 자른
  [reference-crop.png](../../assets/items/female_barbarian_bottom/concept_v1/reference-crop.png)이다.
- [앞뒤 원화](../../assets/items/female_barbarian_bottom/concept_v1/sheet.png),
  [앞면](../../assets/items/female_barbarian_bottom/concept_v1/front.png),
  [뒷면](../../assets/items/female_barbarian_bottom/concept_v1/back.png),
  [프롬프트](../../assets/items/female_barbarian_bottom/concept_v1/prompt.txt),
  [출처·해시](../../assets/items/female_barbarian_bottom/concept_v1/sources.json).
- Tripo 입력용 앞·뒷면은 원화를 열 780에서 나눠 각자 반쪽만 쓰고(라벨 행 제외), 같은 배율·높이로 870×870 정사각형 가운데에 놓았다.
  원화 밖으로 나간 여백은 가장자리 배경 픽셀을 반복해 채웠다. 앞면 오른쪽 여백이 13px뿐이라 그대로 자르지 않았다.
- Codex 샌드박스가 셸을 띄우지 못해 `~/.codex/generated_images/`의 출력 PNG를 그대로 `sheet.png`로 복사했다.

## 범위

- 하의: 철판·리벳을 덧댄 갈색 가죽 허리띠, 앞 가운데 매듭 무늬 원형 버클, 양옆 쇠고리·가죽 고리,
  뾰족한 판 여러 장으로 된 짧은 모피 치마, 앞 가운데 판의 땋은 가죽끈. 뒤는 같은 허리띠와 리벳 띠 고리, 엉덩이를 덮는 모피 판.
- 제외: 속옷(기본 몸체에 있음), 샌들·발목 보호대(신발 슬롯).

## Tripo 생성

- Tripo API 유료 크레딧, 모델 `P2-20260801`, 텍스처 `v3.5-20260815`, detailed PBR,
  입력 조명 제거, 삼각형 목표 4,000, seed 101501. [API 문서](https://developers.tripo3d.ai/en/docs/generation-multiview-to-model/p),
  [이용 조건](https://developers.tripo3d.ai/en/terms).
- 입력은 위 앞·뒷면 정사각형 두 장이다.
- 작업 ID `b323b163-bc48-4cf7-9e66-917a8ff30854`, **120크레딧 사용**, 잔액 800 → 680.
- [제작 명세](../../assets/items/female_barbarian_bottom/tripo_v1/build.json),
  [요청·비용·작업 기록](../../assets/items/female_barbarian_bottom/tripo_v1/generation.json).
  재제출하지 않고 `tools/outfits/tripo.py`로 기존 작업을 조회·회수한다.

| 용도 | 파일 |
| --- | --- |
| Tripo 원본 | [model_url.glb](../../assets/items/female_barbarian_bottom/tripo_v1/source/model_url.glb) |
| Tripo 렌더 | [rendered_image_url.png](../../assets/items/female_barbarian_bottom/tripo_v1/source/rendered_image_url.png) |
| 원본 Blender | [source.blend](../../assets/items/female_barbarian_bottom/tripo_v1/source.blend) |
| 원본 진단 | [review.json](../../assets/items/female_barbarian_bottom/tripo_v1/review.json), [재현 스크립트](../../assets/items/female_barbarian_bottom/tripo_v1/review_source.py) |

원본은 메시 1개, **3,241 triangles**, 4K 컬러·노멀·ORM 텍스처다.
연결 성분 15개, 경계선 842개, 퇴화 면·UV 붕괴 0개다.
모피 판은 두께 없는 한 겹 면이라 뒤에서 보면 앞 가운데 판의 안쪽 면이 비친다.
옆에서 보면 앞 가운데 판의 땋은 끈이 판에서 떨어져 앞으로 늘어져 있다. 피팅 때 판에 붙이거나 다듬는다.

## 피팅 v1 — 2026-10-15

기준 몸체 `assets/modular_human_female_01/rig_v1/female-base.glb`, 리그 `human_female_01_local_v1` 65본.
몸체·동작은 변경하지 않았다. 현재 삼각형 3,340개(원본 3,241 + 구멍 메움 15 + 벨트 연결 84)다.
원래 면의 UV와 텍스처는 유지하고, 추가 연결 면은 기존 갈색 안감 영역을 사용한다. 텍스처는 WebP q90으로 내보냈다.

- 정렬: 배율 0.25, Z −90°. 허리띠 중심을 높이 0.595, 그 높이 몸 단면의 앞뒤 가운데에 맞췄다.
  0.585에서는 뒤에서 팬티 허리선이 허리띠 위로 보였다.
- 부위: 본체 중 원본 높이 0.23 위를 허리띠, 아래를 모피로 나눴다. 따로 떨어진 조각은 땋은 끈, 원형 버클,
  고리·가죽 고리 10개, 모피 판으로 분류했다.
- Tripo가 0.001(원본 단위) 안에 띄워 둔 이음 정점을 피팅 전에 합쳤다. 그대로 두면 앞 가운데 판에 가로 틈이 벌어졌다.
- 허리띠: 안쪽 면을 피부와 팬티에서 4mm로 당기고, 바깥 두께는 ARAP로 유지했다.
- 버클·고리: 주변 허리띠를 따라 강체로 옮기고 피부 밖 6mm까지 밀었다.
- 모피: 허리띠를 따라 ARAP로 매단 뒤 허벅지에 붙은 판을 바깥으로 밀었다. 높이·둘레 각도 격자에서 부족한 간격을
  구하고, 위에서 아래로 최댓값을 내려 보내(늘어뜨림) 흐린 뒤 반복 적용했다. 겹친 판이 함께 움직여 순서가 유지된다.
  정점마다 따로 밀면 겹친 판이 서로 엇갈려 접혔다.
- 구멍 메움: Tripo 원본의 닫힌 작은 구멍 중 허리띠·모피로만 둘러싸인 것(16변 이하, 둘레 12cm 미만)을 기존 정점으로 삼각형화했다.
  뒤 허리띠 아래 V자 틈(흰 팬티가 보이던 곳)과 앞 모피 판 구멍이다. 고리·가죽 고리의 구멍은 원래 뚫린 것이라 두었다.
  메운 면은 2cm 아래 모피 면의 UV를 빌려 갈색 모피로 보이고, 몸 바깥을 향하도록 면마다 방향을 맞췄다.
- 땋은 끈: 원본에서 판 앞으로 떨어져 있어 높이 4mm 조각마다 앞 판 표면 1mm 앞으로 붙였다.
- 휴지 자세 관통 0, 최소 간격 1mm.
- 웨이트: 피부에서 역거리로 옮긴 뒤 모피·끈의 다리 비중을 허리띠 아래로 내려갈수록 최대 0.8까지만 허용하고 나머지는 Hips에 줬다.
  허리띠는 피부 웨이트를 그대로 쓴다(평균 Hips 0.52, 양 UpLeg 0.21·0.23). 처음에 허리띠를 골반에만 묶었더니
  대기에서도 엉덩이 피부가 허리띠를 뚫었다. 버클·고리는 주변 허리띠에서 가장 큰 본 하나에 강체로 묶었다(버클 Hips, 옆 고리 UpLeg).
  여러 본을 섞으면 걷기에서 고리가 4% 휘었다. 땋은 끈은 바로 뒤 모피 정점의 웨이트를 복사한다.
- 가림: 허리띠가 1.2cm 안에서 덮고 가장자리에서 1cm 이상 안쪽인 피부와 팬티를 숨기고, 높이 0.585m 위 팬티 윗단도 가린다.
  현재 피부 224면·팬티 408면을 숨긴다(아래 전투 대기 골반 비침 보정 포함).
  나머지 팬티는 모피 틈으로 보이므로 그대로 둔다.

### 검증

초기 피부 웨이트 전사는 다리를 벌릴 때 앞 판을 좌우로 늘리고 옆 판을 허벅지 안으로 끌어들였다.
큰 동작의 모피 관통도 있었다. 현재 판별 굽힘·충돌 검증은 아래 마지막 보정 항목과
[동작 검사](modular-female-barbarian-bottom-animation-v1.json)에 기록한다.

### 뒤 벨트 안쪽 면 보정 v2 — 2026-10-15

뒤 가운데의 검은 삼각형과 테두리 깜박임은 안쪽 가죽 면이 바깥 철판 면을 뚫거나 거의 맞닿아서 생겼다.
실제 미리보기의 같은 화면 점에서 두 면의 깊이 차이가 0.07~0.20mm였으며 안쪽 면이 더 앞에 있었다.
뒤 벨트 안쪽 34면의 정점과 같은 위치의 UV 이음 정점까지 140개를 골반 쪽으로 2mm 옮겼다.
3,256 triangles, 4,796 vertices. UV·노멀·탄젠트·본·웨이트·인덱스와 컬러·노멀·ORM 이미지 바이트는 원본 그대로다.
가림 정보를 다시 계산했고 여성 몸체에 착용한 뒤·뒤 사선 렌더와 `bindModularPart`의 9동작 검증을 완료했다.

실제 미리보기 페이지를 Chromium에서 열어 뒤 확대와 9개 뒤 사선 각도를 확인했다. 철판 구간(x ±6cm, 높이 0.590~0.601m)의
1,288개 광선에서 안쪽 면은 철판보다 최소 1.54mm 뒤에 있다. 휴지 자세 연속 8프레임의 캔버스 이미지가 일치했고 브라우저 오류는 없다.

- [수정 전 모델](../../assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/belt_repair_v1/before.glb),
  [보정 기록](../../assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/belt_repair_v2/repair.json),
  [재현 스크립트](../../tools/fix-female-barbarian-belt.py).
- [몸체 표면 간격](../../assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/belt_repair_v2/rest-clearance.json).
- 기존 Tripo 텍스처를 재사용했으며 새 생성 요청·비용은 없다.

**[미사용] UV 보정 v1:** 두 면의 텍스처 좌표만 바꾼 첫 수정은 Blender 렌더에서 개선돼 보였으나 실제 미리보기에서
검은 부분과 깜박임이 남았다. 위 안쪽 면 보정으로 대체하고 UV는 원본으로 복원했다.
실패한 모델·비교 렌더·디버그 스크립트는 정리했다.

### 흰 속옷 허리선 가림 — 2026-10-15

![위에서 본 수정 후 허리선](../../assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/waistband_repair_v1/after/angle.png)

속옷 메시 윗단을 숨겨도 몸체 텍스처의 흰 띠가 벨트 안쪽 틈에서 보였다. 벨트 높이 0.602~0.611m 구간의
424정점을 부드럽게 올려 윗선을 최대 4mm 높였고, 뒤 안쪽 윗면은 최대 1.5mm 더 안으로 옮겨 철판과의 겹침을 막았다.
치마 착용 시에만 별도 속옷 메시의 높이 0.585m 위 윗단을 가린다. 벗으면 원래 몸체 인덱스로 복원한다.
몸체·텍스처·UV·웨이트·장비 면 수는 변경하지 않았다. 같은 Tripo 원본을 재사용했으며 추가 생성 비용은 없다.

실제 미리보기에서 위에서 본 뒤·뒤 사선 화면을 확인했다. 철판 구간 1,288개 광선의 안쪽 면 간격은 최소 0.84mm이며,
휴지 자세 8프레임은 일치한다. 몸체 표면 관통 0, 최소 간격 1mm를 유지한다. 9동작 결합 검증을 다시 실행했다.

- [보정 기록](../../assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/waistband_repair_v1/repair.json),
  [재현용 입력 모델](../../assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/waistband_repair_v1/before.glb).
- [몸체 간격 검증](../../assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/waistband_repair_v1/rest-clearance.json),
  [재현 스크립트](../../tools/fit-female-barbarian-waistband.py).

### 전투 대기에서 모피 판 변형 보정 — 2026-10-15

허리띠·버클·고리, 앞 판과 땋은 끈, 뒤 판, 왼쪽 판, 오른쪽 판을 5개 스킨 메시로 나눴다.
삼각형 3,256개, 내보낸 정점 4,845개(경계 복제 49개), 각 메시의 여성 리그는 동일한 65본이다.
원본 면의 위치·UV·텍스처는 유지했다. 원래 허리띠로 분류됐지만 실제 높이가 0.575m 아래인 연결부도 모피 판에 포함해 이음이 벌어지지 않게 했다.

기존 `pelt_physics`의 굽힘·허벅지 충돌을 모피 4판에 연결했다. 판은 골반에 매달고,
허벅지를 크게 벌리면 접히며 바깥으로 올라간다. 고정된 웨이트만 바꾸거나 휴지 자세의 판을 돌리는 시도는
들림·관통 또는 기본 모양의 변화를 만들어 채택하지 않았다. 위쪽 2.5cm는 원래 피부 웨이트를 유지해 허리띠 연결을 보존한다.
여성 미리보기에도 같은 물리 갱신·동작 전환/시점 조정 시 초기화·해제 시 정리를 연결했다.

9동작 × 17시점에서 원본 모델과 같은 허벅지 충돌체로 비교했다. 전투 대기의 앞 판 폭은 기준 대비
**1.52배 → 1.00배**, 충돌체 안쪽 옆 판 정점은 **594 → 6개**로 줄었다. 대기·걷기의 옆 판 충돌체 겹침은 0개다.
달리기·점프·앉기 등 큰 동작에는 일부 겹침이 남는다. 충돌체는 실제 몸체를 근사하므로 전체 삼각형 관통 검사와는 다르다.
본 결합, 웨이트 정규화, 유한 변형과 물리 해제 시 원래 지오메트리 복원을 검증했다.
클라이언트 check/lint와 모피·로브·모듈 결합 테스트 54개를 통과했다.

- [제작 기록](../../assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/panel_weights_v1/repair.json),
  [재현용 입력](../../assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/panel_weights_v1/before.glb),
  [재현 스크립트](../../tools/weight-female-barbarian-panels.py).
- 원래 Tripo 결과를 재사용했으며 새 이미지·3D 생성 요청과 비용은 없다.

### 벨트 윗선 정리 — 2026-10-15

원본 벨트 옆 철판의 솟은 꼭짓점과 가죽 윗단을 높이 0.615m에 가까워지는 부드러운 곡선으로 눌렀다.
0.607m 아래는 유지하고 위쪽 348정점만 최대 13.38mm 낮췄다. 낮아진 허리 단면이 넓어지는 만큼
가로 반경도 보정해 수정 부위의 최소 방사 간격 2.74mm를 유지했다. 노멀은 변형된 면을 따라 회전했다.
버클·고리·모피 판의 형상, 모든 UV·텍스처·본·웨이트·물리 설정은 유지한다.

앞 오른쪽 철판의 V자 패임은 표시된 양 끝을 잇는 기울기를 따라 모서리만 올렸다.
윗단의 세 모서리와 짝을 이루는 두께 면 17정점만 추가로 최대 9.76mm 올렸다.
양 끝점과 나머지 모든 정점 위치는 앞 보정 상태 그대로다. 판 전체를 넓게 펴는 방식은 되돌렸다.

대기·기본 자세의 사선·앞·뒤·옆과 전투 대기를 브라우저에서 확인했다. 9동작 × 17시점 검증도 통과했다.
가림 정보를 다시 계산했고 뒤쪽 흰 속옷이 윗단으로 보이지 않는 것을 확인했다.

- [제작 기록](../../assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/belt_rim_repair_v1/repair.json),
  [재현용 입력](../../assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/belt_rim_repair_v1/before.glb),
  [재현 스크립트](../../tools/smooth-female-barbarian-belt.py).
- 기존 Tripo 원본을 재사용했으며 새 생성 요청과 비용은 없다.

### 허리띠 아래 모피 이음 연결 — 2026-10-15

허리띠와 모피를 나눈 경계가 물리 처리에서 서로 달리 움직여 가로 틈이 열렸다.
원래 같은 위치인 경계 55곳의 모피 정점 97개(앞 35, 뒤 10, 왼쪽 21, 오른쪽 31)를 명시적으로 연결했다.
위쪽 원래 피부 웨이트로 계산한 위치를 매 프레임 모피의 골반 좌표계로 옮겨 부착점으로 사용한다.
길이·접촉 제약에서도 부착점을 유지하며, 고정점이 있는 모피는 강체 회전 결과로 다시 섞지 않는다.

정점 위치·면·UV·텍스처·노멀·본·웨이트 원본은 유지했다. 모피끼리 만나는 아래쪽 경계까지 고정한 시도는
전투 자세에서 판을 당겨 채택하지 않았고, 허리띠와 모피가 만나는 위아래 이음만 연결했다.
9동작 × 17시점에서 모든 연결 경계의 최대 간격이 0.001mm 미만임을 확인했다.
앞 판 폭과 모피 충돌 검사도 유지했으며 클라이언트 check/lint와 관련 테스트 56개가 통과했다.

- [제작 기록](../../assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/panel_seam_repair_v1/repair.json),
  [재현용 입력](../../assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/panel_seam_repair_v1/before.glb),
  [재현 스크립트](../../tools/stitch-female-barbarian-panels.py).
- 기존 Tripo 결과를 재사용했으며 새 생성 요청과 비용은 없다.

### 앞 골반의 피부 비침 가림 — 2026-10-15

대기 동작에서 오른쪽 앞 골반의 피부 조각이 위쪽 모피보다 앞으로 비쳤다.
해당 피부 4면(1912, 1916, 1919, 11823)만 하의 착용 중 가리는 목록에 추가했다.
원본 몸체와 의상 형상은 유지하며 하의를 벗으면 전체 몸체 인덱스가 복원된다.

기본 자세와 대기·걷기·전투 대기의 5시점을 브라우저에서 확인했다.
문제 위치의 8개 광선이 피부 대신 의상을 먼저 맞히고, 하의를 벗으면 원래 20,799면이 복원되는 것을 검증했다.

- [가림 명세](../../assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/body-occlusion.json),
  [재현 스크립트](../../tools/outfits/female_barbarian_bottom_occlusion.py).

### 전투 대기 옆천의 허벅지 겹침 보정 — 2026-10-15

허벅지 충돌체의 앞뒤 반경을 57mm에서 72mm로 늘리고, 골반 바로 아래에
허벅지 본을 따르는 반경 50 × 85 × 65mm의 충돌체를 추가했다.
전투 대기에서 옆천이 피부 뒤로 사라지는 대신 허벅지 바깥으로 접히는 것을 양쪽 사선에서 확인했다.
모든 정점·면·UV·텍스처·본·웨이트와 기존 허리 부착점은 유지했다. 몸체 가림 목록도 늘리지 않았다.
메시 세분화와 길이 제약 뒤 강제 접촉을 추가한 시도는 큰 동작의 늘어남을 키워 제외했다.

실제 몸체를 사용한 전투 대기 3시점의 측면 광선 검사에서, 위쪽 앞 옆천의 가려진 면 중심은
왼쪽 25개에서 2개로, 오른쪽 9개에서 0개로 줄었다. 왼쪽 뿌리의 2개 표본은 남아 있으며,
이는 전체 표면의 무관통을 보장하는 검사가 아니다. 9동작 × 17시점의 앞천 폭·허리 이음·리그 검사와
클라이언트 check/lint, 관련 테스트 56개를 통과했다. 큰 동작의 겹침과 국소 늘어남은 남는다.

- [제작 기록](../../assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/thigh_contact_v1/repair.json),
  [재현 스크립트](../../tools/fit-female-barbarian-thigh-contact.py),
  [측면 검사](modular-female-barbarian-thigh-contact-v1.json).
- 기존 Tripo 결과를 재사용했으며 새 생성 요청과 비용은 없다.

### 전투 대기 양옆 골반의 피부 비침 가림 — 2026-10-15

전투 대기에서 벨트 양옆 아래로 튀어나오는 피부 37면을 하의 착용 중 가리는 목록에 추가했다.
가려진 앞면 뒤에서 다시 보이던 같은 골반의 피부도 포함한다. 원본 몸체와 의상 형상·물리 설정은 유지한다.
가림 면의 원래 인덱스 서명을 검사해 다른 몸체에 잘못 적용되지 않도록 했다.

기본 자세와 대기·걷기·전투 대기 5시점씩을 브라우저에서 확인했다.
문제 부위의 34개 대표 광선에서 피부가 먼저 보이지 않으며, 하의를 벗으면 원래 몸체 인덱스 62,397개가 복원된다.
총 피부 224면·팬티 408면을 가리고 21,543면을 표시한다. 기존 Tripo 원본을 재사용했으며 새 생성 비용은 없다.

- [제작·검증 기록](../../assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/combat_skin_clearance_v1/repair.json),
  [재현 스크립트](../../tools/outfits/female_barbarian_bottom_occlusion.py).

### 벨트와 모피 윗단 연결 — 2026-10-15

전투 대기에서 벌어진 윗단 경계 42곳에 연결 면 84개를 추가했다.
새 윗단은 벨트 바깥면의 본·웨이트를 따라가고, 아래쪽은 모피의 기존 경계에 연결된다.
긴 경계는 높이 0.548m에서 잘라 벨트 아래에 필요한 범위만 메우고, 앞 안감에는 방사 방향 6mm 여유를 뒀다.
추가 면은 기존 갈색 안감 텍셀을 사용한다. 원래 정점·면·UV·텍스처·리그와 몸체 가림 목록은 유지했다.
총 삼각형 3,340개·정점 4,999개다.

연결 면의 길이 제약이 기존 모피를 당기지 않도록 `bend.constraint_triangles`로 원래 면만 길이 제약에 사용한다.
기본 자세·대기와 전투 대기 5시점을 브라우저에서 확인했고, 표시된 틈의 8개 광선 모두 의상을 먼저 맞힌다.
9동작 × 17시점에서 벨트와 일치하는 68개 부착 경계의 최대 틈은 0.001mm 미만이다.
앞천 폭과 원래 모피 변형 수치를 유지했고, check/lint 및 관련 테스트 57개를 통과했다.

- [제작 기록](../../assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/belt_fur_join_v1/repair.json),
  [재현 스크립트](../../tools/join-female-barbarian-belt.py).
- 기존 Tripo 원본을 재사용했으며 새 생성 요청과 비용은 없다.

### 게임 내 모피 판을 로브 리그로 전환 — 2026-10-16

여러 캐릭터가 함께 있을 때의 비용을 줄이려고 게임에서는 모피 4판을 정점 단위 굽힘·충돌 대신 기존 로브 리그로 움직인다.
`tools/prepare-female-knight.mjs`가 패키징할 때 각 판의 `pelt_physics`에서 `robe_physics`를 만든다.
4판은 허리 높이·중심·반경을 하나로 공유하므로 캐릭터당 확장 스켈레톤 1개와 제어 본 6개만 쓴다.
앞·뒤 가운데 제어 본은 두 다리 중 더 앞으로 나온 쪽을 따른다. 좌우가 따로 움직이면 가운데 선에서
판이 찢어졌다(달리기·베기 모서리 최대 35배).

각 열은 허벅지 축을 그대로 따르지 않고, 열의 실제 밑단 방향이 모피 판의 허벅지 충돌체(6개)를
벗어날 때까지만 든다. 그 각도의 70%만 쓰고, 휴지 자세에서 이미 닿아 있는 만큼은 허용한다.
다리가 빠르게 움직이면(초당 3rad에서 최대) 허벅지 방향도 따라가 달릴 때 흔들림을 살린다. 최대 1.35rad.
앞 판은 가운데 열 하나로만 움직인다. 옆 열과 섞이면 달릴 때 폭이 1.4배로 벌어졌다(지금 1.00배).
벨트 고정 정점 근처는 원래 피부 웨이트를, 멀어질수록 골반 웨이트를 섞어 벨트 아래 틈이 벌어지지 않게 했다.
브라우저 미리보기에서 모피 굽힘 결과와 비교해 값을 정했다. 정지 자세의 정점 위치 평균 차이는 6.7cm → 4.0cm,
달리기 밑단 속도는 이전 로브와 같은 초당 약 32cm다(모피 굽힘은 13cm).

`validate-female-barbarian-bottom.mjs`는 원본 피팅 GLB로 결합·웨이트·휴지 형상을 확인하고,
패키징된 GLB로 실제 로브 경로의 이음 간격·모서리 늘어남·해제 복원을 검사한다.
허벅지 충돌 검사(`validate-female-barbarian-thigh-contact.mjs`)는 모피 굽힘 전용이라 삭제했다.

- 큰 동작에서 허벅지가 모피 판 앞으로 조금 지나가고, 달리기·앉기에서 옆 판이 비스듬히 벌어진다. 늘어남은 쓰러짐 최대 5.2배다.

- 공유 허리 높이는 4판 피벗 중 가장 높은 값이다. 앞·뒤 판은 회전 축이 약 2.6cm 올라간다.
- 10명 기준 CPU 물리 시간과 재현 명령은 [성능 기록](modular-female-barbarian-performance.json)에 있다.

### 남은 문제

- 기본 몸체 피부에 하의 속옷이 구워져 있어 팬티 메시를 숨겨도 같은 흰색이 보인다. 그래서 틈은 메워서 막았다.
- 뒤 허리띠의 가죽 이음 무늬는 원본 그대로다. 철판 위 검은 삼각형과 안쪽 면의 겹침은 위 형상 보정으로 수정했다.
- 앞 가운데 판 끝은 무릎 위 약 5cm다. 원화보다 조금 길다.
- 큰 동작의 모피 관통과 일부 이음 변형(동작 검사 참조).

| 용도 | 파일 |
| --- | --- |
| 하의 | [bottom_female_barbarian.glb](../../assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/bottom_female_barbarian.glb) |
| 가림 명세 | [body-occlusion.json](../../assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/body-occlusion.json) |
| 피팅 기록 | [modular-female-barbarian-bottom-fitting-v1.json](modular-female-barbarian-bottom-fitting-v1.json) |
| 동작 검사 | [modular-female-barbarian-bottom-animation-v1.json](modular-female-barbarian-bottom-animation-v1.json) |
| 성능 기록 | [modular-female-barbarian-performance.json](modular-female-barbarian-performance.json) |

### 미리보기

개발 서버의 `/modular-character-preview.html?character=female&camera=lower&bottom=barbarian`에서 연다.

### 재현

```bash
blender -b --python-exit-code 1 -P tools/blender-scripts/fit_female_barbarian_bottom.py
.venv/bin/python tools/rig-female-knight-top-v2.py assets/items/female_barbarian_bottom/tripo_v1/fitted_v1 bottom_female_barbarian doc/assets/modular-female-barbarian-bottom-fitting-v1.json 1
.venv/bin/python tools/fix-female-barbarian-belt.py assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/bottom_female_barbarian.glb
.venv/bin/python tools/fit-female-barbarian-waistband.py assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/bottom_female_barbarian.glb
.venv/bin/python tools/weight-female-barbarian-panels.py assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/bottom_female_barbarian.glb
cp assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/bottom_female_barbarian.glb assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/belt_rim_repair_v1/before.glb
.venv/bin/python tools/smooth-female-barbarian-belt.py
cp assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/bottom_female_barbarian.glb assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/panel_seam_repair_v1/before.glb
.venv/bin/python tools/stitch-female-barbarian-panels.py
cp assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/bottom_female_barbarian.glb assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/thigh_contact_v1/before.glb
.venv/bin/python tools/fit-female-barbarian-thigh-contact.py
cp assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/bottom_female_barbarian.glb assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/belt_fur_join_v1/before.glb
.venv/bin/python tools/join-female-barbarian-belt.py
.venv/bin/python tools/outfits/female_barbarian_bottom_occlusion.py
node tools/prepare-female-knight.mjs
node tools/validate-female-barbarian-bottom.mjs
blender -b --python-exit-code 1 -P tools/blender-scripts/review_female_barbarian_bottom.py
blender -b --python-exit-code 1 -P tools/blender-scripts/review_female_barbarian_bottom.py -- --belt --output assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/belt_repair_v2/blender
```
