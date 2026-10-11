# 바드 부츠 — Tripo 피팅·대칭 제작 v1

2026-10-11. 사용자 제공 오른발 부츠 한 짝을 현재 남성 몸체에 피팅하고 반대쪽을 대칭 제작했다.
기존 65본 리그를 연결하고 개발 미리보기의 바드 세트에 추가했다. 게임 아이템 등록·배포는 별도다.

- [두 짝 피팅 GLB](../../assets/modular_human_male_01/bard/tripo_boots_v1/boots_bard.glb)
- [편집용 Blender](../../assets/items/bard_starter/tripo_boots_v1/bard-boots-fitting.blend)
- [사용자 원본](../../assets/items/bard_starter/tripo_boots_v1/source.glb)
- [원본 출처·텍스처 기록](../../assets/items/bard_starter/tripo_boots_v1/source.json)
- [피팅 명세](modular-bard-tripo-boots-fitting-v1.json)
- [실제 런타임 바인드·동작·착탈 검사](modular-bard-tripo-boots-animation-v1.json)
- [원본 보존·대칭·입구 단면 검사](modular-bard-tripo-boots-validation-v1.json)
- [Blender 편집본·검수 렌더 기록](modular-bard-tripo-boots-fitted-review-v1.json)

## 원본과 출처

사용자가 `Y:\public\web_downloads\leather+boot+3d+model (1).glb`로 전달했다.
이 환경의 원본 경로는 `/mnt/y/web_downloads/leather+boot+3d+model (1).glb`다.
원본은 수정하지 않고 항목 폴더에 같은 바이트로 복사했다.

GLB generator는 Tripo이며 한 짝 1,703삼각형, UV·노멀 이음 중복 포함 2,064정점,
메시·재질 각 1개, 내장 2048×2048 JPEG 텍스처 1개다. 리그는 없었다.
제안한 800쿼드≈1,600삼각형 대비 약 6.4% 많으며 원래 쿼드 수와 생성 설정은 미확인이다.
입구는 열려 있고 가죽 커프 안쪽 면이 있다. 용접 진단상 연결 성분 12개와 열린 모서리 59개가
있으며 끈·버클 등의 분리된 부품과 입구를 포함한다. 퇴화 면과 붕괴 UV 삼각형은 0이다.
[원본 진단](../../assets/items/bard_starter/tripo_boots_v1/source-review.json)을 보존했다.

입수일은 2026-10-11이다. 정확한 생성일·작업 ID·모델 버전·실제 입력 이미지·프롬프트·
구독 등급은 미확인이다. 사용자 제공 Tripo 출력물과 생성 계정의 이용 조건을 따른다.
참조 원화는 [부츠 제작 기록](modular-bard-parts.md#부츠-한-짝-정면측면-원화--2026-10-11)의
OpenAI Codex built-in ImageGen, **ChatGPT Pro 20x**, 2026-10-11 기록을 따른다.

## 피팅과 보정

현재 `assets/modular_human_male_01/fitted/base.glb`,
`human_male_01_mixamo_candidate_v2`, `interfaces/v1`을 기준으로 제작했다.
실제 종아리 단면에 맞춰 가죽 몸통과 커프의 여유를 조정했다. 처음에는 발등·발끝·뒤꿈치의
피부가 노출돼 발 방향과 폭을 맞추고 발 표면에 대해 정점·면 중심·모서리 중점 여유를 보정했다.
피부를 숨기지 않은 정면·측면·후면·위쪽 렌더에서도 보정 결과를 확인했다.

원본 면 연결·UV·내장 텍스처를 유지했다. 왼발은 오른발을 X축 대칭하고 삼각형 방향과
좌우 본 대응을 바꿨다. 두 짝 합계는 **3,406삼각형**이며 목표 수를 맞추기 위한 데시메이션은 하지 않았다.
종아리는 같은 쪽 Leg, 발목·발끝은 Foot·ToeBase로 부드럽게 연결된다.

초기 바지 밑단 처리에서 후면 커프 위쪽 관통을 발견했다. 부츠 입구 Y=0.445–0.525m의
17단면 × 128방향에서 안쪽 반경의 최솟값을 구하고, 바지 밑단을 Y=0.445m까지 넣었다.
입구 구간은 Leg에 고정하고 Y=0.535m 이후부터 원래 바지로 부드럽게 이어진다.
이 처리는 착용 시 생성하는 바지 사본에만 적용하며 원본 바지 GLB는 유지한다.

## 검증과 보관

- 원본 면 연결·UV·텍스처 바이트 보존, 정확한 좌우 대칭·면 방향, 같은 쪽 본 영향,
  기존 65본 계층·inverse bind 일치를 검사했다. 가중치 합 최대 오차는 0이다.
- 실제 `bindModularPart`와 게임의 대기·걷기·달리기·점프·전투 대기·베기·앉기
  7종 × 13시점 = 91자세에서 좌표 유한성, 부츠 UV 이음의 벌어짐 0, 밑단의 Leg 상대 위치를 확인했다.
- 기준 자세와 91자세에서 양쪽 입구 각각 5단면 × 64방향, 총 920단면을 검사했다.
  비교 가능한 광선의 음수 여유는 0이며 최소 여유는 약 8.21mm다.
  열린 커프 위쪽의 부츠 교차 누락 6,827광선은 별도 기록했다. 이를 닫힌 면으로 간주하지 않았다.
- 부츠 착탈·재착용·에셋 누락 때 바지 원본과 맨발의 복원을 확인했다.
- `npm run check`, `npm run lint`, 관련 4개 테스트 파일의 129개 테스트를 통과했다.

전체 보관 GLB 합계는 몸체 13,891 + 헤어 934 + 상의 5,201 + 하의 3,017 + 부츠 3,406 =
**26,449삼각형**이다. 현재 개발 미리보기의 가림·바지 처리 후 실제 표시 합계는
**18,004삼각형**, 숨김 포함 런타임 합계는 24,003삼각형이다. 얼굴 1,505삼각형은 유지했다.
장갑·악기는 이 합계에 포함하지 않는다. 보관 합계는 조립 목표 15,000–20,000보다 크므로
최종 장비·가림 확정 시 다시 집계한다.

Blender 편집본에는 텍스처, 기준 몸체·바드 세트, 런타임에서 넣어 입힌 바지 사본,
숨긴 사용자 원본·연결부 가이드, 게임 자세 표본을 포함했다. 타임라인은 고정 자세 표본이며
연속 애니메이션이 아니다. 사용자 검수 완료 후 비교·검수 이미지, 생성 이미지의 중복 사본,
임시 바지 검수 GLB와 자세 표본 JSON을 삭제했다. 원본·최종 GLB·Blender·원화·검증 결과는 보존했다.
모든 연속 프레임의 면 충돌과 다른 세트 장비의 혼합 호환은 미검증이다.

재현 순서는 `tools/fit-tripo-bard-boots.py`, `tools/validate-bard-boots.mjs`,
`tools/validate-tripo-bard-boots.py`, `tools/blender-scripts/review_tripo_bard_boots.py`다.
Python은 프로젝트 `.venv`를 사용하고 Blender 검수에는 `--images`로 저장소 밖 경로를 지정한다.
삭제한 바지 사본과 자세 표본은 `validate-bard-boots.mjs` 실행으로 다시 생성한다.
