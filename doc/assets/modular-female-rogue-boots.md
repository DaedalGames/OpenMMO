# 여성 로그 부츠

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
node tools/validate-female-rogue-boots.mjs
blender -b --python-exit-code 1 -P tools/blender-scripts/review_female_rogue_boots.py
```

## 출처·라이선스

- 원화 생성: OpenAI Codex built-in `image_gen`, **ChatGPT Pro 20x**, 2026-10-26.
  OpenAI 출력물 이용 조건을 따른다. 참조 원화의 출처는 [캐릭터 제작 기록](characters.md)을 따른다.
- 참조 이미지는 원본을 흰 바탕에 합성하고 `[220,640,360,590]` 영역을 FFmpeg로 추출했다.
  생성 시트는 1536×1024이며 정면 `[192,0,512,1024]`, 후면 `[832,0,512,1024]`를 잘랐다.
  각 입력은 460×920으로 비율을 유지해 축소한 뒤 1024×1024 흰 바탕 중앙에 배치했다.
- 3D 생성: Tripo API 유료 크레딧, 2026-10-26. [다중 이미지 API](https://developers.tripo3d.ai/en/docs/generation-multiview-to-model/p),
  [이용 조건](https://developers.tripo3d.ai/en/terms)을 따른다.
