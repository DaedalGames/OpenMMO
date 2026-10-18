# 여성 바바리안 상의

[여성 바바리안 원화](../../client/public/character_concepts/female_barbarian.webp)의 상의를 앞뒤 원화로 옮기고
Tripo로 생성해 여성 공통 몸체(`human_female_01_local_v1` 65본)에 피팅했다. 채택본은 Tripo v1의 `fitted_v1`이다.
리벳 철판 컵, 가운데 파란 보석과 청동 고리, 컵 아래 철띠, 등의 X자 가죽끈·버클, 착용자 오른쪽 어깨의 가시 견갑으로 구성한다.
초커·손목 보호대·벨트·모피 하의는 포함하지 않는다.
게임 적용은 [여성 야만용사 런타임](female-knight-runtime.md#여성-야만용사-적용--2026-10-16)을 따른다.

![여성 바바리안 상의 원화](../../assets/items/female_barbarian_top/concept_v1/sheet.png)

## 최종 파일

| 용도 | 파일 |
| --- | --- |
| 상의 | [top_female_barbarian.glb](../../assets/items/female_barbarian_top/tripo_v1/fitted_v1/top_female_barbarian.glb) (2,983 triangles, 4K 컬러·노멀·ORM) |
| 피팅 데이터 | [fit-data.npz](../../assets/items/female_barbarian_top/tripo_v1/fitted_v1/fit-data.npz) |
| 몸체 가림 | [body-occlusion.json](../../assets/items/female_barbarian_top/tripo_v1/fitted_v1/body-occlusion.json) (기본 상의·리본, 컵 안쪽 피부) |
| 피팅 기록 | [modular-female-barbarian-top-fitting-v1.json](modular-female-barbarian-top-fitting-v1.json) |
| 동작 검사 | [modular-female-barbarian-top-animation-v1.json](modular-female-barbarian-top-animation-v1.json) |

웨이트: 컵·끈·밴드는 아래 피부 웨이트를 따른다. 가운데 보석·고리는 `Spine1 0.9 + Spine2 0.1` 강체, 견갑은 `RightShoulder` 단독 강체다.

## 재현

리깅 단계 도구(`rig-female-knight-top-v2.py`)가 삭제되어 채택 GLB가 편집 원본이다.
가림과 검사는 남은 도구로 다시 실행한다.

```bash
.venv/bin/python tools/outfits/female_barbarian_top_occlusion.py
node tools/validate-female-barbarian-top.mjs
blender -b --python-exit-code 1 -P tools/blender-scripts/review_female_barbarian_top.py
```

형상 피팅은 [`fit_female_barbarian_top.py`](../../tools/blender-scripts/fit_female_barbarian_top.py)가 만든다(리깅 전 단계).

## 출처·라이선스

- 원화: OpenAI Codex built-in ImageGen(`codex exec`, codex-cli 0.162.1), **ChatGPT Pro 20x**, 2026-10-14.
  OpenAI 출력물 이용 조건을 따른다. 참조 원화의 출처는 [캐릭터 문서](characters.md)에 있다.
  [프롬프트](../../assets/items/female_barbarian_top/concept_v1/prompt.txt),
  [출처·분리 영역·해시](../../assets/items/female_barbarian_top/concept_v1/sources.json),
  [참조 입력](../../assets/items/female_barbarian_top/concept_v1/reference-crop.png)(원화를 흰 바탕에 합성해 `[260,250,520,400]`을 FFmpeg로 자름).
- 3D: Tripo API 유료 크레딧, 모델 `P2-20260801`, 텍스처 `v3.5-20260815`, detailed PBR, 입력 조명 제거,
  목표 3,000 triangles, seed 101401, 2026-10-14. 입력은 원화 앞·뒤 영역을 자른 두 장이다.
  작업 ID `1733c4c6-0730-4606-b020-a94c31b01984`, **120크레딧**(잔액 920 → 800).
  [API 문서](https://developers.tripo3d.ai/en/docs/generation-multiview-to-model/p),
  [이용 조건](https://developers.tripo3d.ai/en/terms).
  기존 작업은 재제출 없이 `tools/outfits/tripo.py`로 조회·회수한다.
- [제작 명세](../../assets/items/female_barbarian_top/tripo_v1/build.json),
  [요청·비용·작업 기록](../../assets/items/female_barbarian_top/tripo_v1/generation.json),
  [입력](../../assets/items/female_barbarian_top/tripo_v1/inputs/),
  [Tripo GLB](../../assets/items/female_barbarian_top/tripo_v1/source/model_url.glb),
  [생성 미리보기](../../assets/items/female_barbarian_top/tripo_v1/source/rendered_image_url.png),
  [원본 Blender](../../assets/items/female_barbarian_top/tripo_v1/source.blend),
  [원본 진단](../../assets/items/female_barbarian_top/tripo_v1/review.json)([스크립트](../../assets/items/female_barbarian_top/tripo_v1/review_source.py)).

## 제한

- 동작 검사에서 대기·걷기는 관통 0이다. jump·slash1·dying에서는 팔이 가슴 앞을 지나거나, 팔을 든 자세에서 상완이 견갑 아래로 들어가 관통이 남는다.
- 컵은 두께 없는 한 겹 면이라 뒤에서 보면 안쪽 면이 옆구리에 밝게 보일 수 있다.
  팔을 크게 움직이면 겨드랑이 쪽 가장자리가 접힌다.
- 보석판이 가슴골보다 넓어 가운데 고리·밑띠가 명치에서 조금 뜬다. 버클 고리가 끈과 비틀린 모양은 Tripo 원본 형상이다.
