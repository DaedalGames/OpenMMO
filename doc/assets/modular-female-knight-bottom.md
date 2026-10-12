# 여성 기사 하의

2026-10-13. [여성 기사 상의](modular-female-knight-top.md)에 맞춘 골반·허벅지 판금 하의다.
현재 승인본은 **fitted_v11**이며 여성 캐릭터 미리보기의 하의 선택에 연결했다.
본 게임 장비 등록과 모든 동작의 무관통 승인은 포함하지 않는다.

## 최종 에셋

- [착용 GLB](../../assets/items/female_knight_bottom/tripo_v1/fitted_v11/bottom_female_knight.glb):
  SHA-256 `53f853b29a4a91752bb1b3d20c5633b7ff97feea310be3f6a3545bcf1e3148e2`.
- [Blender 제작본](../../assets/items/female_knight_bottom/tripo_v1/fitted_v11/female-knight-bottom-fitted.blend),
  [몸체 가림 정보](../../assets/items/female_knight_bottom/tripo_v1/fitted_v11/body-occlusion.json),
  [피팅 명세](../../assets/items/female_knight_bottom/tripo_v1/fitted_v11/fitting.json).
- 5,758 triangles, 4 primitives, 65 bones. 리그는 `human_female_01_local_v1`이다.
- 몸체: `assets/modular_human_female_01/rig_v1/female-base.glb`,
  SHA-256 `cb6de19c87b3b0291e107834f17fca93a3f1a10e87b0fa041db6c3de98ec4732`.
  몸체 높이 1은 제작 좌표 단위이며 미터로 확정하지 않는다.
- 벨트·중앙 가리개는 Hips, 좌우 판금과 긴 끈은 같은 쪽 UpLeg에 연결한다.
  기본 몸체와 상의 v3를 함께 배치한 Blender 제작본을 보존한다.

허리 위쪽 판금은 둥글고 아래쪽은 점차 평평해지는 매끄러운 곡면이다. 하단은 수평이며,
안쪽 가장자리는 길게 내려오다 끝 부근에서 꺾인다. 모서리만 작게 둥글렸다.
상단 테두리와 앞쪽 판금은 실제 허리벨트·가죽띠에 닿거나 그 아래로 들어가도록 넓은 영역을
완만하게 변형했다. 중앙 가리개와 같은 메탈 재질·텍스처를 사용한다.
가죽, 중앙 가리개, 기존 리벳, 리그와 가림 정보는 v10에서 유지했다.

하의 가림은 속옷 1,110 triangles에만 적용하며 피부는 숨기지 않는다.
상의·하의 가림은 슬롯별 합집합으로 계산하고 해제하면 원래 몸체를 복원한다.
미리보기에는 하의 선택, 하의 확대 시점, 로드 실패 후 재선택 처리가 포함된다.

## 원화·생성 출처와 이용 조건

- 사용자 제공 참고 이미지의 원저작자와 라이선스는 미확인이다.
- 원화 도구·등급·날짜: OpenAI Codex ImageGen, **ChatGPT Pro 20x**, 2026-10-12.
  OpenAI 생성 출력물 이용 조건을 적용한다.
- [원화 v2 시트](../../assets/items/female_knight_bottom/concept_v2/sheet.png),
  [앞면](../../assets/items/female_knight_bottom/concept_v2/front.png),
  [뒷면](../../assets/items/female_knight_bottom/concept_v2/back.png),
  [프롬프트](../../assets/items/female_knight_bottom/concept_v2/prompt.txt),
  [출처·해시 기록](../../assets/items/female_knight_bottom/concept_v2/sources.json).
  1774×887 시트에서 FFmpeg로 887×887 앞뒤 입력을 추출했다.
- **[미사용]** concept_v1은 뒷면 가리개가 짧은 최초 원화다. v2 편집 입력과 출처 이력을 위해 보존한다.
  [사용자 원본 참고 이미지](../../assets/items/female_knight_bottom/concept_v1/user-reference.png)도 보존한다.
- Tripo API, 유료 크레딧, 2026-10-12. 모델 `P2-20260801`, 텍스처 `v3.5-20260815`,
  detailed PBR, 조명 제거, 목표 4,000 triangles. 자동 크기 추정·자동 리깅은 사용하지 않았다.
- 작업 ID `6722d281-43da-4a7e-944f-69a49d6117bd`, 비용 120크레딧.
  피팅 수정에는 추가 유료 API 호출이 없다.
- [요청 명세](../../assets/items/female_knight_bottom/tripo_v1/build.json),
  [생성·비용·해시 기록](../../assets/items/female_knight_bottom/tripo_v1/generation.json),
  [Tripo 이용 조건](https://developers.tripo3d.ai/en/terms).
- [Tripo 원본 GLB](../../assets/items/female_knight_bottom/tripo_v1/source/model_url.glb):
  SHA-256 `0b3a7bc7a3fa0f4d4776a881f22dbaf1cbc8ffa051cb0de931133a3d045d6d2a`.
  3,578 triangles, 미리깅 상태, 4096×4096 색상·노멀·ORM 텍스처가 포함된다.
- [원본 Blender](../../assets/items/female_knight_bottom/tripo_v1/source.blend),
  [원본 검사](../../assets/items/female_knight_bottom/tripo_v1/review.json),
  [추출 텍스처 기록](../../assets/items/female_knight_bottom/tripo_v1/texture-extraction.json)을 보존한다.
  원본의 열린 테두리·비다양체 형상은 생성 기록에 남겼으며 원본 자체는 수정하지 않았다.

## 수정 이력과 정리

| 버전 | 수정 및 검수 결과 |
| --- | --- |
| v1–v4 | 원본 피팅·리깅, 허리 간격 축소, 움푹한 실루엣 완화, 옆면 돌출 축소 |
| v5 | 울퉁불퉁한 측면 판금을 매끄러운 쉘로 재구성하고 하단을 수평으로 단축 |
| v6 | 중앙 가리개와 같은 메탈 재질 복원 |
| v7 | 아래로 내려갈수록 곡률을 줄임 |
| v8–v9 | 안쪽 지그재그 윤곽 및 모서리 둥글림; v9의 과도한 둥글림은 이후 수정 |
| v10 | 안쪽 가장자리를 길게 내리고 끝 부근에서만 꺾이도록 수정 |
| v11 | 판금을 허리벨트·가죽띠 아래로 연장하고 주변 곡면을 완만하게 연결 |

**[미사용]** fitted_v1–v10의 생성 GLB·Blender·계산 캐시와 검수 렌더는 사용자 요청으로 삭제했다.
최종 v11, 원본, 원화, 사용자 수정 참고 이미지, 작은 피팅·검증·실패 후보 기록은 남겼다.
[정리 기록](../../assets/items/female_knight_bottom/tripo_v1/cleanup.json)을 참조한다.
과거 기록의 출력 경로·해시는 제작 이력이며 해당 중간 파일의 현존을 뜻하지 않는다.

## 검증

- [glTF 검사](../../assets/items/female_knight_bottom/tripo_v1/fitted_v11/gltf-validation.json): 오류·경고 0.
- [런타임 검사](../../assets/items/female_knight_bottom/tripo_v1/fitted_v11/runtime-validation.json):
  14개 클립 각각 61시점, 강체 엣지 10,585개, 65본 바인딩·정규화 가중치·가림 합집합 통과.
- [형상 검사](../../assets/items/female_knight_bottom/tripo_v1/fitted_v11/preservation-validation.json):
  외부 면 990개, 수평 하단 정점 30개, 정규화 노멀·접선, 기존 부품·재질 보존 통과.
  기본 자세 피부 검사 1,620개 표본에서 관통 0.
- [가죽 접촉 검사](../../assets/items/female_knight_bottom/tripo_v1/fitted_v11/leather-contact-samples.json):
  앞쪽 엣지 20/20개가 가죽 아래에 위치한다. 상단 림 16개 중 15개는 아래,
  1개는 접촉 허용 오차 1e-5 이내다.
- [브라우저 검수](../../assets/items/female_knight_bottom/tripo_v1/fitted_v11/browser-review.json):
  정면·측면·후면·확대와 8개 동작, 의상 전환을 확인했다. 제공된 GLB의 해시도 일치했다.
- 엄격한 전역 볼록성이나 모든 동작의 삼각형 단위 무관통을 주장하지 않는다.
  가죽 아래 접합부의 조밀한 단면 표본에서 작은 음의 회전량(-0.000310)이 관찰됐다.

기사 상·하의와 기본 몸체 합계는 가림 전 32,212, 가림 후 26,230 triangles다.
금발 단발을 포함하면 34,648 / 28,666 triangles이며 얼굴 4,604 triangles는 유지했다.
캐릭터 권장 예산보다 높지만 예산만을 위한 추가 감면은 하지 않았다.

## 재검증·재제작

현재 최종 파일은 아래 명령만으로 런타임 재검증할 수 있다.

```sh
node tools/validate-female-knight-bottom.mjs v11
```

원본부터 재제작하려면 저장된 소스 에셋과 Blender가 필요하다. 다음 순서로 실행한다.
이 명령은 중간 파일과 최종 제작본을 다시 생성하므로 편집한 최종본은 먼저 별도로 보존한다.

```sh
blender -b --python tools/blender-scripts/fit_female_knight_bottom.py -- v1
blender -b --python tools/blender-scripts/fit_female_knight_bottom.py -- v4
blender -b --python tools/blender-scripts/refine_female_knight_bottom.py
blender -b --python tools/blender-scripts/match_female_knight_bottom_material.py
blender -b --python tools/blender-scripts/flatten_female_knight_bottom.py
blender -b --python tools/blender-scripts/zigzag_female_knight_bottom.py
blender -b --python tools/blender-scripts/round_female_knight_bottom_edges.py -- v9
blender -b --python tools/blender-scripts/round_female_knight_bottom_edges.py -- v10
blender -b --python tools/blender-scripts/round_female_knight_bottom_edges.py -- v11
```

버전 간 형상 보존 검사와 가죽 접촉 검사 스크립트는 v10 비교 입력을 요구하므로 위 순서로
중간본을 재생성한 뒤 프로젝트 `.venv` Python으로 실행한다. v5 쉘 검사도 해당 버전 생성 후 실행한다.
검수 스크린샷은 정리했으며 최종 검증 결과 JSON과 사용자 참고 이미지는 보존했다.
