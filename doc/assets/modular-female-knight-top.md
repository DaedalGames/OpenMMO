# 여성 기사 상의

짧은 흉갑·등판, 목 보호대, 견갑·상완 판금, 검은 천 소매와 가죽 고정끈으로 된 여성 기사 상의다. 복부는 노출하고 소매는 팔꿈치 아래 팔뚝에서 끝난다.
채택본은 `tripo_v1/fitted_v3`이며 여성 기준 몸체 65본 리그에 연결했다. **4,279삼각형**, 4K 컬러·노멀·ORM이다.
흉갑 중심은 `Spine1 0.9 + Spine2 0.1`, 견갑은 같은 쪽 `Shoulder`, 소매는 팔·팔뚝 본을 따른다.

![여성 기사 상의 착용](../images/characters/modular_human_female_01/female-knight-top-v3.png)

## 최종 파일

- [GLB](../../assets/items/female_knight_top/tripo_v1/fitted_v3/top_female_knight.glb),
  [Blender 편집본](../../assets/items/female_knight_top/tripo_v1/fitted_v3/female-knight-top-fitted.blend)(기준 리그·착용 몸체·9개 액션 포함)
- [몸체 가림](../../assets/items/female_knight_top/tripo_v1/fitted_v3/body-occlusion.json): 기본 상의·리본 2,488면과 덮이는 피부 2,384면을 숨기고, 벗거나 로딩에 실패하면 복원한다.
- [소매 보정 기록](../../assets/items/female_knight_top/tripo_v1/fitted_v3/sleeve-adjustment.json),
  [소매 보정 데이터](../../assets/items/female_knight_top/tripo_v1/fitted_v3/sleeve-adjustment.npz),
  [해시](../../assets/items/female_knight_top/tripo_v1/fitted_v3/local-artifacts.json)
- 검사: [피팅](modular-female-knight-top-fitting-v3.json), [본 결합·동작](modular-female-knight-top-animation-v3.json), [브라우저](modular-female-knight-top-preview-v3.json)

## 재현

재생성 스크립트는 없으며 채택한 `.blend`와 GLB가 편집 원본이다. 본 결합·동작 검사는 다음으로 다시 실행한다.

```bash
node tools/validate-female-knight-top-v2.mjs
```

## 출처·라이선스

- 원화: OpenAI Codex built-in ImageGen, **ChatGPT Pro 20x**, 2026-10-12. OpenAI 출력물 이용 조건 적용.
  [앞뒤 원화](../../assets/items/female_knight_top/concept_v1/sheet.png),
  [프롬프트](../../assets/items/female_knight_top/concept_v1/prompt.txt),
  [출처·해시](../../assets/items/female_knight_top/concept_v1/sources.json).
- 원화 참고: [사용자 사진](../../assets/items/female_knight_top/concept_v1/user-reference.png). 원저작자·라이선스 미확인.
- 메시: Tripo API 유료 크레딧, 2026-10-12. `P2-20260801`, 텍스처 `v3.5-20260815`, detailed PBR, 입력 조명 제거,
  4,000삼각형 목표. 작업 ID `93a31e72-6ad5-4e28-84c6-293ddf9062cc`, **120크레딧**.
  [API 문서](https://developers.tripo3d.ai/en/docs/generation-multiview-to-model/p), [이용 조건](https://developers.tripo3d.ai/en/terms).
  [제작 명세](../../assets/items/female_knight_top/tripo_v1/build.json),
  [요청·비용·작업 기록](../../assets/items/female_knight_top/tripo_v1/generation.json).
  `tools/outfits/tripo.py`로 기존 작업을 조회·회수한다.
- Tripo 입력: 시트의 `[0,128,768,704]`, `[768,128,768,704]`를 FFmpeg로 잘라
  [앞](../../assets/items/female_knight_top/tripo_v1/inputs/front.png)·[뒤](../../assets/items/female_knight_top/tripo_v1/inputs/back.png)로 제출했다.
- 생성 원본: [GLB](../../assets/items/female_knight_top/tripo_v1/source/model_url.glb),
  [Blender](../../assets/items/female_knight_top/tripo_v1/source.blend),
  [메시 진단](../../assets/items/female_knight_top/tripo_v1/review.json)·[스크립트](../../assets/items/female_knight_top/tripo_v1/review_source.py).
- 피팅·리깅은 로컬 작업이며 추가 비용은 없다.

## 제한

- 가림 전 피부·의상 안쪽 접촉이 남는다. 소매 입구 정점만 피부 비관통을 검사했다.
- 다른 장갑·투구 혼합과 출시용 장비 등록은 미검증이다. 높은 목 보호대와 투구에는 별도 옷깃 형상이 필요할 수 있다.
