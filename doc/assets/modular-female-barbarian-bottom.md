# 여성 바바리안 하의 — 2026-10-15

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

![Tripo 원본 앞·옆·뒤·사선](../../assets/items/female_barbarian_bottom/tripo_v1/review/strip.png)

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

![착용 앞·옆·뒤·사선·아래](../../assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/review/strip.png)

기준 몸체 `assets/modular_human_female_01/rig_v1/female-base.glb`, 리그 `human_female_01_local_v1` 65본.
몸체·동작은 변경하지 않았다. 삼각형 3,256개(원본 3,241 + 구멍 메움 15), UV는 Tripo 원본 그대로이고 텍스처는 WebP q90으로 내보냈다.

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
  현재 피부 189면·팬티 406면을 숨긴다(아래 허리선 보정 후 다시 계산).
  나머지 팬티는 모피 틈으로 보이므로 그대로 둔다.

### 검증

`bindModularPart`로 결합해 9동작 × 121시점을 검사했다. 본·inverse bind 일치, 웨이트 정규화, 상체 본 영향 없음,
강체 조각 변형 0. 관통(휴지 자세보다 2mm 이상 깊어진 정점, 가장 가까운 피부 정점 기준 근사)은 아래와 같다.

| 동작 | 관통 정점 | 최대 깊이 | 모서리 최대 늘어남 |
| --- | --- | --- | --- |
| 대기 | 13 | 0.4cm | 2.3배 |
| 걷기 | 166 | 1.1cm | 4.3배 |
| 달리기 | 559 | 4.2cm | 6.4배 |
| 점프 | 1,446 | 6.8cm | 5.4배 |
| 전투 대기 | 1,038 | 5.0cm | 8.3배 |
| 베기 | 1,089 | 6.6cm | 8.7배 |
| 쓰러지기 | 1,171 | 8.1cm | 7.6배 |
| 앉기 | 945 | 4.4cm | 2.6배 |

큰 동작의 관통은 대부분 모피 판이다. 다리를 크게 들면 허벅지가 판을 뚫고, 다리를 벌리면 앞 가운데 판이 양 다리 사이에서 늘어난다.
위 표는 아래 안쪽 면·허리선 보정과 가림 재계산 후의 값이다. 안쪽 면과 검사에 사용되는 가시 몸체 정점이 바뀌어 근사 관통 집계는 일부 늘었지만,
휴지 자세의 실제 몸체 표면 검사에서는 관통 0, 최소 간격 1mm를 유지한다.

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
- [미리보기 검사](../../assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/belt_repair_v2/runtime-validation.json),
  [몸체 표면 간격](../../assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/belt_repair_v2/rest-clearance.json).
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
- [미리보기 검증](../../assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/waistband_repair_v1/runtime-validation.json),
  [몸체 간격 검증](../../assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/waistband_repair_v1/rest-clearance.json),
  [재현 스크립트](../../tools/fit-female-barbarian-waistband.py).

### 남은 문제

- 기본 몸체 피부에 하의 속옷이 구워져 있어 팬티 메시를 숨겨도 같은 흰색이 보인다. 그래서 틈은 메워서 막았다.
- 뒤 허리띠의 가죽 이음 무늬는 원본 그대로다. 철판 위 검은 삼각형과 안쪽 면의 겹침은 위 형상 보정으로 수정했다.
- 앞 가운데 판 끝은 무릎 위 약 5cm다. 원화보다 조금 길다.
- 큰 동작의 모피 관통과 늘어남(위 표).

| 용도 | 파일 |
| --- | --- |
| 하의 | [bottom_female_barbarian.glb](../../assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/bottom_female_barbarian.glb) |
| 가림 명세 | [body-occlusion.json](../../assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/body-occlusion.json) |
| 피팅 기록 | [modular-female-barbarian-bottom-fitting-v1.json](modular-female-barbarian-bottom-fitting-v1.json) |
| 동작 검사 | [modular-female-barbarian-bottom-animation-v1.json](modular-female-barbarian-bottom-animation-v1.json) |

### 미리보기

개발 서버의 `/modular-character-preview.html?character=female&camera=lower&bottom=barbarian`에서 연다.

### 재현

```bash
blender -b --python-exit-code 1 -P tools/blender-scripts/fit_female_barbarian_bottom.py
.venv/bin/python tools/rig-female-knight-top-v2.py assets/items/female_barbarian_bottom/tripo_v1/fitted_v1 bottom_female_barbarian doc/assets/modular-female-barbarian-bottom-fitting-v1.json 1
.venv/bin/python tools/fix-female-barbarian-belt.py assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/bottom_female_barbarian.glb
.venv/bin/python tools/fit-female-barbarian-waistband.py assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/bottom_female_barbarian.glb
.venv/bin/python tools/outfits/female_barbarian_bottom_occlusion.py
node tools/validate-female-barbarian-bottom.mjs
blender -b --python-exit-code 1 -P tools/blender-scripts/review_female_barbarian_bottom.py
blender -b --python-exit-code 1 -P tools/blender-scripts/review_female_barbarian_bottom.py -- --belt --output assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/belt_repair_v2/blender
```
