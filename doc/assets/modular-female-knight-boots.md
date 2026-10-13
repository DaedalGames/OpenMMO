# 여성 기사 판금 부츠

2026-10-13. 현재 착용 검토본은 `fitted_v4`다. 한쪽 판금 부츠를 좌우 대칭 제작하고
여성 기준 몸체의 65본 리그에 연결했다. 허벅지·종아리는 1mm 여유를 기준으로 피팅하며,
착용 중에는 발목·발가락과 접지를 높은 굽 자세에 맞춰 보정한다.

## 현재 파일과 출처

- [양쪽 리깅 GLB](../../assets/items/female_knight_boots/fitted_v4/boots_female_knight.glb).
- [여성 몸체·부츠·보정된 9개 액션을 포함한 Blender 편집본](../../assets/items/female_knight_boots/fitted_v4/female-knight-boots-fitted.blend).
- [정면 착용](../../assets/items/female_knight_boots/fitted_v4/browser/idle1.png),
  [측면](../../assets/items/female_knight_boots/fitted_v4/review/rest-side.png).
- [승인된 한쪽 피팅 원본](../../assets/items/female_knight_boots/sole_v3/boot_right.glb),
  [한쪽 편집본](../../assets/items/female_knight_boots/sole_v3/boot_right.blend).
- [Tripo 원본](../../assets/items/female_knight_boots/tripo_v1/source/model_url.glb),
  [원본 PBR 추출 기록](../../assets/items/female_knight_boots/tripo_v1/texture-extraction.json).

원화는 OpenAI Codex ImageGen, **ChatGPT Pro 20x**, 2026-10-13 생성이다.
사용자 참고 이미지의 원저작자·라이선스는 미확인이며, 생성 원화에는 OpenAI 출력물 이용 조건이 적용된다.
[원화 시트](../../assets/items/female_knight_boots/concept_v1/sheet.png),
Tripo용 [정면](../../assets/items/female_knight_boots/concept_v1/front.png)·
[측면](../../assets/items/female_knight_boots/concept_v1/side.png)·
[후면](../../assets/items/female_knight_boots/concept_v1/back.png),
[프롬프트](../../assets/items/female_knight_boots/concept_v1/prompt.txt),
[출처·해시](../../assets/items/female_knight_boots/concept_v1/sources.json)를 보관한다.
개별 시점은 1536×1024 시트를 FFmpeg로 512×1024씩 분리한 입력이다.

Tripo API 유료 크레딧으로 2026-10-13 생성했다. 모델 `P2-20260801`,
텍스처 `v3.5-20260815`, detailed PBR, 한쪽 목표 2,000삼각형이며 실제 원본은 2,106삼각형이다.
작업 ID는 `20653499-69ca-4be6-bfa0-76ac6ad77323`, 실제 비용은 **120크레딧**이다.
[요청 명세](../../assets/items/female_knight_boots/tripo_v1/build.json),
[작업·비용 기록](../../assets/items/female_knight_boots/tripo_v1/generation.json),
[Tripo 이용 조건](https://developers.tripo3d.ai/en/terms)을 따른다.
이후 굽·밑창·후면·피팅·리깅 수정은 로컬 작업이며 추가 생성 비용은 없다.

## 피팅과 착용 자세

기준 몸체는 `assets/modular_human_female_01/rig_v1/female-base.glb`,
SHA-256 `cb6de19c87b3b0291e107834f17fca93a3f1a10e87b0fa041db6c3de98ec4732`,
리그는 `human_female_01_local_v1`이다. 승인된 한쪽 원본 `sole_v3/boot_right.glb`의
SHA-256은 `aa05a6d1b6ec8b73e1265e1fc64d460ae75800068557c211c6f6c067b02d6af2`다.

몸체 높이 1.0과 실제 키 1.8m를 대응시켜 1mm를 제작 좌표 0.000556으로 환산했다.
여성 다리의 단면·무릎·발목 위치로 피팅하고 X 대칭, 왼쪽 면 방향 반전,
Left/Right UpLeg·Leg·Foot·ToeBase 대응을 적용했다. 본 순서·계층·inverse bind는 몸체와 같다.
관절 경계에서 면을 분리하고 판금은 구역별 단일 본 또는 일정한 50:50 무릎 가중치로 연결했다.
뒤 가죽과 검은 관절 안감에는 연속 가중치를 사용한다. 내부 입구 캡은 한쪽 169면을 제거했다.

**1mm는 입력 여유 기준이며 모든 표면의 일정한 실측 거리는 아니다.** 판금 굴곡 때문에
허벅지·종아리의 표본 전후좌우 간격은 약 −0.44–4.60mm다. 이음·사선의 국소 교차에는
착용 중 피부 가림을 적용한다. [피팅·단면 기록](../../assets/items/female_knight_boots/fitted_v4/fitting.json)을 참고한다.
가림 경계는 각도별 커프 높이보다 안쪽에 두며, 벗거나 로드에 실패하면 피부를 복원한다.

양쪽 Foot에 30도 족저굴곡, ToeBase에 반대 방향 30도 보정을 적용한다.
착용 자세에서 만든 부츠를 역스키닝해 공통 bind 자세에 저장했으므로,
정상 착용 실루엣에는 GLB scene extras의 `heel_pose` 적용이 필요하다.
미리보기는 애니메이션 뒤 자세와 밑창 높이를 보정하고, 앉기에는 골반 높이를 유지하는
2본 다리 IK를 적용한다. 적용 전 회전을 복원해 보정 누적을 막으며, 벗으면 맨발 자세로 돌아간다.
공통 몸체·애니메이션 원본은 덮어쓰지 않았다. Blender에는 보정된 기본 자세와 9개 액션을 저장했다.

## 검증과 예산

- [형상 검사](../../assets/items/female_knight_boots/fitted_v4/geometry-validation.json):
  좌우 대칭, 면 방향·UV·가중치·본 대응, 65본 bind, 단위 노멀, 원본·텍스처 보존, 퇴화 면 0개.
- [동작 검사](../../assets/items/female_knight_boots/fitted_v4/runtime-validation.json):
  실제 `bindModularPart`와 14개 클립을 각각 61시점에서 검사했다.
  발 자세 보정·착탈 복원·누적 없음·단일 본 판금의 모서리 길이 유지를 확인했다.
- [브라우저 검사](../../assets/items/female_knight_boots/fitted_v4/browser-review.json):
  정면·측면·후면, 주요 8개 동작과 반복 착탈 확인, 페이지 오류 0개.
- [예산 집계](../../assets/items/female_knight_boots/fitted_v4/assembled-budget.json):
  부츠 양쪽 **17,522삼각형**, 기사 세트·단발 조립 시 숨김 포함 **52,204**, 표시 **42,820**,
  머리·얼굴 배분 **6,527**. 조립 목표 15,000–20,000을 초과한 제작 검토본이며 예산만을 위한 감면은 하지 않았다.

깊은 무릎 굽힘의 검은 관절 간격과 선형 스키닝에 의한 보호대 압축은 남는다.
전용 하이힐 보행, 다른 복장과 혼합 착용, 실제 게임 장착 호환과 출시 예산 정리는 후속 단계다.

## 제작 이력과 정리

| 단계 | 결과와 보관 상태 |
| --- | --- |
| `tripo_v1` | 원본 메시·PBR·생성 기록 보존. 뒤쪽 판금 중복과 굵은 굽을 발견했다. |
| `heel_v1` **[미사용]** | 굽만 가늘게 만든 이전 시도. 후면 재구성에 대체되어 중간 파일 정리. |
| `refined_v2` | 뒤 무릎·뒤꿈치 중복 제거, 긴 굽과 가죽 후면 재구성. `sole_v3` 재생성 입력 GLB·스크립트 보존. |
| `sole_v3` | 사용자 빨간 선에 맞춘 앞발 접지와 아치. 승인된 한쪽 원본·편집본·재현 도구 보존. |
| `fitted_v1` **[미사용]** | 첫 대칭·리깅. 다리가 굵고 발 자세가 평평해 대체. 중간 파일 정리. |
| `fitted_v2` **[미사용]** | 슬림 피팅·실제 높은 굽 자세 적용. 너무 붙는 부분을 후속 조정. 중간 파일 정리. |
| `fitted_v3` **[미사용]** | 1cm 여유는 사용자가 취소. 각도별 세밀한 보정의 뾰족한 경계도 기각했다. 중간 파일 정리. |
| `fitted_v4` | 1mm 여유 기준으로 재피팅한 현재 저장본. |

[밑창 지시 이미지](../../assets/items/female_knight_boots/sole_v3/user-sole-reference.png),
[슬림 윤곽 지시 이미지](../../assets/items/female_knight_boots/references/user-slim.png)를 보존한다.
커밋 요청에 따라 이전 피팅 모델, 중복 Blender·파생 몸체, 로그, 비교 렌더, 임시 보고서,
스크립트 사본을 정리했다. 현재 문서용 정면·측면 이미지와 최종 검증 기록은 남겼다.

## 재현

저장소 루트에서 실행한다. 앞의 두 단계는 승인된 한쪽 원본을 다시 만들 때만 필요하다.
최종 편집본을 다시 렌더할 때는 동작 검사로 보정 샘플을 만든 뒤 Blender를 실행한다.

```bash
.venv/bin/python assets/items/female_knight_boots/refined_v2/refine_boot.py
.venv/bin/python assets/items/female_knight_boots/sole_v3/flatten_forefoot.py
.venv/bin/python tools/fit-female-knight-boots.py
node tools/validate-female-knight-boots.mjs
blender -b --python-exit-code 1 --python tools/blender-scripts/review_female_knight_boots.py
```

생성되는 `heel-animation-offsets.json`, `body-high-heels-review.glb`, 일괄 검수 렌더는
편집본 재현용 중간 산물이다. 출시용 파일 목록에는 포함하지 않는다.
