# 여성 기사 하의

2026-10-13. [여성 기사 상의](modular-female-knight-top.md)에 맞춘 골반·허벅지 판금 하의다.
현재 **fitted_v17**을 여성 캐릭터 미리보기에 연결했다. 양쪽 앞 가죽끈을 허리 버클 끝에 맞추고,
버클 틈과 자연스럽게 늘어지는 선을 조정했다. 거의 겹쳐 깜박이던 앞뒷면에는 얇은 두께를 확보했다.
본 게임 장비 등록과 모든 동작의 무관통 승인은 포함하지 않는다.

## 최종 에셋

- [착용 GLB](../../assets/items/female_knight_bottom/tripo_v1/fitted_v17/bottom_female_knight.glb):
  SHA-256 `f5a5debd117114a18f5927a3de7781bcaedcec785d4963fa4e499854d50caee4`.
- [Blender 제작본](../../assets/items/female_knight_bottom/tripo_v1/fitted_v17/female-knight-bottom-fitted.blend),
  [몸체 가림](../../assets/items/female_knight_bottom/tripo_v1/fitted_v17/body-occlusion.json),
  [피팅 명세](../../assets/items/female_knight_bottom/tripo_v1/fitted_v17/fitting.json).
- 제작 입력: [v11 GLB](../../assets/items/female_knight_bottom/tripo_v1/fitted_v11/bottom_female_knight.glb),
  [v11 Blender](../../assets/items/female_knight_bottom/tripo_v1/fitted_v11/female-knight-bottom-fitted.blend).
  GLB SHA-256 `53f853b29a4a91752bb1b3d20c5633b7ff97feea310be3f6a3545bcf1e3148e2`.
- 5,758삼각형·4 primitives·65본. 리그는 `human_female_01_local_v1`이다.
  몸체는 `assets/modular_human_female_01/rig_v1/female-base.glb`이며
  SHA-256은 `cb6de19c87b3b0291e107834f17fca93a3f1a10e87b0fa041db6c3de98ec4732`다.
- 기사 상·하의와 몸체 합계는 가림 전 32,212·가림 후 26,230삼각형이다.
  금발 단발 포함 34,648·28,666삼각형, 얼굴 4,604삼각형을 유지했다.
  권장 예산보다 높지만 예산만을 위한 감면은 하지 않았다.

## 형상·연결·가림

v11의 판금은 둥근 허리에서 아래로 갈수록 평평해지고, 수평 밑단과 끝에서 꺾이는 안쪽 윤곽을 가진다.
중앙 가리개와 같은 메탈 재질을 사용한다. 이번 수정에서 판금·가리개·뒤쪽 끈은 유지했다.

양쪽 앞 가죽끈과 끝 장식의 584정점을 안쪽으로 0.013, 아래로 0.001 이동했다.
위쪽에 집중했던 깊이 보정을 전체 길이에 분산해 꺾임을 폈다. 위쪽은 Hips에 고정하고
아래쪽은 같은 쪽 UpLeg로 완만하게 가중치를 전환한다. 수치는 몸체 높이 1인 제작 좌표이며
미터로 확정하지 않는다.

양면 재질인 끈의 앞뒷면이 거의 겹치거나 교차하여 깜박임이 발생했다. 해당 구간 101정점의
깊이를 최대 ±0.00045 보정하고 노멀·탄젠트를 맞췄다. 버클과 끝 장식에 가까워질수록 보정을
줄여 끝 위치를 유지했다. UV·인덱스·재질·텍스처·골격은 보존했으며 새 면·메쉬를 추가하지 않았다.
v12의 추가 보강 메쉬는 사용하지 않는다. 로컬 편집이며 신규 생성·유료 API 호출은 없다.

하의 가림은 속옷 1,110삼각형에만 적용하며 피부는 숨기지 않는다.
상하의 가림은 슬롯별 합집합으로 계산하고 해제하면 몸체를 복원한다.
미리보기는 하의 선택·하의 확대·로드 실패 후 재선택을 지원한다.

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
| v11 | 판금을 허리벨트·가죽띠 아래로 연장하고 주변 곡면을 완만하게 연결; 현재 끈 편집의 입력 |
| v12 | 추가 보강 메쉬 후보. 사용자 요청으로 되돌림 |
| v13–v14 | 화면 오른쪽 앞 가죽끈을 허리 버클에 연결하고 버클 틈·늘어지는 선 조정 |
| v15 | 반대쪽 끈도 버클 끝에 맞춤; 두께 검사 회귀 비교용 GLB 보존 |
| v16–v17 | 양쪽 앞 가죽끈의 거의 겹치는 앞뒷면에 간격 확보 |

**[미사용]** fitted_v1–v10의 생성 GLB·Blender·계산 캐시와 검수 렌더는 사용자 요청으로 삭제했다.
당시 최종 v11, 원본, 원화, 사용자 수정 참고 이미지, 작은 피팅·검증·실패 후보 기록은 남겼다.
[정리 기록](../../assets/items/female_knight_bottom/tripo_v1/cleanup.json)을 참조한다.
과거 기록의 출력 경로·해시는 제작 이력이며 해당 중간 파일의 현존을 뜻하지 않는다.


이번 정리에서 v12–v16의 중간 GLB·Blender와 v13–v17 검수 스크린샷 등 60개,
약 381.1MiB를 삭제했다. v17 최종본·편집 원본·검증 기록, v11 제작 입력,
v15의 GLB·가림·피팅 명세(회귀 검사 입력), 각 단계의 작은 피팅 기록과 사용자 참고 이미지는 남겼다.
[이번 정리 목록](../../assets/items/female_knight_bottom/tripo_v1/strap-cleanup.json)을 참조한다.
중간 버전의 과거 피팅 기록에 있는 출력·검증 경로는 제작 이력이며 파일 보존 목록이 아니다.

## 검증

- [두께 검사](../../assets/items/female_knight_bottom/tripo_v1/fitted_v17/thickness-validation.json):
  얇은 측벽을 제외한 넓은 앞뒷면(`|normal.z| > 0.7`)을 검사했다.
  화면 왼쪽 1,380샘플의 최소 간격은 0.000174992, 오른쪽 1,454샘플은 0.000175831이며 교차는 0개다.
  버클·끝 장식·XY 좌표·UV·인덱스·가중치·재질·골격 보존도 검사한다.
- [런타임 검사](../../assets/items/female_knight_bottom/tripo_v1/fitted_v17/runtime-validation.json):
  14동작×61시점, 양쪽 연결부 153정점, 강체 엣지 10,605개,
  65본 바인딩·정규화 가중치·가림 전환 통과.
- [glTF 검사](../../assets/items/female_knight_bottom/tripo_v1/fitted_v17/gltf-validation.json): 오류·경고 0.
- [브라우저 검수](../../assets/items/female_knight_bottom/tripo_v1/fitted_v17/browser-review.json):
  정면의 작은 카메라 이동과 양쪽 사선에서 깜박임 줄무늬가 없음을 확인했다.
  중간 피팅 단계에서는 대기·걷기·달리기·앉기도 검수했다.
- 기존 동작 중 판금 틈과 끈 변형은 남아 있다. 두께 수치 검사는 기본 자세의 넓은 앞뒷면에
  한정하며 모든 동작·측벽의 삼각형 단위 무관통 승인은 아니다.

## 재검증·재제작

보관한 입력으로 최종본을 검사할 수 있다.

```sh
node tools/validate-female-knight-bottom.mjs v17
.venv/bin/python tools/validate-female-knight-strap-thickness.py v17
```

v11 입력에서 최종 GLB와 Blender를 다시 만들려면 다음 명령을 실행한다.
편집한 최종본을 덮어쓰므로 필요한 수정본은 먼저 별도로 보존한다.

```sh
blender -b --python-exit-code 1 --python tools/blender-scripts/connect_female_knight_front_strap.py -- --version v17 --blend
```

v13–v16을 재생성하려면 `--version` 값을 바꾼다. v15는 두께 검사 비교 입력이므로 보존한다.
v11 자체를 원본부터 재제작하는 절차는 다음과 같다.

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
