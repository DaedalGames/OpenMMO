# 여성 로그 상의

[여성 로그 원화](../../client/public/character_concepts/female_rogue.webp)의 상의를 앞뒤 원화로 옮기고 Tripo로 생성한 뒤 현재 여성 기준 몸체에 피팅하고 기존 65본 리그에 연결했다.
검은 가죽 코르셋(가운데 리벳 단추, 뒤 레이스업), 가슴 위 X자 가죽끈과 고리, 칠부 회색 니트 소매, 어깨 가죽 탭, 등으로 내린 후드로 구성한다.
장갑·치마·벨트·가터는 포함하지 않는다.

![여성 로그 상의 원화](../../assets/items/female_rogue_top/concept_v1/sheet.png)

## Tripo v1 원본

![Tripo v1 정면](../../assets/items/female_rogue_top/tripo_v1/review/front.png)

3,751 triangles, 18개 분리 조각(본체 1,629 정점 + 고리·리벳 등), 4K 컬러·노멀·ORM.
[진단](../../assets/items/female_rogue_top/tripo_v1/review.json), [렌더](../../assets/items/female_rogue_top/tripo_v1/review/).

- 등 가운데가 트여 있어 뒤에서 앞 컵의 안쪽 면이 보인다.
- 가슴 X자 끈 아래에 원화에 없는 작은 고리가 붙었다.

## 피팅·리깅 v1 — 2026-10-25

- 기준: `assets/modular_human_female_01/rig_v1/female-base.glb`, 실제 높이 1.80m,
  `human_female_01_local_v1`. Blender Metric, `scale_length = 1`, 메시·리그 스케일 1.
- 원본의 회전 오프셋을 제거하고 몸통 높이·가슴·허리를 맞췄다. 칠부 소매는 여성 몸체의
  어깨·팔꿈치·팔목 축을 따라 다시 배치했다. UV 이음은 같은 위치와 가중치로 처리했다.
- 피부 삼각형의 barycentric 가중치를 전사하고 후드와 어깨 사이를 완만하게 연결했다.
  작은 고리·리벳의 분리 조각은 같은 가중치를 사용한다. 각 정점은 최대 4개 본을 따른다.
- 생성 원본의 3,751 triangles, UV와 4K 컬러·노멀·ORM을 유지했다. 새 유료 생성 요청은 없다.
- 내보낸 GLB를 실제 `bindModularPart`로 붙여 65개 본과 inverse bind 행렬의 일치,
  기본 자세 유지, 가중치 정규화, 반대 팔 가중치 유입 방지를 확인했다.
  여성 몸체의 9개 동작을 각각 33프레임씩 검사했다.
- 검수 조합은 몸체+상의 25,926 triangles(숨김 포함), 가림 후보 적용 시
  21,657 triangles다. 얼굴은 기존 몸체에 포함되며 헤어·무기는 제외했다.
- Blender 편집본에는 기준 몸체·상의·검수용 조명과 카메라, 기본 자세 및 9개 동작의
  샘플 자세, 숨겨진 Tripo 원본을 보관했다. 타임라인 1은 기본 자세이며 이후 10프레임 간격으로
  각 동작의 검수 자세가 있다. 원본 몸체 GLB와 Tripo 원본은 수정하지 않았다.

[리깅 GLB](../../assets/items/female_rogue_top/tripo_v1/fitted_v1/top_female_rogue.glb),
[편집용 Blender](../../assets/items/female_rogue_top/tripo_v1/fitted_v1/female-rogue-top.blend),
[피팅·동작·피부 간격 통합 기록](../../assets/items/female_rogue_top/tripo_v1/fitted_v1/fitting.json),
[가림 후보](../../assets/items/female_rogue_top/tripo_v1/fitted_v1/body-occlusion.json).

![피팅 앞뒤](../../assets/items/female_rogue_top/tripo_v1/fitted_v1/review/fitting.png)

재현 명령은 저장소 루트에서 실행한다. 첫 실행은 정적 피팅과 가중치 전사이며,
검사 도구가 내보낸 현재 여성 리그의 동작 행렬로 두 번째 피팅의 여유를 보정한다.

```bash
blender -b --python-exit-code 1 -P tools/blender-scripts/fit_female_rogue_top.py
node tools/validate-female-rogue-top.mjs
blender -b --python-exit-code 1 -P tools/blender-scripts/fit_female_rogue_top.py -- --animation-clearance
node tools/validate-female-rogue-top.mjs
blender -b --python-exit-code 1 -P tools/blender-scripts/review_female_rogue_top.py
```

기본 자세에서 검사한 정점·삼각형 중심의 3mm 초과 피부 관통은 0개다.
동작 중 최근접 피부 검사에는 일부 중첩 후보가 남는다(타 사지와의 접촉도 포함).
이를 충돌 합격으로 취급하지 않으며, 게임 등록 전 해당 동작·혼합 장비의 마무리 보정이 필요하다.
원본의 후드 뒤 작은 틈과 추가 가슴 고리는 보존했다.
여성 캐릭터 미리보기의 상의 목록에 **로그 가죽 코르셋**으로 연결했다.
`?character=female&top=rogue&camera=upper`로 바로 착용해 볼 수 있다.
브라우저에서 착용·해제 후 피부와 삼각형 수 복원, 6개 동작 전환, 페이지 오류 0개를 확인했다.
`npm run check`, `npm run lint`를 통과했다. 가림 JSON의 `primitive_triangles`도 기존 로더 규격에 맞췄다.
게임 등록·혼합 장비 조합·최종 런타임 텍스처 압축은 별도 단계다.
가림 JSON은 현재 몸체 해시에 종속된 후보이며, 착탈 시 원래 몸체 인덱스를 복원해야 한다.

사용자가 미리보기 결과를 확인하고 정리·커밋을 요청했다(2026-10-25).
개별 검수 렌더·동작 행렬 샘플·진단 중간 파일 23개와 작업용 임시 파일을 삭제했다.
검사 결과는 `fitting.json`에 통합했으며 최종 앞뒤 문서 이미지와 원본 정면 이미지는 보존했다.

### 보정 이력

- 초기 후드 가중치가 어깨·소매로 넘어가 달리기에서 모서리가 8.66배 늘어났다.
  후드 경계를 연속 가중치로 바꾸고 UV 이음을 통합해 전사·평활화했다.
- 숨긴 피부를 제외한 열린 메시로 간격을 계산하면 잘못된 음수 거리가 발생했다.
  현재는 전체 피부에서 최근접 삼각형을 찾고 해당 면의 가림 여부를 따로 기록한다.
- 동작 여유 보정에서 가슴을 지나는 손까지 피하려 하면 컵이 과도하게 변형됐다.
  몸통 보정에서는 팔 표면을 제외하고 마지막에 전체 피부와 촘촘한 삼각형 샘플을 다시 검사했다.

## 밑단 단축 v2 — 2026-10-25

- 사용자가 표시한 밑단 곡선을 따라 코르셋 하단을 약 36mm 올렸다.
  두 갈래 곡선과 끝단 장식은 함께 이동하며, 허리 위쪽으로 변형을 완만하게 줄였다.
  소매·가슴·후드의 기존 정점 위치는 유지했다.
- 승인된 v1 GLB를 직접 입력으로 사용해 기존 피팅 보정을 유지했다.
  하단을 피부에 다시 맞추고 노멀을 갱신했다. 3,751 triangles, UV·4K PBR 텍스처,
  스켈레톤·가중치·inverse bind 정보는 유지했다. 유료 생성 요청은 없다.
- 기본 자세에서 정점·삼각형 중심의 3mm 초과 피부 관통 후보는 0개다.
  기존 65본 및 9개 동작 각각 33프레임의 변형 검사를 통과했다.
  치마 v3와 함께 프리뷰에 연결했고, 착탈과 동작 전환을 확인했다.
  조합은 숨김 포함 28,636 triangles, 가림 적용 시 24,234 triangles다.
  기존 머리·얼굴은 그대로이며 큰 동작의 관통 보정은 별도 범위다.

[검사 기록](../../assets/items/female_rogue_top/tripo_v1/fitted_v2/fitting.json).
**[미사용]** 중간 모델·Blender·가림 파일은 현재 보정본으로 대체해 정리했다.

```bash
blender -b --python-exit-code 1 -P tools/blender-scripts/shorten_female_rogue_top.py
node tools/validate-female-rogue-top.mjs
blender -b --python-exit-code 1 -P tools/blender-scripts/review_female_rogue_top.py
```

## 앞 단추 아래 윤곽·옆 밑단 보정 v3 — 2026-10-25

- v2의 짧은 보정 구간 때문에 앞 단추 근처에서 꺾이던 윤곽을 수정했다.
  기존 v1 피팅본에서 36mm의 밑단 단축은 유지하고, 높이 방향 보정 구간을 150mm로 넓혔다.
  하단의 가로 윤곽을 평활화하고 피부 여유를 다시 맞춰 옆으로 튀어나온 가장자리도 줄였다.
- 아래 단추와 장식은 바뀐 천 표면에 밀착시키고 가중치를 전사했다.
  허리 보정 구간을 벗어난 장식과 소매·상단 정점 좌표는 v1과 같으며,
  3,751 triangles, 원본 UV 삼각형과 내장 텍스처 바이트, 65본 스켈레톤을 보존했다.
- 기존 런타임 연결 및 9개 동작 각각 33프레임 변형 검사를 통과했다.
  치마 v4와 함께 앞·뒤·옆 확대와 대기·걷기, 착탈 복원을 확인했다.
  `npm run check`, `npm run lint`를 통과했다. 큰 동작의 기존 관통 보정 범위는 유지한다.

[v3 GLB](../../assets/items/female_rogue_top/tripo_v1/fitted_v3/top_female_rogue.glb),
[v3 Blender](../../assets/items/female_rogue_top/tripo_v1/fitted_v3/female-rogue-top.blend),
[피팅·검사 통합 기록](../../assets/items/female_rogue_top/tripo_v1/fitted_v3/fitting.json),
[가림 정보](../../assets/items/female_rogue_top/tripo_v1/fitted_v3/body-occlusion.json).

## 단추 앞섶 폭 복원 v4 — 2026-10-26

- 하단 평활화가 단추가 붙은 앞섶의 가로 좌표까지 바꿔, 아래 단추 두 줄이 벌어졌다.
  v1 앞섶 중심 X=0.013m, 반폭 25mm 구간의 가로 좌표를 고정하고 바깥쪽 45mm에서 부드럽게 연결했다.
  피부 여유를 맞추거나 평활화할 때도 이 구간은 앞뒤 방향만 보정한다.
- 앞쪽 보호 구간 37개 정점의 원본 대비 최대 가로 변위는 v3 약 19.8mm에서 v4 0mm로 복원됐다.
  밑단의 36mm 단축과 매끄러운 옆선은 유지했다. 소매·상단 정점 좌표와 원본 UV 삼각형·텍스처 바이트도 유지했다.
- 기본 자세의 정점·면 중심 피부 간격은 약 6mm 이상이다. 기존 65본 연결과 9개 동작 각각 33프레임의
  가중치·유한 변형 검사를 통과했다. 대기·걷기 각각 5시점에서 단추 배열을 확대 검수했다.
  상하의 착탈 복원과 리소스 로드도 확인했으며 페이지 오류는 0개다.
  `npm run check`, `npm run lint`를 통과했다.
- 치마 v4와 함께 현재 프리뷰에 연결했다. 상의 3,751 triangles, 숨김 포함 조합 28,636 triangles,
  가림 적용 후 24,198 triangles다. 기존 머리·얼굴 배분과 큰 동작의 추가 관통 보정 범위는 유지한다.

[v4 GLB](../../assets/items/female_rogue_top/tripo_v1/fitted_v4/top_female_rogue.glb),
[v4 Blender](../../assets/items/female_rogue_top/tripo_v1/fitted_v4/female-rogue-top.blend),
[피팅·검사 통합 기록](../../assets/items/female_rogue_top/tripo_v1/fitted_v4/fitting.json),
[가림 정보](../../assets/items/female_rogue_top/tripo_v1/fitted_v4/body-occlusion.json),
[옆면 확대](../../assets/items/female_rogue_top/tripo_v1/fitted_v4/review/detail-side.png).

![단추 앞섶 폭 복원](../../assets/items/female_rogue_top/tripo_v1/fitted_v4/review/detail-front.png)

## 앉기 전용 하단 보정 v5 — 2026-10-26

- 사용자가 앉을 때 배에 묻히는 상의 하단을 해당 동작에서만 고치도록 요청했다.
  승인된 v4의 기본 정점·UV·텍스처·스킨 가중치·스켈레톤을 그대로 두고,
  기본 가중치가 0인 `pose_sit_idle` 모프를 추가했다. 하단 코르셋 426개 정점의 최대 보정량은 약 29.6mm다.
  가슴 끈과 소매는 보정 대상에서 제외하고, 앞섶의 가로 좌표는 고정했다.
- 프리뷰의 `sit_idle`에서만 모프 가중치 1을 적용하고, 다른 동작으로 바꾸면 즉시 0으로 복원한다.
  일시정지 상태에서 상의를 불러오거나 다시 입는 경우에도 적용한다.
  하단 금속 고리는 원형을 유지한 채 보정된 천을 따라 움직이도록 맞췄다.
- 실제 프리뷰 앉기 9개 시점으로 피팅하고 61개 시점에서 검사했다.
  하단 정점·면 중심의 몸통 피부 간격은 최소 약 -14.9mm에서 +5.6mm로 개선됐으며,
  1mm 초과 관통 샘플은 0개다. 검사는 하단 코르셋과 몸통 피부를 대상으로 하며,
  팔의 자기 중첩과 상단 가슴 끈은 포함하지 않는다.
- 실제 프리뷰의 14개 동작을 각각 33시점에서 런타임 연결·변형 검사했다.
  앉기를 제외한 13개 동작은 v4와 정점 위치 차이가 정확히 0m다.
  기본 GLB 버퍼·스켈레톤·재질과 기존 몸체 가림 인덱스도 보존했다.
- 브라우저 앉기 5시점의 정면·사선을 확대 검수하고, 다른 동작 전환·일시정지 중 착탈을 확인했다.
  페이지 오류·리소스 로드 실패는 0개이며, 조건부 모프 단위 검사 2개와 `npm run check`, `npm run lint`를 통과했다.
  조합은 여전히 숨김 포함 28,636 triangles, 가림 적용 후 24,198 triangles다.
  이 상의 보정 단계에서는 다른 동작과 치마 형상을 변경하지 않았다.

이후 치마에도 [앉기 전용 v5 보정](modular-female-rogue-skirt.md)을 추가해 함께 프리뷰에 연결했다.

[현재 GLB](../../assets/items/female_rogue_top/tripo_v1/fitted_v5/top_female_rogue.glb),
[현재 Blender](../../assets/items/female_rogue_top/tripo_v1/fitted_v5/female-rogue-top.blend),
[피팅·검사 통합 기록](../../assets/items/female_rogue_top/tripo_v1/fitted_v5/fitting.json),
[가림 정보](../../assets/items/female_rogue_top/tripo_v1/fitted_v5/body-occlusion.json),
[앉기 사선 확대](../../assets/items/female_rogue_top/tripo_v1/fitted_v5/review/detail-side.png).

![앉기 전용 상의 하단 보정](../../assets/items/female_rogue_top/tripo_v1/fitted_v5/review/detail-front.png)

```bash
node tools/export-female-rogue-seated-poses.mjs
blender -b --python-exit-code 1 -P tools/blender-scripts/fit_female_rogue_top_seated.py
node tools/validate-female-rogue-top.mjs
blender -b --python-exit-code 1 -P tools/blender-scripts/review_female_rogue_top.py
```

## 오른팔 소매 밀착 보정 v6 — 2026-10-26

- 대기 자세에서 팔 뒤로 뜨던 오른쪽 소매를 팔 표면에 맞추고 각진 윤곽을 완만하게 정리했다.
  v5의 오른팔 가중치 구간에서 842개 정점을 보정했으며 최대 이동량은 약 44.1mm다.
  겨드랑이 연결부까지 포함해 피부 여유를 다시 확인했다.
- 왼팔·코르셋의 정점, 스킨 가중치·65본 스켈레톤, UV·텍스처·3,751 triangles와
  기존 `pose_sit_idle` 모프를 보존했다. 몸체 가림 인덱스는 유지하고 상의 해시만 갱신했다.
  소매 형상은 기본 메시에서 수정하므로 다른 동작에서도 적용된다. 새 유료 생성 요청은 없다.
- 기본 자세와 실제 대기 동작 61시점에서 움직이는 정점·면 중심·변 중점을 검사했다.
  보정 경계 삼각형을 포함한 피부 간격은 최소 약 +0.47mm이며, 1mm 초과 관통 샘플은 0개다.
  14개 동작 각각 33시점의 런타임 연결·유한 변형 검사를 통과했고, 수정 영역 밖 정점의
  v5 대비 동작 중 위치 차이는 0m다. 다른 큰 동작의 피부 관통 합격을 뜻하지 않는다.
- 프리뷰 연결을 v6로 갱신했다. 대기 5시점의 뒤·옆·앞을 검수하고 착탈 및 앉기 모프의
  적용·복원을 확인했다. 페이지 오류·리소스 실패는 0개이며 `npm run check`, `npm run lint`를 통과했다.
  상의 삼각형 수와 얼굴 배분, 기존 조합의 숨김 포함·가림 적용 후 삼각형 수는 동일하다.

[v6 GLB](../../assets/items/female_rogue_top/tripo_v1/fitted_v6/top_female_rogue.glb),
[편집용 Blender](../../assets/items/female_rogue_top/tripo_v1/fitted_v6/female-rogue-top.blend),
[피팅·검사 기록](../../assets/items/female_rogue_top/tripo_v1/fitted_v6/fitting.json),
[가림 정보](../../assets/items/female_rogue_top/tripo_v1/fitted_v6/body-occlusion.json).

[정면 검수](../../assets/items/female_rogue_top/tripo_v1/fitted_v6/review/idle-front.png),
[오른쪽 검수](../../assets/items/female_rogue_top/tripo_v1/fitted_v6/review/idle-right.png).

![오른팔 소매 보정 후 대기 자세 후면](../../assets/items/female_rogue_top/tripo_v1/fitted_v6/review/idle-back.png)

```bash
node tools/export-female-rogue-seated-poses.mjs assets/items/female_rogue_top/tripo_v1/fitted_v6 idle1
blender -b --python-exit-code 1 -P tools/blender-scripts/fit_female_rogue_sleeve.py
node tools/validate-female-rogue-top.mjs
```

## 출처·라이선스

- 원화: OpenAI Codex built-in ImageGen(`codex exec`, codex-cli 0.162.1), **ChatGPT Pro 20x**, 2026-10-25.
  OpenAI 출력물 이용 조건을 따른다. 참조 원화의 출처는 [캐릭터 문서](characters.md)에 있다.
  [프롬프트](../../assets/items/female_rogue_top/concept_v1/prompt.txt),
  [출처·해시](../../assets/items/female_rogue_top/concept_v1/sources.json),
  [참조 입력](../../assets/items/female_rogue_top/concept_v1/reference-crop.png)(원화를 흰 바탕에 합성해 `[0,220,832,300]`을 FFmpeg로 자름).
- 3D: Tripo API 유료 크레딧, 모델 `P2-20260801`, 텍스처 `v3.5-20260815`, detailed PBR, 입력 조명 제거,
  목표 4,000 triangles, seed 102501, 2026-10-25. 입력은 원화 앞 `[0,120,768,720]`·뒤 `[768,120,768,720]` 영역을 자른 두 장이다.
  작업 ID `53edf32c-cf8b-4135-80d4-aec96da81fe0`, **120크레딧**(잔액 280 → 160).
  [API 문서](https://developers.tripo3d.ai/en/docs/generation-multiview-to-model/p),
  [이용 조건](https://developers.tripo3d.ai/en/terms).
  기존 작업은 재제출 없이 `tools/outfits/tripo.py`로 조회·회수한다.
- [제작 명세](../../assets/items/female_rogue_top/tripo_v1/build.json),
  [요청·비용·작업 기록](../../assets/items/female_rogue_top/tripo_v1/generation.json),
  [입력](../../assets/items/female_rogue_top/tripo_v1/inputs/),
  [Tripo GLB](../../assets/items/female_rogue_top/tripo_v1/source/model_url.glb),
  [생성 미리보기](../../assets/items/female_rogue_top/tripo_v1/source/rendered_image_url.png),
  [원본 Blender](../../assets/items/female_rogue_top/tripo_v1/source.blend)([스크립트](../../assets/items/female_rogue_top/tripo_v1/review_source.py)).
