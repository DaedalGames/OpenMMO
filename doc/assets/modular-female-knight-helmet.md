# 여성 기사 헬멧 원화 — 2026-10-14

사용자가 제공한 여성 기사 이미지의 열린 바이저 헬멧을 참고해 제작했다.
원화에서 정면·후면만 선택해 Tripo 메시 생성을 완료했다. 여성 베이스 피팅·리깅과 개발 미리보기는 아래 기록을 따르며, 게임 아이템 등록은 별도 단계다.

![헬멧 원화](../../assets/items/female_knight_helmet/concept_v1/sheet.png)

- 도구: OpenAI Codex built-in ImageGen, **ChatGPT Pro 20x**, 2026-10-14.
- [사용자 참고 이미지](../../assets/items/female_knight_helmet/concept_v1/user-reference.png): 원저작자·라이선스 미확인.
- 생성 원화: OpenAI 출력물 이용 조건 적용.
- [프롬프트](../../assets/items/female_knight_helmet/concept_v1/prompt.txt), [출처·해시](../../assets/items/female_knight_helmet/concept_v1/sources.json).

은빛 판금, 위로 열린 뾰족한 바이저와 세로 통풍구, 황동 경첩·리벳,
검은 패딩 안감, 얼굴을 드러내는 볼 보호대와 짧게 벌어진 뒷목 테두리를 따른다.
정면·측면 사선·후면을 한 시트에 배치했다. 인물·머리카락·상의 목 보호대는 포함하지 않는다.
후면은 참고 이미지에 보이지 않아 같은 디자인을 바탕으로 보완했다.

2026-10-14 사용자 요청으로 FFmpeg를 사용해 원화를 세로로 3분할했다. 원본과 시점 표기는 유지했다.
[정면](../../assets/items/female_knight_helmet/concept_v1/front.png) ·
[측면](../../assets/items/female_knight_helmet/concept_v1/side.png) ·
[후면](../../assets/items/female_knight_helmet/concept_v1/back.png).
추후 메시 생성 시 각 이미지의 시점 표기를 제외한 입력 영역을 사용한다. 바이저는 열린 상태를 기준으로 하고,
여닫는 기능은 별도 설계가 필요하다. 여성 베이스의 실제 머리 크기, 단발 헤어 가림,
상의 목 보호대와의 겹침은 피팅 단계에서 확인한다. 그림의 비율은 실측 치수가 아니다.

## Tripo 생성 준비 — 2026-10-14

사용자 요청에 따라 정면과 후면만 사용하고 측면은 제외했다. 각 분리 이미지에서
아래 글자를 제외한 높이 760픽셀을 FFmpeg로 추출했다. 전체 헬멧 형상은 유지한다.

- [제작 명세](../../assets/items/female_knight_helmet/tripo_v1/build.json).
- P2-20260801, 삼각형 2,000 목표, detailed PBR, 텍스처 v3.5-20260815, 입력 조명 제거.
- 이전 장갑과 같은 설정의 예상 비용은 120크레딧이다. Tripo 유료 API 크레딧을 사용하며 생성물은 Tripo 이용 조건을 따른다.
- 최초 잔액은 40크레딧으로 부족했다. 사용자 충전 후 [사전 확인](../../assets/items/female_knight_helmet/tripo_v1/preflight.json)에서 잔액 1,040크레딧을 확인하고 제출했다.
- `tools/outfits/tripo.py`로 단일 제출했다. 작업 ID: `0873f512-16c5-4a52-a3b6-b1cec2cc7b89`. [생성 기록](../../assets/items/female_knight_helmet/tripo_v1/generation.json)에 요청과 상태를 보존한다.

## 생성 결과 — 2026-10-14

정면·후면 두 장으로 생성 완료했다. 측면 이미지는 업로드하지 않았다.
**120크레딧 사용**, 완료 후 잔액 **920크레딧**, 보류 0이다.

- [원본 GLB](../../assets/items/female_knight_helmet/tripo_v1/source/model_url.glb)
- [텍스처 내장 Blender 원본](../../assets/items/female_knight_helmet/tripo_v1/source.blend)
- [추출 텍스처·재질 대응](../../assets/items/female_knight_helmet/tripo_v1/source/textures.json)
- [메시 진단](../../assets/items/female_knight_helmet/tripo_v1/review.json), [검수 스크립트](../../assets/items/female_knight_helmet/tripo_v1/review_source.py)
- [정면 렌더](../../assets/items/female_knight_helmet/tripo_v1/review/front.png), [후면 렌더](../../assets/items/female_knight_helmet/tripo_v1/review/back.png), [사선 렌더](../../assets/items/female_knight_helmet/tripo_v1/review/angle.png)

실측 2,166삼각형, 메시 1개, 컬러·노멀·ORM 각각 4096×4096이다.
열린 바이저와 얼굴 입구, 볼 보호대·뒷목 테두리와 경첩·리벳을 렌더에서 확인했다.
퇴화 면·UV 붕괴는 0개다. 임시 용접 기준 연결 성분 17개, 열린 경계 112개이며
진단의 비다양체 집계에도 열린 경계가 포함된다. 밀폐된 솔리드 모델로 판정하지 않는다.
장식·바이저의 실제 분리 상태, 머리 삽입 공간, 여성 베이스와 헤어·목 보호대의 피팅은 아직 미검증이다.
원본 형상·텍스처를 보존했으며 크기 맞춤·리깅·미리보기 장착은 후속 단계다.

## 여성 베이스 피팅·리깅 — 2026-10-14

현재 착용본은 `tripo_v1/fitted_v1/`이다. Tripo 생성 원본과 원본 Blender는 보존했다.

- [피팅 GLB](../../assets/items/female_knight_helmet/tripo_v1/fitted_v1/helmet_female_knight.glb)
- [몸체·상의와 기존 동작이 포함된 Blender](../../assets/items/female_knight_helmet/tripo_v1/fitted_v1/female-knight-helmet-fitted.blend)
- [피팅 기록](../../assets/items/female_knight_helmet/tripo_v1/fitted_v1/fitting.json), [재현 스크립트](../../tools/fit-female-knight-helmet.py)
- [실제 착용 미리보기](../../assets/items/female_knight_helmet/tripo_v1/fitted_v1/review/browser-final.png)

여성 베이스 `rig_v1/female-base.glb`의 실제 머리에 맞춰 원본의 +X 전방을 +Z로 회전했다.
회전 후 축별 배율은 `[0.18, 0.18, 0.155]`, 이동은 `[0, 0.966, -0.002]`다.
여성 몸체 높이 1 기준 제작 좌표이며 실측 미터가 아니다.
기존 65본의 순서·계층·inverse bind를 복사하고 모든 정점은 **Head 100%**로 연결했다.
바이저는 열린 상태로 고정하며 전체 판금이 머리와 함께 움직인다. 별도의 여닫기 본은 없다.
2,166삼각형과 원본 UV·4K 텍스처 바이트를 유지하고 노멀·탄젠트를 다시 계산했다.

얼굴·머리 피부를 삭제하거나 숨기지 않는다. 선택한 헤어는 투구를 정상 착용한 동안 숨기고
투구를 벗거나 로딩에 실패하면 복원한다. 투구 착용 중 헤어를 바꾸면 선택을 기억했다가
벗을 때 표시한다. 미리보기의 `투구` 선택과 `helmet=knight` URL로 착용할 수 있다.
얼굴 확대는 투구까지 들어오도록 프레임을 조정했다.

[리깅 검사](../../assets/items/female_knight_helmet/tripo_v1/fitted_v1/animation-validation.json):
14동작 × 61시점에서 기준 자세, 원본 bind 일치, Head 연결 유지, 금속 모서리 길이 보존과
유한 변형을 확인했다. [GLB 검사](../../assets/items/female_knight_helmet/tripo_v1/fitted_v1/gltf-validation.json)는 오류·경고 0개다.
정지·전투 대기·달리기·베기·앉기·쓰러지기를 정면·측면·후면 렌더로 검토했다.
[브라우저 검사](../../assets/items/female_knight_helmet/tripo_v1/fitted_v1/browser-validation.json)에서
착탈, 헤어 선택 복원, 로딩 실패·재시도, 로딩 중 투구 해제를 확인했다.
프런트엔드 타입 검사·린트도 통과했다. 모든 연속 자세에서 목 보호대와의 무관통을 보장하는 검사는 아니다.

[조립 기록](../../assets/items/female_knight_helmet/tripo_v1/fitted_v1/assembly-counts.json):
기사 투구·상의·하의·부츠·장갑 착용 시 숨김 포함 66,017, 표시 51,538삼각형이다.
헤어는 미표시이며 얼굴 4,604면을 그대로 유지한다. 검·횃불·망토는 별도 합산한다.
기존 캐릭터의 예산 초과에 숫자 맞춤 감축을 적용하지 않았다.
추가 유료 API 호출 없이 로컬에서 피팅·리깅했다.
