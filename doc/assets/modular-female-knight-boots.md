# 여성 기사 판금 부츠

2026-10-13. 현재 착용 검토본은 `fitted_v5`다. 한쪽 판금 부츠를 좌우 대칭 제작하고
여성 기준 몸체의 65본 리그에 연결했다. 허벅지·종아리는 1mm 여유를 기준으로 피팅하며,
허벅지 입구는 피부 돌출을 막도록 추가 여유를 둔다. 착용 중에는 발목·발가락과 접지를
높은 굽 자세에 맞춰 보정한다.

## 현재 실루엣 보정본

사용자가 제공한 [목표](../../assets/items/female_knight_boots/references/user-side-target.png),
[곡선 표시](../../assets/items/female_knight_boots/references/user-side-curves.png),
[수정 전 화면](../../assets/items/female_knight_boots/references/user-side-before.png)을 기준으로
기존 `fitted_v4`의 착용 자세에서 메시를 수정했다. 참고 이미지의 원저작자·라이선스는
미확인이며 형상 참고로만 사용했다. 새 이미지·텍스처 생성이나 유료 API 호출은 없다.

- 노란 선: 발등에서 발끝으로 이어지는 윗면을 완만하게 연결하고, 납작한 쐐기형 발끝에 둥근 높이를 준다.
- 빨간 선: 뒤쪽 종아리 부피를 정리하고, 굽 위 발목 구간에 오목한 곡선을 만든다.
- 파란 선: 정강이 앞면을 거의 곧게 유지하면서 아래쪽 굴곡을 약하게 만든다.

첫 v5에서는 앞 정강이의 오목한 부분을 충분히 펴지 않고 뒤 종아리를 과하게 줄여,
사용자가 앞뒤 곡선이 바뀐 것처럼 보인다고 지적했다. [추가 윤곽 지시](../../assets/items/female_knight_boots/references/user-side-correction.png)에
맞춰 앞 정강이를 발끝 방향(+Z)으로 채우고, 뒤 종아리(-Z)의 부피를 복원했다.
뒤쪽 오목한 구간은 발목 높이에 두며, 둥근 발끝과 발등 보정은 유지한다.

이후 [앞코·밑창 윤곽 지시](../../assets/items/female_knight_boots/references/user-toe-sole-outline.png)에
맞춰 앞코를 제작 좌표 약 0.01593만큼 줄여 짧고 뭉툭하게 만들었다. 앞발 높이를 최대
0.0015 더하고 아치의 밑면을 최대 0.0035 뒤쪽으로 넓혔다. 굽 위의 뒤꿈치 경계는
뒤쪽으로 올라가는 사선으로 변형했다. 접지 높이와 가는 힐 끝, 발목 위 0.10 이상의
형상은 유지했다. 이번 추가 수정은 UV·면·가중치·텍스처를 바꾸지 않는 좌표 변형이다.
[측면 확대](../../assets/items/female_knight_boots/fitted_v5/browser/foot-side.png)와
[사선 확대](../../assets/items/female_knight_boots/fitted_v5/browser/foot-angle.png)에서 확인할 수 있다.

[정면 발목 지시](../../assets/items/female_knight_boots/references/user-front-ankle-alignment.png)에
맞춰 발목 아래의 수직 중심선을 정강이 기울기에 맞게 수정했다. 제작 높이 0.13–0.24의
정강이 단면 중심을 직선으로 근사하고 발목·발등·앞코·힐을 그 연장선에 맞췄다.
0.10–0.165 구간에서 보정을 부드럽게 연결하며 좌우 이동만 적용하므로 기존 측면 윤곽과
접지 높이는 유지된다. [수정된 정면](../../assets/items/female_knight_boots/fitted_v5/browser/ankle-front.png)을
기준으로 양쪽을 대칭 검토했고, 14개 동작의 발끝 이음새 검사를 다시 통과했다.

[발 가로선 지시](../../assets/items/female_knight_boots/references/user-level-foot-crossline.png)의
기울기는 정지 메시의 변형이 아니라 대기 애니메이션의 발 본 회전에서 확인됐다.
정지·일반 대기·무장 대기·전투 대기와 대응하는 횃불 동작에서 부츠의 접지 평면을 수평으로
보정한다. 발목 위치와 발이 향하는 방향을 유지하고, 걷기·달리기·점프·공격·죽기·앉기에는
이 보정을 적용하지 않는다. 매 프레임 원래 회전을 복원하므로 착탈이나 동작 전환으로
보정이 누적되지 않는다. Blender의 동작과 검증 기록도 함께 갱신했다.
[대기 자세 후면](../../assets/items/female_knight_boots/fitted_v5/browser/standing-rear.png)을 보존한다.
밑창의 좌우 정점 489쌍을 검사했고, 보정 대상 6개 동작의 최대 높이차/폭 비율은 2.55e-6 이하다.

이어 [대기 자세의 수직 힐 지시](../../assets/items/female_knight_boots/references/user-upright-standing-heel.png)에
맞춰 가는 힐 기둥은 정강이 연장선에서 분리했다. 아래 기둥을 뒤꿈치 아래의 수직 축에
맞추고 제작 높이 0.01–0.065에서 기존 뒤꿈치 컵으로 부드럽게 연결했다. 부츠 본체·앞코·
발목은 그대로이며, 힐의 접지 높이와 UV·텍스처·가중치도 유지했다. 대기 자세에서는
앞코와 힐의 접지 평면을 함께 수평으로 맞춰 기둥이 앞뒤·좌우로 기울지 않도록 한다.

[뒤꿈치 컵 표시](../../assets/items/female_knight_boots/references/user-rounded-cup-before.png)와
[추가 참고 이미지](../../assets/items/female_knight_boots/references/user-rounded-cup-reference.png)에
맞춰 빨간 부분의 컵을 뒤쪽으로 둥글게 채우고, 노란 부분의 굽 연결부는 안으로 들어가게
수정했다. 제작 높이 0.016–0.070에서 뒤쪽 곡면만 변형하며, 최대 컵 확장은 0.004,
굽 연결부의 최대 후퇴는 0.006이다. 가는 힐 기둥과 접지 높이, 앞코·발목·정강이는
유지했다. 참고 이미지는 사용자가 제공했으며 원저작자·라이선스는 미확인이다.
형상 참고로만 사용했고 새 이미지·텍스처 생성은 없다.
이어 [곡선 정리 지시](../../assets/items/female_knight_boots/references/user-smooth-heel-curve.png)에
따라 굽 연결부의 잔굴곡을 삼차 스플라인으로 정리했다. 제작 높이 0.014–0.044의
후면 단면이 역방향으로 꺾이지 않는지 검사했고, 컵과 아래 기둥으로 부드럽게 연결했다.
정점 수·UV·가중치를 유지하며 뒤쪽 좌표와 법선만 보정했다.
마지막 [미세 보정 지시](../../assets/items/female_knight_boots/references/user-fine-heel-curve.png)는
빨간 위쪽 곡선을 바깥으로, 파란 아래쪽 곡선을 안으로 소폭 옮기는 것이다.
스플라인 제어점과 아래쪽 접선만 조정했고, 직전 커밋 대비 실제 정점의 최대 이동은
제작 좌표 0.0002931이다. 힐 아래쪽과 나머지 부츠의 정점은 유지했으며,
후면 단면이 역방향으로 꺾이지 않는지와 14개 동작을 다시 검사했다.
추가 [파란 구간 지시](../../assets/items/female_knight_boots/references/user-blue-heel-trim.png)에
맞춰 제작 높이 0.002–0.023의 굽 뒤쪽 절반만 최대 0.00018 안으로 깎았다.
양 끝의 이동량을 부드럽게 줄였으며, 위쪽 컵·굽 연결부와 하단 접지부의 정점은
직전 상태와 동일하다. 형상 대칭·UV·리그 유지와 14개 동작 검사를 통과했다.

이어 [빨간 밑창 윤곽 지시](../../assets/items/female_knight_boots/references/user-red-sole-arch.png)에
맞춰 앞바닥에서 굽 위 연결부로 올라가는 아치를 굽 방향으로 채웠다. 제작 높이
-0.0302–0.040의 밑면을 부드러운 곡선으로 최대 0.00706 이동하고 발등 쪽으로 보정을
줄였다. 양쪽에 대칭 적용했으며 접지부·가는 힐·상단 부츠의 정점은 직전 상태와 같다.
UV·면 구성·텍스처·가중치를 유지했고, 면 뒤집힘·좌우 대칭·14개 동작 검사와 측면·사선
브라우저 검토를 통과했다. 사용자 제공 화면을 형상 참고로 사용한 로컬 메시 수정이며
추가 생성 비용은 없다. GLB와 Blender 편집본을 함께 갱신했다.

다음 [파란 화살표 지시](../../assets/items/female_knight_boots/references/user-blue-plate-extension.png)는
판금 무늬의 끝을 밑창 쪽으로 미는 수정이다. 무늬와 입체 테두리가 함께 이동하도록
제작 높이 0–0.058의 안쪽 판금 경계를 굽 방향으로 최대 0.004752 늘렸다.
밑창 외곽의 300개 높이 단면은 이전과 동일하며, 힐·접지부·상단 부츠도 유지했다.
UV와 원본 PBR 텍스처는 그대로 사용해 무늬·금속성·노멀의 대응을 보존했다.
양쪽 대칭과 면 뒤집힘 검사, 14개 동작 검사 및 측면·사선 브라우저 검토를 통과했다.

이어 [네이비 재질 지시](../../assets/items/female_knight_boots/references/user-navy-cuff-material.png)에
따라 허벅지 바깥쪽의 검은 표면을 무릎 뒤쪽과 같은 `concept_knee_leather` 재질로 바꿨다.
한쪽 106면에 기존 가죽 이미지의 진한 네이비 구간을 투영했고, 갈색 끈·버클·은색 테두리는
원래 재질을 유지한다. 새 이미지 생성이나 텍스처 파일 수정은 없다. 삼각형별 위치·법선·
가중치와 리그가 수정 전과 동일한지 확인했고, 14개 동작 검사를 통과했다.
[측면 재질](../../assets/items/female_knight_boots/fitted_v5/browser/cuff-navy-side.png)과
[재질 검증](../../assets/items/female_knight_boots/fitted_v5/material-validation.json)을 보존한다.

텍스처 이미지·재질·65본 리그·높은 굽 자세·허벅지 입구·피부 가림은 유지했다.
발끝 곡면의 국소 분할에서 UV와 가중치를 보간했고, 위쪽 가죽 면은 기존 무릎 재질에
맞게 UV와 재질 지정을 바꿨다. `fitted_v4`에서는 재현 입력인 GLB·피팅·가림·자세 JSON만 보존했다.

- [현재 GLB](../../assets/items/female_knight_boots/fitted_v5/boots_female_knight.glb),
  [Blender 편집본](../../assets/items/female_knight_boots/fitted_v5/female-knight-boots-fitted.blend).
- [측면](../../assets/items/female_knight_boots/fitted_v5/review/rest-side.png),
  [사선](../../assets/items/female_knight_boots/fitted_v5/review/rest-angle.png),
  [미리보기 발 확대](../../assets/items/female_knight_boots/fitted_v5/browser/feet.png).
- [변형·해시 기록](../../assets/items/female_knight_boots/fitted_v5/side-profile.json),
  [동작 검사](../../assets/items/female_knight_boots/fitted_v5/runtime-validation.json),
  [브라우저 검사](../../assets/items/female_knight_boots/fitted_v5/browser-review.json).

14개 동작을 각각 61시점에서 검사했다. 발끝 이음새, 판금의 강체 모서리 길이,
가중치·본 호환, 착탈 복원 검사를 통과했다. 정면·측면·후면과 걷기·달리기·앉기 렌더를 검토했다.
부츠 양쪽은 **20,586삼각형**이며 기사 세트·단발 조립 시 숨김 포함 **55,268**, 표시 **45,884**이다.
머리·얼굴 배분은 **6,527**로 유지된다. 제작 검토본으로서 기존 조립 예산 초과 상태는 남는다.
옆 실루엣을 수정했으므로 아래 `fitted_v4`의 단면 피부 간격 수치는 현재 형상에 적용하지 않는다.
걷기에서 발목 판금 사이가 벌어지는 기존 현상은 v4와 같은 시점에서 비교 확인했으며 남아 있다.

## v4 피팅 원본과 출처

- [양쪽 리깅 GLB](../../assets/items/female_knight_boots/fitted_v4/boots_female_knight.glb).
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

2026-10-13 발끝 보정: 발끝 판금만 ToeBase에 연결되어 대기 동작에서 발등과 경계가
벌어지는 문제를 수정했다. 발끝도 발등과 같은 Foot 본을 따르며, 높은 굽 착용 자세에서
역스키닝해 승인된 정지 형상·UV·텍스처를 유지한다. GLB와 Blender 편집본을 함께 갱신했다.

2026-10-13 입구 여유 보정: 허벅지 뒤쪽 사선 판금을 피부가 뚫는 현상을 수정했다.
제작 높이 0.34–0.40 구간에서 확장을 부드럽게 늘려, 위쪽 입구는 앞·옆 7mm에서
뒤쪽 최대 14mm까지 바깥으로 이동했다. 이는 추가 이동량이며 최종 피부 간격은 아니다.
8mm와 10mm 균일 확장에서는 걷는 자세의 반대쪽 입구에 작은 교차가 남아,
뒤쪽 여유를 더 주고 앞·옆의 확장을 줄였다. 피부 가림 목록·발끝·종아리 형상은 유지했다.

후속 확대에서 반대쪽 안쪽 사선 판금에 작은 피부 돌출이 남아 있음을 확인했다.
제작 높이 0.40–0.49의 안쪽 후면만 부드럽게 최대 약 2.5mm 더 벌렸다.
가림·가중치·UV·면 구성은 유지했으며 양쪽 후면 사선에서 대기·걷기·달리기를 확인했다.

**1mm는 입력 여유 기준이며 모든 표면의 일정한 실측 거리는 아니다.** 판금 굴곡과
입구 추가 여유 때문에 허벅지·종아리의 표본 전후좌우 간격은 약 0.59–17.01mm다.
이음·사선의 국소 교차에는 착용 중 피부 가림을 적용한다.
[피팅·단면 기록](../../assets/items/female_knight_boots/fitted_v4/fitting.json)을 참고한다.
가림 경계는 각도별 커프 높이보다 안쪽에 두며, 벗거나 로드에 실패하면 피부를 복원한다.

양쪽 Foot에 30도 족저굴곡, ToeBase에 반대 방향 30도 보정을 적용한다.
착용 자세에서 만든 부츠를 역스키닝해 공통 bind 자세에 저장했으므로,
정상 착용 실루엣에는 GLB scene extras의 `heel_pose` 적용이 필요하다.
미리보기는 애니메이션 뒤 자세와 밑창 높이를 보정하고, 앉기에는 골반 높이를 유지하는
2본 다리 IK를 적용한다. 적용 전 회전을 복원해 보정 누적을 막으며, 벗으면 맨발 자세로 돌아간다.
공통 몸체·애니메이션 원본은 덮어쓰지 않았다. Blender에는 보정된 기본 자세와 9개 액션을 저장했다.

## 검증과 예산

최종 [형상 검사](../../assets/items/female_knight_boots/fitted_v5/geometry-validation.json)에서
좌우 대칭 오차는 7.52e-9 이하, 노멀 길이 오차는 5.97e-8 이하다.
[동작 검사](../../assets/items/female_knight_boots/fitted_v5/runtime-validation.json)와
[예산 집계](../../assets/items/female_knight_boots/fitted_v5/assembled-budget.json)는 현재 GLB 기준이다.
이전 v4 검사와 비교 렌더는 정리했으며, 현재 검증 결과와 문서용 측면·사선·발 확대만 보존한다.

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
| `fitted_v4` | 1mm 여유 기준의 피팅 원본. v5 옆 실루엣 보정의 입력으로 보존. |
| `fitted_v5` | 앞뒤 발목 곡선, 짧고 뭉툭한 앞코, 두꺼운 밑창·아치, 사선 뒤꿈치 경계와 정강이에 맞춘 정면 발목 방향을 반영한 현재 저장본. |

[밑창 지시 이미지](../../assets/items/female_knight_boots/sole_v3/user-sole-reference.png),
[슬림 윤곽 지시 이미지](../../assets/items/female_knight_boots/references/user-slim.png)를 보존한다.
커밋 요청에 따라 이전 피팅 모델, 중복 Blender·파생 몸체, 로그, 비교 렌더, 임시 보고서,
스크립트 사본을 정리했다. 문서용 최종 측면·사선·발끝 이미지와 최종 검증 기록은 남겼다.

## 재현

저장소 루트에서 실행한다. 앞의 두 단계는 승인된 한쪽 원본을 다시 만들 때만 필요하다.
최종 편집본을 다시 렌더할 때는 동작 검사로 보정 샘플을 만든 뒤 Blender를 실행한다.

```bash
.venv/bin/python assets/items/female_knight_boots/refined_v2/refine_boot.py
.venv/bin/python assets/items/female_knight_boots/sole_v3/flatten_forefoot.py
.venv/bin/python tools/fit-female-knight-boots.py
.venv/bin/python tools/shape-female-knight-boots.py
node tools/validate-female-knight-boots.mjs
blender -b --python-exit-code 1 --python tools/blender-scripts/review_female_knight_boots.py
```

생성되는 `heel-animation-offsets.json`, `body-high-heels-review.glb`, 일괄 검수 렌더는
편집본 재현용 중간 산물이다. 출시용 파일 목록에는 포함하지 않는다.
