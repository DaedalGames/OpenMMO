# 여성 기사 장갑 원화 — 2026-10-13

상의 제작에 사용한 사용자 참고 이미지에서 팔꿈치 보호대·팔뚝 판금·손가락 장갑을 참고했다.
한쪽 장갑의 손등·손바닥 원화를 사용했다. 현재 양손 피팅본은 아래 제작 기록을 따른다.

![장갑 원화](../../assets/items/female_knight_gloves/concept_v2/sheet.png)

[손등](../../assets/items/female_knight_gloves/concept_v2/dorsal.png) · [손바닥](../../assets/items/female_knight_gloves/concept_v2/palm.png)

2026-10-13 사용자 요청으로 FFmpeg를 사용해 원화를 세로로 분할했다. 원본과 시점 표기는 유지한다.

- 도구: OpenAI Codex built-in ImageGen, **ChatGPT Pro 20x**, 2026-10-13.
- 원본 참고: [사용자 이미지](../../assets/items/female_knight_top/concept_v1/user-reference.png). 원저작자·라이선스는 미확인이다.
- 생성 원화: OpenAI 출력물 이용 조건 적용.
- [프롬프트](../../assets/items/female_knight_gloves/concept_v2/prompt.txt), [출처·해시](../../assets/items/female_knight_gloves/concept_v2/sources.json).

장갑 슬롯에 팔꿈치 보호대, 팔뚝 보호대, 손목·손가락 판금과 안쪽 가죽을 포함한다.
보호대 위의 고정 밴드와 천 소매는 상의와 겹쳐 v2에서 제거했다. 장갑은 팔꿈치 보호대부터 시작한다.
은색 금속·식물 음각·황동 리벳·갈색 고정끈은 참고 이미지의 디자인을 따른다.
장갑이 상의 소매를 바깥에서 덮으며 팔꿈치 안쪽은 유연한 소재로 남긴다.

원화는 v2를 사용한다. 원화와 생성 원본은 피팅본과 별도로 보존한다.
프롬프트는 착용자 왼쪽을 지정했으며 실제 3D 좌우와 손가락 본 대응은 제작 시 확인한다.
기준 몸체는 `assets/modular_human_female_01/rig_v1/female-base.glb`, 리그는 `human_female_01_local_v1`이다.
팔꿈치 보호대와 상의 연결부의 치수·가림 범위·지원 조합은 피팅 후 정한다.

**[미사용] v1**: 보호대 위의 밴드와 천이 상의 영역과 중복되었다. 원본과 분할 이미지는 `assets/items/female_knight_gloves/concept_v1/`에 보존했다. v2는 내장 ImageGen으로 해당 윗부분을 제거한 수정본이다.

## Tripo 메시 생성 — 2026-10-13

- 도구·요금: Tripo API, 유료 API 크레딧. 생성물은 [Tripo 이용 조건](https://developers.tripo3d.ai/en/terms)을 따른다.
- [제작 명세](../../assets/items/female_knight_gloves/tripo_v1/build.json), [작업·비용 기록](../../assets/items/female_knight_gloves/tripo_v1/generation.json).
- 작업 ID: `bd7d5e10-8255-4ac9-ad65-21646f90d1c5`. 중복 제출 없이 기존 작업을 조회·회수한다.
- `P2-20260801`, 한쪽 2,000삼각형 목표, detailed PBR, `v3.5-20260815`, 입력 조명 제거.
- v2 원화에서 FFmpeg로 손등 `[0,160,596,1070]`, 손바닥 `[596,160,597,1070]`을 추출해 각각 front/back 입력으로 제출했다. 글자와 위쪽 여백만 제외했다.
- 반대편은 이후 대칭 제작한다. 양쪽 목표 합계는 4,000삼각형이며 생성 후 숫자 맞춤 감축은 하지 않는다. 전체 착용·표시 삼각형 수는 피팅 이후 측정한다.

생성 완료 및 원본 회수: **120크레딧 사용**, 완료 후 잔액 40·보류 0크레딧.

- [Tripo 원본 GLB](../../assets/items/female_knight_gloves/tripo_v1/source/model_url.glb)
- [텍스처 내장 Blender 원본](../../assets/items/female_knight_gloves/tripo_v1/source.blend)
- [분리한 텍스처·재질 대응](../../assets/items/female_knight_gloves/tripo_v1/source/textures.json)
- [메시 진단](../../assets/items/female_knight_gloves/tripo_v1/review.json), [검수 스크립트](../../assets/items/female_knight_gloves/tripo_v1/review_source.py)
- [손등 렌더](../../assets/items/female_knight_gloves/tripo_v1/review/front.png), [손바닥 렌더](../../assets/items/female_knight_gloves/tripo_v1/review/back.png), [사선 렌더](../../assets/items/female_knight_gloves/tripo_v1/review/angle.png)

실측 **2,144삼각형**, 메시 1개, UV 이음 임시 용접 기준 연결 성분 1개다. 반대편 단순 복제 시 4,288삼각형이다.
컬러·노멀·ORM은 각각 4K이며 GLB와 Blender에 내장하고 원본 이미지 바이트도 별도로 추출했다.
팔꿈치 보호대부터 손가락까지의 형상, 다섯 손가락과 손바닥 가죽·고정끈을 렌더에서 확인했다.
원화에서 제거한 보호대 위 밴드와 소매는 생성되지 않았다.

퇴화 면·UV 붕괴는 0개다. 임시 용접 진단에서 경계 모서리 4개와 비다양체 모서리 12개가 있어
피팅 전 해당 위치를 점검해야 한다. 현재 파일은 생성 원본이며 속 빈 입구, 손가락 사이 분리,
여성 몸체 착용, 대칭 제작, 리깅·동작 및 상의 소매와의 겹침은 아직 검증하지 않았다.

## 양손 피팅과 미리보기 — 2026-10-14

위 한계는 Tripo 생성 원본의 상태다. 최초 양손 피팅본은 `tripo_v1/fitted_v1/`이며, 현재 미리보기는 아래 `fitted_v3/` 팔꿈치 관절 수정본을 사용한다.

- [양손 GLB](../../assets/items/female_knight_gloves/tripo_v1/fitted_v1/gloves_female_knight.glb)
- [몸체·상의·장갑·기존 동작을 포함한 Blender](../../assets/items/female_knight_gloves/tripo_v1/fitted_v1/female-knight-gloves-fitted.blend)
- [피팅 데이터·방법](../../assets/items/female_knight_gloves/tripo_v1/fitted_v1/fitting.json), [재현 스크립트](../../tools/fit-female-knight-gloves.py)
- [착용 미리보기](../../assets/items/female_knight_gloves/tripo_v1/fitted_v1/review/browser-final.png)

오른쪽을 먼저 피팅·리깅하고 동작 검사를 거친 뒤 반대편을 제작했다. 여성 베이스의
양손 손가락 기준 자세가 달라, 반사한 디자인을 실제 왼손 본 위치와 피부 표면에 다시 맞췄다.
기존 65본의 순서·계층·inverse bind를 그대로 사용하고 체형과 원본 동작은 변경하지 않았다.

팔꿈치 안쪽에서 겹친 라이닝 74면을 제거했다. 한쪽 2,070, 양쪽 **4,140삼각형**이다.
삼각형 수를 목표에 맞추기 위한 감축은 하지 않았다. UV와 4K 컬러·노멀·ORM 이미지 바이트는 유지한다.
양쪽 모두 비다양체 모서리·퇴화 면 0개이며, 보호대 안쪽의 열린 경계 66개가 남는다.
밀폐된 솔리드 모델로 취급하지 않는다.

손가락은 메시의 연결 관계로 구분해 각 손가락 본에 맞췄다. 손바닥 연결부는 ARAP으로
형상을 보정하고, 엄지·손바닥·손가락 사이 웨이트를 메시 연결 방향으로 부드럽게 이었다.
팔뚝 판금과 보호대는 같은 쪽 ForeArm을 따라 강성을 유지한다.
기준 몸체에서 손가락 약 0.0016, 팔뚝 0.004, 보호대 0.008의 제작 좌표 여유를 적용했다.
몸체 높이 1의 좌표이며 실측 미터로 해석하지 않는다.

장갑 착용 시 몸체 4,375면, 같은 기사 상의의 소매 568면을 가린다.
상의와 장갑의 착용 순서에 관계없이 적용하며, 벗기기·로딩 실패 시 피부와 소매를 복원한다.
몸체·상의 원본에 영구 삭제를 적용하지 않는다. 미리보기의 `장갑` 선택에서 착탈한다.

개발 서버 경로:
`/modular-character-preview.html?character=female&top=knight&gloves=knight&camera=upper`.
게임 아이템 등록이나 생산 서버 배포는 포함하지 않는다.

### 검증

- [런타임 본 결합·동작·가림 검사](../../assets/items/female_knight_gloves/tripo_v1/fitted_v1/animation-validation.json): 양손 × 14동작 × 33시점. 기준 자세와 bind 일치, 정규화 웨이트, 반대쪽 본 영향 없음, 유한 변형 확인. 길이 0.0015 이상 모서리의 최대 길이 비율 약 2.53, 같은 본을 따르는 판금 모서리 길이는 유지된다.
- [GLB 검사](../../assets/items/female_knight_gloves/tripo_v1/fitted_v1/gltf-validation.json): 오류·경고 0개.
- [브라우저 검사](../../assets/items/female_knight_gloves/tripo_v1/fitted_v1/browser-validation.json): 착용, 8개 기본 동작, 검·횃불, 오른손·왼손 확대 확인.
- [실패·복원 검사](../../assets/items/female_knight_gloves/tripo_v1/fitted_v1/failure-validation.json): 로딩 실패 시 이전 몸체·소매 유지, 재시도, 로딩 중 선택 변경, 착탈 후 원래 삼각형 수 복원.
- 프런트엔드 `npm run check`, `npm run lint` 통과.
- [같은 팔 피부와의 접촉 측정](../../assets/items/female_knight_gloves/tripo_v1/fitted_v1/clearance-validation.json): 각 손 126시점. 가림 전 피부와의 내부 접촉은 남는다. 손 약 −0.0054, 팔뚝 −0.0126, 보호대 −0.0169의 최소 부호 거리를 기록했으며, 모든 면의 무관통을 보장하는 검사는 아니다. 다른 상의·혼합 장갑 조합은 미검증이다.

[조립 삼각형 기록](../../assets/items/female_knight_gloves/tripo_v1/fitted_v1/assembly-counts.json):
몸체·단발·기사 상의·하의·부츠·양손 장갑은 숨김 포함 **65,734**, 표시 **51,407**삼각형이다.
얼굴 4,604면은 유지한다. 맨손 장착 상태 기준이며 검·횃불·방패·망토는 별도 합산한다.
기존 몸체와 장비부터 조립 예산을 넘고 있어, 이 작업에서 수치 맞춤 감축은 하지 않았다.

### 수정 이력

- **[미사용] 전체 손 RBF 변형**: 손가락 깊이 차이와 엄지 연결부에서 접힘·돌출이 생겼다. 손가락 단면 대응과 ARAP 연결부 보정으로 교체했다.
- **[미사용] 손가락별 단절 웨이트**: 엄지와 손바닥 경계의 작은 모서리가 쓰러지기 동작에서 약 8.37배 늘어났다. 연결부 웨이트를 부드럽게 이어 최대 약 2.53배로 줄였다.
- 소매 끝이 팔뚝 보호대 밖으로 나오던 문제는 장갑 착용 시 소매 가림으로 수정했다.
- 횃불 자세의 왼손 확대에서 정지 자세 경계구를 사용한 화면 밖 판정으로 장갑이 사라졌다. 미리보기 장갑은 해당 판정을 비활성화해 움직인 손을 표시한다.
- 로컬 피팅·리깅·대칭 제작에는 추가 유료 API 호출이 없다. 원화·Tripo 원본·현재 Blender 편집본을 보존한다.

## 팔꿈치 보호대와 장갑 입구 축소 — 2026-10-14

사용자 착용 화면에서 보호대와 장갑 입구가 팔에 비해 과하게 벌어진 것을 확인했다.
**[미사용] fitted_v1**은 비교용으로 그대로 보존하고, 현재 착용본을 `tripo_v1/fitted_v2/`로 교체했다.

- 팔꿈치 보호대 최대 반경은 양쪽 모두 약 **30.3%**, 팔뚝 장갑 입구는 약 **25.9%** 줄였다.
- 원본 세로 좌표에 따른 반경 배율을 `[.24, .32, .38, .38]`에서 `[.24, .25, .265, .265]`로 변경했다. 길이와 손가락 대응 방식은 유지하고 ARAP 및 표면 여유 보정을 다시 적용했다.
- 4,140삼각형, 65본, UV·텍스처 바이트와 몸체·소매 가림 범위는 유지한다. 원본, 기존 피팅 Blender, 새 Blender를 각각 보존한다.
- [치수 비교](../../assets/items/female_knight_gloves/tripo_v1/fitted_v2/size-comparison.json), [피팅 기록](../../assets/items/female_knight_gloves/tripo_v1/fitted_v2/fitting.json).
- [현재 양손 GLB](../../assets/items/female_knight_gloves/tripo_v1/fitted_v2/gloves_female_knight.glb), [Blender 편집본](../../assets/items/female_knight_gloves/tripo_v1/fitted_v2/female-knight-gloves-fitted.blend), [브라우저 착용 화면](../../assets/items/female_knight_gloves/tripo_v1/fitted_v2/review/browser-final.png).

양손 × 14동작 × 33시점의 [리깅·동작 검사](../../assets/items/female_knight_gloves/tripo_v1/fitted_v2/animation-validation.json)를 통과했다.
[GLB 오류·경고](../../assets/items/female_knight_gloves/tripo_v1/fitted_v2/gltf-validation.json)는 0개다.
정지·무장 대기·달리기·베기·앉기 렌더와 실제 브라우저의 양손 확대를 확인했다.
[브라우저 검사](../../assets/items/female_knight_gloves/tripo_v1/fitted_v2/browser-validation.json)에서 런타임 오류는 없었다.
가림 전 피부의 내부 접촉 한계는 계속 적용하며, [축소본 측정](../../assets/items/female_knight_gloves/tripo_v1/fitted_v2/clearance-validation.json)에 별도로 기록한다.
추가 유료 API 호출 없이 로컬 피팅으로 수정했다.

### 장갑 착용 시 상의 소매 끝 정리 — 2026-10-14

사용자가 표시한 검은 조각은 상의를 해제했을 때 사라지는 것으로 확인한 상의 소매 끝이다.
장갑을 착용했을 때 소매 가림의 팔 축 기준을 `+0.005`에서 `−0.025`로 올려,
보호대 밖으로 길게 나온 삼각형을 제거했다. 양쪽 소매 가림은 568면에서 720면으로 증가했다.
장갑을 벗으면 상의 소매가 복원된다. 장갑 메시·텍스처·리그와 원본 상의 GLB는 그대로다.
너무 높이 자른 `−0.040` 후보는 보호대 위에 틈을 만들어 채택하지 않았다.

[수정 전](../../assets/items/female_knight_gloves/tripo_v1/fitted_v2/review/sleeve/before.png) ·
[상의 제거로 원인 확인](../../assets/items/female_knight_gloves/tripo_v1/fitted_v2/review/sleeve/without-top.png) ·
[수정 후](../../assets/items/female_knight_gloves/tripo_v1/fitted_v2/review/sleeve/after.png).
기존 마스크와 Blender는 `fitted_v2/sleeve-before-trim/`에 비교용으로 보존했다.
현재 Blender에 소매 가림을 반영하고 팔을 굽히는 렌더를 다시 확인했다.
조립 표시 삼각형 수는 51,255이며, 숨김 포함 65,734와 얼굴 4,604는 유지한다.

## 전투 대기 팔꿈치 관절 수정 — 2026-10-14

**[미사용] fitted_v2**는 팔꿈치 보호대까지 ForeArm 100%로 묶여 있었다. 깊게 굽히면
보호대 윗부분이 위팔에서 떨어지고, 짧아진 소매와 몸체 가림 사이로 빈 내부가 보였다.
기존의 본 호환·변형 수치 검사는 이 시각적 연결 문제를 검출하지 못했다.
현재 착용본은 `tripo_v1/fitted_v3/`이며 v2 원본과 Blender는 비교용으로 보존한다.

- 보호대는 같은 쪽 Arm 55%·ForeArm 45%로 움직인다. 원본 높이 0.16–0.30 구간에서 부드럽게 연결하고, 아래팔 판금과 손가락 웨이트는 유지한다. 선형 스키닝이므로 보호대 전체를 완전한 강체로 취급하지 않는다.
- 기존 여성 베이스의 팔꿈치 표면에서 검은 천 안감을 만들고, 기존 Arm/ForeArm 웨이트를 이어 받았다. 표면 여유는 몸체 높이 1 기준 0.0008이다. 원본 몸체의 출처·이용 조건을 그대로 따르며 별도의 생성 API는 사용하지 않았다.
- 안감은 절차적 어두운 단색 PBR 재질이다. 기존 장갑의 UV·4K 텍스처 바이트를 유지한다.
- 기존 장갑 4,140면 + 안감 553면 = **4,693삼각형**, 65본이다. 현재 조립은 숨김 포함 66,287, 표시 51,808이며 얼굴 4,604면은 유지한다.
- 소매 가림 720면과 착탈 시 복원 동작을 유지한다.

[현재 GLB](../../assets/items/female_knight_gloves/tripo_v1/fitted_v3/gloves_female_knight.glb) ·
[Blender](../../assets/items/female_knight_gloves/tripo_v1/fitted_v3/female-knight-gloves-fitted.blend) ·
[피팅 기록](../../assets/items/female_knight_gloves/tripo_v1/fitted_v3/fitting.json) ·
[전투 대기 실제 미리보기](../../assets/items/female_knight_gloves/tripo_v1/fitted_v3/review/combat-browser/Left-1.png).

전투 대기의 시작·중간 시점을 양팔 앞뒤에서 추가 렌더했다. 실제 브라우저에서도 같은 동작을
양팔 앞뒤에서 확인했다. [14동작 × 33시점 검사](../../assets/items/female_knight_gloves/tripo_v1/fitted_v3/animation-validation.json),
[착탈·로딩 실패·복원 검사](../../assets/items/female_knight_gloves/tripo_v1/fitted_v3/failure-validation.json)를 통과했다.
[GLB 검사](../../assets/items/female_knight_gloves/tripo_v1/fitted_v3/gltf-validation.json)는 오류·경고 0개다.
가려진 내부 면의 접촉과 모든 연속 시점의 무관통을 보장하는 검사는 아니다.
