# 여성 기사 하의

[여성 기사 상의](modular-female-knight-top.md)에 맞춘 골반·허벅지 판금 하의다.
여성 기사 캐릭터의 하의 슬롯으로 쓰이며, `tools/prepare-female-knight.mjs`가 게임용 GLB로 변환한다
([여성 기사 런타임](female-knight-runtime.md)). 채택본은 **fitted_v42**다.

## 최종 파일

- [착용 GLB](../../assets/items/female_knight_bottom/tripo_v1/fitted_v42/bottom_female_knight.glb):
  12,118삼각형·4 primitives·65본, 리그 `human_female_01_local_v1`.
  2026-10-17 미터 단위로 전환했다.
- [Blender 제작본](../../assets/items/female_knight_bottom/tripo_v1/fitted_v42/female-knight-bottom-fitted.blend),
  [몸체 가림](../../assets/items/female_knight_bottom/tripo_v1/fitted_v42/body-occlusion.json),
  [피팅 명세](../../assets/items/female_knight_bottom/tripo_v1/fitted_v42/fitting.json).
- v42 검사 기록: [런타임](../../assets/items/female_knight_bottom/tripo_v1/fitted_v42/runtime-validation.json),
  [클립 연결](../../assets/items/female_knight_bottom/tripo_v1/fitted_v42/clip-attachment-validation.json),
  [직선 구간](../../assets/items/female_knight_bottom/tripo_v1/fitted_v42/straightness-validation.json).
  검사 도구는 삭제됐다.
- 가림은 몸체 하의 속옷 1,110삼각형만 숨기고 피부는 남긴다. 상의 가림과 합집합으로 적용한다.

## 재현

재생성 도구는 남아 있지 않다. 위 v42 `.blend`·GLB가 편집 원본이다.

## 출처·라이선스

- 원화: OpenAI Codex ImageGen, **ChatGPT Pro 20x**, 2026-10-12. OpenAI 생성 출력물 이용 조건을 적용한다.
  - [concept_v2 시트](../../assets/items/female_knight_bottom/concept_v2/sheet.png)(채택),
    [프롬프트](../../assets/items/female_knight_bottom/concept_v2/prompt.txt),
    [출처·해시 기록](../../assets/items/female_knight_bottom/concept_v2/sources.json).
    concept_v1 시트에서 뒤 중앙 가리개만 앞 가리개 형태로 바꾼 편집본이다.
  - [concept_v1 시트](../../assets/items/female_knight_bottom/concept_v1/sheet.png)(concept_v2 편집 원본),
    [프롬프트](../../assets/items/female_knight_bottom/concept_v1/prompt.txt),
    [출처 기록](../../assets/items/female_knight_bottom/concept_v1/sources.json).
  - [사용자 제공 참고 이미지](../../assets/items/female_knight_bottom/concept_v1/user-reference.png):
    원저작자·라이선스 미확인.
- 3D: Tripo API, 유료 크레딧, 2026-10-12. multiview-to-model, 모델 `P2-20260801`,
  텍스처 `v3.5-20260815`, detailed PBR, 조명 제거, 목표 4,000 triangles, 자동 크기·자동 리깅 미사용.
  작업 ID `6722d281-43da-4a7e-944f-69a49d6117bd`, 비용 120크레딧.
  [Tripo 이용 조건](https://developers.tripo3d.ai/en/terms).
  - [요청 명세](../../assets/items/female_knight_bottom/tripo_v1/build.json),
    [생성·비용·해시 기록](../../assets/items/female_knight_bottom/tripo_v1/generation.json).
  - 입력: concept_v2 시트를 FFmpeg로 자른 887×887
    [앞면](../../assets/items/female_knight_bottom/tripo_v1/inputs/front.png)·[뒷면](../../assets/items/female_knight_bottom/tripo_v1/inputs/back.png).
  - [Tripo 원본 GLB](../../assets/items/female_knight_bottom/tripo_v1/source/model_url.glb):
    3,578 triangles, 리깅 전, 4096×4096 색상·노멀·ORM 텍스처.
    [원본 Blender](../../assets/items/female_knight_bottom/tripo_v1/source.blend),
    [원본 검사](../../assets/items/female_knight_bottom/tripo_v1/review.json),
    [추출 텍스처 기록](../../assets/items/female_knight_bottom/tripo_v1/texture-extraction.json).
- 피팅·리깅·끈 정렬은 로컬 Python/Blender 편집이며 추가 생성·유료 API 호출은 없다.

## 제한

- 끈은 가중치 변형이며 천 시뮬레이션이 아니다. 앉기와 큰 관절 회전에서 끈이 몸에 묻히거나 접힐 수 있다.
- 모든 동작의 무관통은 검증하지 않았다.
- `.blend`는 미터 전환 전 제작 단위(몸체 높이 1)로 남아 있다. 단위 전환은 [여성 기사 런타임](female-knight-runtime.md#원본-미터-단위-전환--2026-10-17)을 참고한다.
