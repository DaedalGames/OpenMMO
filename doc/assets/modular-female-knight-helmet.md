# 여성 기사 헬멧

열린 바이저 판금 투구다. 채택본은 `tripo_v1/fitted_v1`이며 여성 기준 몸체 65본 리그의 **Head 100%**로 연결했다.
바이저는 열린 상태로 고정되며 여닫기 본은 없다. **2,166삼각형**, 원본 UV와 4K 텍스처를 유지한다.
착용 중에는 선택한 헤어를 숨기고, 벗거나 로딩에 실패하면 복원한다. 얼굴·머리 피부는 숨기지 않는다.

![헬멧 원화](../../assets/items/female_knight_helmet/concept_v1/sheet.png)

## 최종 파일

- [GLB](../../assets/items/female_knight_helmet/tripo_v1/fitted_v1/helmet_female_knight.glb),
  [Blender 편집본](../../assets/items/female_knight_helmet/tripo_v1/fitted_v1/female-knight-helmet-fitted.blend)
- [피팅 기록](../../assets/items/female_knight_helmet/tripo_v1/fitted_v1/fitting.json),
  [가림](../../assets/items/female_knight_helmet/tripo_v1/fitted_v1/body-occlusion.json),
  [동작 검사](../../assets/items/female_knight_helmet/tripo_v1/fitted_v1/animation-validation.json),
  [조립 삼각형](../../assets/items/female_knight_helmet/tripo_v1/fitted_v1/assembly-counts.json),
  [해시](../../assets/items/female_knight_helmet/tripo_v1/fitted_v1/local-artifacts.json)

## 재현

```bash
.venv/bin/python tools/fit-female-knight-helmet.py
node tools/validate-female-knight-helmet.mjs
blender -b --python-exit-code 1 --python tools/blender-scripts/review_female_knight_helmet.py
```

## 출처·라이선스

- 원화: OpenAI Codex built-in ImageGen, **ChatGPT Pro 20x**, 2026-10-14. OpenAI 출력물 이용 조건 적용.
  [프롬프트](../../assets/items/female_knight_helmet/concept_v1/prompt.txt),
  [출처·해시](../../assets/items/female_knight_helmet/concept_v1/sources.json). 후면은 참고 이미지에 없어 같은 디자인으로 보완했다.
- 원화 참고: [사용자 이미지](../../assets/items/female_knight_helmet/concept_v1/user-reference.png). 원저작자·라이선스 미확인.
- 메시: Tripo API 유료 크레딧, 2026-10-14. `P2-20260801`, 2,000삼각형 목표, detailed PBR, `v3.5-20260815`, 입력 조명 제거.
  작업 ID `0873f512-16c5-4a52-a3b6-b1cec2cc7b89`, **120크레딧**. `tools/outfits/tripo.py`로 단일 제출했다.
  [Tripo 이용 조건](https://developers.tripo3d.ai/en/terms).
  [제작 명세](../../assets/items/female_knight_helmet/tripo_v1/build.json),
  [사전 잔액 확인](../../assets/items/female_knight_helmet/tripo_v1/preflight.json),
  [생성 기록](../../assets/items/female_knight_helmet/tripo_v1/generation.json),
  [해시](../../assets/items/female_knight_helmet/tripo_v1/local-artifacts.json).
- Tripo 입력: 시트의 정면·후면만 FFmpeg로 글자를 빼고 잘라 제출했다(측면 제외).
  [front](../../assets/items/female_knight_helmet/tripo_v1/inputs/front.png)·[back](../../assets/items/female_knight_helmet/tripo_v1/inputs/back.png).
- 생성 원본: [GLB](../../assets/items/female_knight_helmet/tripo_v1/source/model_url.glb),
  [렌더](../../assets/items/female_knight_helmet/tripo_v1/source/rendered_image_url.png),
  [텍스처·재질 대응](../../assets/items/female_knight_helmet/tripo_v1/source/textures.json),
  [텍스처 내장 Blender](../../assets/items/female_knight_helmet/tripo_v1/source.blend),
  [메시 진단](../../assets/items/female_knight_helmet/tripo_v1/review.json)·[스크립트](../../assets/items/female_knight_helmet/tripo_v1/review_source.py).
- 피팅·리깅은 로컬 작업이며 추가 비용은 없다.

## 제한

- 연결 성분 17개·열린 경계가 있어 밀폐 솔리드가 아니다.
- 모든 연속 자세에서 상의 목 보호대와의 무관통은 검사하지 않았다.
