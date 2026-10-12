# 여성 나이트 헤어 원화

**[미사용 · 보관] 2026-10-12:** 사용자 요청으로 긴 헤어의 추가 작업을 보류했다.
원화·Tripo 원본·후면 보정본·피팅 GLB·Blender 편집본과 재현 스크립트를 보존한다.
미리보기에서는 기본 착용을 해제하고 `긴 금발 (보관본)`으로 선택할 때만 표시한다.
다음 버전은 어깨에 닿지 않는 턱 아래 길이의 금발 헤어로 진행한다.

단발 [정면 원화 v2](../images/characters/modular_human_female_01/parts/knight/hair_female_knight-bob-front-v2.png)를
OpenAI Codex built-in ImageGen, **ChatGPT Pro 20x**로 2026-10-12 보정했다.
사용자 지적에 따라 가운데 투명 구멍을 조금 어두운 금발 머릿결로 채워 후면 안쪽 면을 나타냈다.
외곽 배경의 투명도와 기존 단발 실루엣을 유지했다. Tripo 후면 검수 결과는 아래에 기록했다.
[v2 프롬프트·출처·해시](modular-female-knight-bob-front-v2-sources.json).
**[미사용]** 가운데가 뚫린 [v1 원화](../images/characters/modular_human_female_01/parts/knight/hair_female_knight-bob-front-v1.png)와
[최초 생성 기록](modular-female-knight-bob-sources.json)은 보존한다.
같은 도구·등급·날짜로 보정 정면을 참고한 [측면](../images/characters/modular_human_female_01/parts/knight/hair_female_knight-bob-side-v2.png)과
정면·측면을 함께 참고한 [후면](../images/characters/modular_human_female_01/parts/knight/hair_female_knight-bob-back-v2.png)을 생성했다.
측면은 화면 왼쪽을 보며, 후면은 정수리부터 짧은 끝부분까지 머릿결이 연속되는 형태다.
바깥 배경만 투명하게 유지했다. [측면·후면 프롬프트·해시 기록](modular-female-knight-bob-views-v2-sources.json).
시점 간 정확한 직교 기하 일치는 보장하지 않는다. Tripo 생성과 단발 피팅·리깅은 아래 기록을 따른다.

### 단발 Tripo 생성 v1 (2026-10-12)

사용자 요청으로 보정된 단발 v2의 정면·오른쪽 측면·후면 3장을 Tripo API에 제출했다.
도구·등급은 Tripo 유료 API 크레딧이며, 출처·이용 조건은 위 원화 기록과
[Tripo 이용 조건](https://developers.tripo3d.ai/en/terms)을 따른다.
`P2-20260801`, 목표 2,500삼각형, `quad=false`, PBR 상세 텍스처,
`v3.5-20260815`를 사용한다. 헤어 파츠 예산으로, 기존 몸체·얼굴은 변경하지 않는다.

- 작업 ID: `fb994e78-cb1a-4fab-aa0f-2bea9e599fc5`.
- [제작 명세](modular-female-knight-bob-tripo-v1-build.json), [요청·작업·비용 기록](modular-female-knight-bob-tripo-v1-sources.json).
- 입력은 [Tripo 다중 시점 API](https://developers.tripo3d.ai/en/docs/generation-multiview-to-model/p)의 `front`/`right`/`back` 슬롯으로 전달했다.
- 상태: 생성 성공, **120크레딧 사용**, 잔액 **520크레딧**, 보류 **0크레딧**.

[원본 GLB](../../assets/modular_human_female_01/hair/tripo_knight_bob_v1/model_url.glb)와
[텍스처 내장 Blender 편집본](../../assets/modular_human_female_01/hair/tripo_knight_bob_v1/source.blend)을 저장했다.
최종 **2,491삼각형**, 메시 1개, 임시 용접 진단 기준 연결 성분 1개,
4K 컬러·노멀·ORM 텍스처다. 원본 메시를 수정하거나 감축하지 않았다.

[로컬 단발 단독 미리보기](http://localhost:10005/modular-character-preview.html?asset=female-knight-bob)에서
회전·확대, 정면/측면/후면/정수리 전환, 자동 회전과 와이어프레임을 사용할 수 있다.
여성 캐릭터 화면의 `새 단발 헤어 단독 보기` 링크로도 이동한다. 이 화면은 피팅 전 원본을 보여준다.

- [정면](../../assets/modular_human_female_01/hair/tripo_knight_bob_v1/review/front.png) · [측면](../../assets/modular_human_female_01/hair/tripo_knight_bob_v1/review/side.png) · [후면](../../assets/modular_human_female_01/hair/tripo_knight_bob_v1/review/back.png) · [상단](../../assets/modular_human_female_01/hair/tripo_knight_bob_v1/review/top.png).
- [기하·후면 검사 기록](modular-female-knight-bob-tripo-v1-review.json).
- 정수리와 후면 중앙이 채워졌다. 중앙 후면 광선 63/63개가 후면 절반의 표면과 만났다.
  이는 중앙 영역의 덮임 검사이며, 모든 구멍이나 밀폐 상태를 보장하는 검사는 아니다.
- 경계선 188개, 비매니폴드 선 202개(경계선 포함), 퇴화 면·붕괴 UV 각각 0개.
- 정면의 어두운 머릿결이 얼굴 공간 앞쪽의 방패 모양 안쪽 면으로도 생성됐다.
  기존 머리에 피팅하면서 위치를 확인하고 불필요한 내부 면을 정리해야 한다.
  측면·뒤쪽 일부 다발에는 각진 경계와 좁은 틈도 남아 있다.
- 원본 생성 단계에서는 피팅·리깅·게임 등록을 진행하지 않았다. 기존 여성 몸체에 단순 합산하면
  22,175 + 2,491 = 24,666삼각형이며, 실제 조립/가림 합계는 피팅 단계에서 측정한다.

### 단발 피팅·리깅 v1 (2026-10-12)

기존 `rig_v1/female-base.glb` 두상에 맞춰 금발 단발을 피팅했다. 정수리와 앞머리 비율을
유지하고, 아래쪽 끝부분만 부드럽게 올려 턱 아래 길이와 어깨 여유를 확보했다.
얼굴 내부 깊숙이 묻힌 55삼각형을 제거했다. 나머지 UV와 원본 4K 텍스처를 유지했고
데시메이션은 하지 않았다. 최종 **2,436삼각형**, 메시 1개다.

- [리깅 GLB](../../assets/modular_human_female_01/hair/tripo_knight_bob_v1/fitted_v1/hair_female_knight_bob.glb)
- [몸체·텍스처·9개 동작을 포함한 Blender 편집본](../../assets/modular_human_female_01/hair/tripo_knight_bob_v1/fitted_v1/female-knight-bob-fitted.blend)
- [단발 착용 미리보기](https://localhost:10004/modular-character-preview.html?character=female&hair=bob&camera=face&motion=idle1)
- [정면](../../assets/modular_human_female_01/hair/tripo_knight_bob_v1/fitted_v1/fit-front.png) · [측면](../../assets/modular_human_female_01/hair/tripo_knight_bob_v1/fitted_v1/fit-side.png) · [후면](../../assets/modular_human_female_01/hair/tripo_knight_bob_v1/fitted_v1/fit-back.png)
- [피팅·리깅·해시](modular-female-knight-bob-fitting-v1.json), [애니메이션 검사](modular-female-knight-bob-animation-v1.json), [브라우저 검사](modular-female-knight-bob-browser-v1.json).

여성 리그 `human_female_01_local_v1`의 **65개 본 순서·계층·inverse bind 행렬을 그대로 복사**했다.
짧은 단발 전체를 `Head` 가중치 1로 연결했다. 별도 흔들림 본이나 물리 시뮬레이션은 없다.
9개 동작 각각 61시점, 총 549시점에서 모든 정점의 머리 부착, 가중치 합, 유한한 변형,
모서리 길이 보존을 확인했다. 걷기·달리기·점프·베기·쓰러지기·앉기 앞뒤 렌더와
브라우저의 9개 동작 및 헤어 착탈을 검수했다. 이 검사는 모든 프레임의 충돌 부재를 보장하지 않는다.
노멀맵용 탄젠트를 내보냈고, 길이 0인 탄젠트 1개는 법선에 직교하는 단위 벡터로 보정했다.
[최종 glTF 검사](../../assets/modular_human_female_01/hair/tripo_knight_bob_v1/fitted_v1/gltf-validation.json)는 오류·경고 0개다.
미리보기 코드의 `npm run check`와 `npm run lint`도 통과했다.

몸체·헤어 조립 합계는 **22,175 + 2,436 = 24,611삼각형**이다. 몸체를 잘라내거나 숨기는
마스크가 없어 숨겨진 두피를 포함한 합계와 표시 메시 합계는 같다. 픽셀 가림 이후 삼각형은 세지 않았다.
얼굴이 별도 메시로 나뉘지 않아 두상 영역(몸체 삼각형의 모든 정점 높이 ≥ 0.88)을 대신 측정하면
**5,051삼각형**이다. 몸체·얼굴·애니메이션은 변경하지 않았다. 조립 목표 15,000–20,000보다
많은 기존 몸체의 상세도를 유지했으며, 새 예산 맞춤 감축은 하지 않았다.

여성 미리보기의 기본 헤어를 `금발 단발`로 설정했다. `없음`과 `긴 금발 (보관본)`도 선택할 수 있다.
원본 단독 미리보기에는 피팅한 착용 화면으로 가는 링크를 추가했다. 게임 캐릭터 등록·배포는 미진행이다.
원본 GLB·원본 Blender 파일과 긴 헤어 보관본을 보존했다. 출처·라이선스·요금제는 위 Tripo API와
ChatGPT Pro 20x 원화 기록을 따르며, 이번 피팅은 로컬 Blender 작업으로 **추가 API 비용 0크레딧**이다.

초기 균일 높이 축소는 앞머리 위치를 바꿔 채택하지 않았다. 최종본은 아래 끝에만 부드러운 높이 보정을
적용한다. 내부 면 제거도 얼굴 중앙 깊은 영역으로 제한해 보이는 다발을 보존했다.

같은 날 가르마 두피 관통을 줄이려던 앞머리 국소 보정(최대 높이 0.010, 전방 0.005)은
사용자가 너무 높다고 지적해 제거했다. 사용자 요청에 따라 헤어 전체의 모든 정점에 동일하게
높이 +0.0035, 전방 +0.002를 적용했다(최초 피팅 기준, 모델 좌표 단위).
이전 국소 보정보다 앞머리를 낮추고 기존 형태를 복원했으며, 삼각형 수·UV·리깅 가중치는 유지했다.
브라우저에서 대기 동작의 0·25·50·75·100% 시점을 확인했다.
[가르마 보정 후 대기 화면](../../assets/modular_human_female_01/hair/tripo_knight_bob_v1/fitted_v1/parting-idle-0.5.png).

후면 두피 관통도 사용자 지적에 따라 보정했다. 넓은 헤어 삼각형의 내부가 두피와 겹쳐,
후면을 최대 0.0035만큼 뒤로 띄우고 옆면·아래쪽으로 부드럽게 줄였다. 앞머리 위치와 높이는 유지했다.
정점뿐 아니라 후면 삼각형 내부를 포함한 기본 자세 3,390개 지점에서 두피 밖 간격을 확인했다
(최소 약 0.00135, 모델 좌표 단위). 대기 5시점의 후면·좌우 사선 근접 화면도 확인했다.
[후면 보정 화면](../../assets/modular_human_female_01/hair/tripo_knight_bob_v1/fitted_v1/rear-back-idle-0.5.png).

현재 여성 착용 미리보기는 [로딩 최적화 파생본](modular-female-preview.md)을 사용한다.
피팅 원본의 메시·리깅을 유지한 2K 컬러/1K 노멀·ORM 버전이며, 원본이 바뀌면 자동 재생성된다.

재현 순서:

```bash
blender -b -t 6 --python-exit-code 1 --python tools/blender-scripts/fit_female_knight_bob.py
.venv/bin/python tools/rig-female-knight-bob.py
node tools/validate-female-knight-bob.mjs
blender -b -t 6 --python-exit-code 1 --python tools/blender-scripts/review_female_knight_bob.py
```

## 긴 헤어 보관본 제작 이력

2026-10-12. 기존 [여성 나이트 원화](../../client/public/character_concepts/female_knight.webp)를 참고해
Tripo 제작용 **헤어만** 분리했다. 기존 머리 모델을 사용하므로 얼굴·두상은 생성하지 않았다.

- [정면 원화](../images/characters/modular_human_female_01/parts/knight/hair_female_knight-front-v1.png): 1024×1536 RGBA PNG, 실제 투명 배경.
- [측면 원화](../images/characters/modular_human_female_01/parts/knight/hair_female_knight-side-v1.png): 화면 왼쪽을 향한 옆모습, 1024×1536 RGBA PNG, 실제 투명 배경.
- [후면 원화](../images/characters/modular_human_female_01/parts/knight/hair_female_knight-back-v1.png): 뒷모습, 1024×1536 RGBA PNG, 실제 투명 배경.
- 밝은 금발, 중앙에 가까운 가르마, 긴 앞머리 다발과 완만한 굴곡을 유지했다.
- 한 이미지에 한 헤어의 한 시점만 담았다. 얼굴·피부·몸·갑옷은 포함하지 않는다.
- 측면은 정면을, 후면은 정면과 측면을 참고해 생성했다. 정면을 주 기준으로 사용한다.
- 측면·후면은 정면에서 보이지 않는 형태를 보완한 후보로, 정확한 직교 투영이나 시점 간 기하학적 일치를 보장하지 않는다.
- Tripo 생성과 후면 보정, 기존 여성 몸체 피팅·리깅은 아래 단계별 기록을 따른다.

생성 도구: OpenAI Codex built-in ImageGen. 등급: **ChatGPT Pro 20x**. 생성일: **2026-10-12**.
출처·이용 조건은 OpenAI 생성 출력물 이용 조건과 [기존 여성 나이트 원화 기록](characters.md#female-knight)을 따른다.
원본 출처는 ComfyUI jibMixZIT_v10, A포즈 수정은 Qwen Image Edit, 투명화·키 조정은 ChatGPT Pro 20x다.
실제 생성 프롬프트·입출력 SHA-256·투명도 확인 결과는 [생성 기록](modular-female-knight-hair-sources.json)에 있다.

## Tripo API 메시 생성

2026-10-12, 사용자 요청으로 정면·측면·후면 3장을 사용해 헤어 메시 1건을 제출했다.
화면 왼쪽을 보는 측면은 캐릭터의 오른쪽 측면으로 해석해 `right` 슬롯에 전달했다.
모델은 `P2-20260801`, 목표는 3,000삼각형, PBR·detailed 텍스처와 `v3.5-20260815`를 사용했다.
헤어만을 위한 예산이며 조립 캐릭터 전체 예산을 적용하지 않았다.

- 작업 ID: `c10df22d-f0a9-461d-b87e-a8b42409eae2`.
- 도구·등급: Tripo API, 유료 API 크레딧.
- [요청 설정](modular-female-knight-hair-tripo-v1-build.json), [작업·비용·출력 기록](modular-female-knight-hair-tripo-v1-sources.json).
- [다중 시점 API 문서](https://developers.tripo3d.ai/en/docs/generation-multiview-to-model/p), [Tripo 이용 조건](https://developers.tripo3d.ai/en/terms).

생성 성공. **120크레딧 사용**, 잔액 **640크레딧**, 보류 **0크레딧**을 확인했다.
원본은 [GLB](../../assets/modular_human_female_01/hair/tripo_knight_v1/model_url.glb),
텍스처를 내장한 편집본은 [Blender 파일](../../assets/modular_human_female_01/hair/tripo_knight_v1/source.blend)이다.
정점이나 면을 수정하거나 감축하지 않았다.

검수 결과 **2,819삼각형**, 메시 오브젝트 1개, 4K 컬러·노멀·ORM 텍스처를 확인했다.
임시 용접 기준 연결 성분은 2개이며 경계선 388개, 비매니폴드 선 393개(경계선 포함),
퇴화 면과 붕괴한 UV 삼각형은 각각 0개다. [검수 기록](modular-female-knight-hair-tripo-v1-review.json).

**원본 검수 — 아래 보정본으로 보완:** 정면의 금발·가르마·긴 웨이브는 생성됐지만, 뒷머리 상단이 비어 있으며
후면에서 안쪽 면과 각진 패치가 노출된다. 완성된 후면 원화와 일치하지 않으므로
게임 적용 전 후면 메시 보정과 기존 두상 피팅이 필요하다. 리깅·게임 적용은 하지 않았다.

- [정면 렌더](../../assets/modular_human_female_01/hair/tripo_knight_v1/review/front.png)
- [측면 렌더](../../assets/modular_human_female_01/hair/tripo_knight_v1/review/side.png)
- [후면 렌더](../../assets/modular_human_female_01/hair/tripo_knight_v1/review/back.png)
- [사선 렌더](../../assets/modular_human_female_01/hair/tripo_knight_v1/review/angle.png)

## 뒷머리 보정본 (2026-10-12)

사용자 요청으로 Blender에서 뒷머리 곡면과 연속된 머리카락 면을 추가했다.
기존 앞머리·옆머리의 메시와 UV를 유지하고, 후면 원화의 머릿결을 새 면에 투영했다.
세 갈래로 내려오는 끝부분과 얕은 굴곡을 만들고, 가는 머릿결은 2K 탄젠트 노멀로 베이크했다.
초기 보정에서 나타난 UV 빈 공간, 정수리 틈, 측면 돌출은 채택본에서 수정했다.

- [보정 GLB](../../assets/modular_human_female_01/hair/tripo_knight_v1/rear_filled_v1/hair_female_knight-rear-filled-v1.glb)
- [텍스처 내장 Blender 편집본](../../assets/modular_human_female_01/hair/tripo_knight_v1/rear_filled_v1/hair_female_knight-rear-filled-v1.blend)
- [후면](../../assets/modular_human_female_01/hair/tripo_knight_v1/rear_filled_v1/back.png) · [측면](../../assets/modular_human_female_01/hair/tripo_knight_v1/rear_filled_v1/side.png) · [정면](../../assets/modular_human_female_01/hair/tripo_knight_v1/rear_filled_v1/front.png) · [사선](../../assets/modular_human_female_01/hair/tripo_knight_v1/rear_filled_v1/angle.png)
- [보정·검수·해시 기록](modular-female-knight-hair-rear-filled-v1.json)
- 재생성: `blender -b -t 6 --python-exit-code 1 --python tools/blender-scripts/fill_female_knight_hair.py`

총 **4,835삼각형**(원본 2,819 + 추가 2,016), 메시 오브젝트 2개다.
내보낸 GLB 재수입 후 원본 삼각형과 UV의 보존을 소수점 5자리 정밀도로 확인했다.
후면 중앙의 105개 광선 검사 지점이 모두 채워졌으며, 추가 면의 퇴화 면·붕괴 UV는 0개다.
추가 면은 양면 헤어 표면으로, 원본과 용접한 밀폐 솔리드는 아니다.
원본 파일을 보존했고 **추가 API 비용은 0크레딧**이다.

출처·이용 조건은 위 Tripo 원본과 ChatGPT Pro 20x 후면 원화 기록을 따른다.
보정 도구는 로컬 Blender다. 새 후면은 원화 기반 텍스처라 원본 4K 부분과 세부 머릿결에 차이가 있다.
이 보정본을 입력으로 아래 피팅·리깅을 진행했다.

## 여성 몸체 피팅·리깅 (2026-10-12)

기준은 `rig_v1/female-base.glb`, 리그 ID는 `human_female_01_local_v1`이다.
기존 몸체와 머리 원본을 보존하고, 헤어만 두상·가슴·등에 맞춰 변형했다.
원본의 별도 중앙 다발은 앞가슴을 가리고 새 후면과 겹쳐 제거했다(449삼각형).
최종 헤어는 **4,386삼각형**, 메시 2개이며 숫자를 맞추는 데시메이션은 하지 않았다.

- [리깅 GLB](../../assets/modular_human_female_01/hair/tripo_knight_v1/fitted_v1/hair_female_knight.glb)
- [몸체·텍스처·9개 동작을 포함한 Blender 편집본](../../assets/modular_human_female_01/hair/tripo_knight_v1/fitted_v1/female-knight-hair-fitted.blend)
- [로컬 보관본 미리보기](https://localhost:10004/modular-character-preview.html?character=female&camera=full&motion=walk&hair=knight): 헤어 선택에서 착탈, 동작·시점 변경 가능.
- [정면](../../assets/modular_human_female_01/hair/tripo_knight_v1/fitted_v1/fit-front.png) · [측면](../../assets/modular_human_female_01/hair/tripo_knight_v1/fitted_v1/fit-side.png) · [후면](../../assets/modular_human_female_01/hair/tripo_knight_v1/fitted_v1/fit-back.png)
- [피팅·리깅·해시](modular-female-knight-hair-fitting-v1.json), [애니메이션 검사](modular-female-knight-hair-animation-v1.json), [브라우저 검사](modular-female-knight-hair-browser-v1.json).

여성 리그의 **65개 본 순서·계층·inverse bind 행렬을 그대로 사용**한다.
두피 부근은 Head에 고정하고, 긴 부분은 실제 여성 몸체의 몸통 가중치를 부드럽게 전사한 뒤
목·머리 가중치와 혼합한다. 팔 가중치는 제외한다. 별도 헤어 본과 물리 시뮬레이션은 없다.
초기 높이 기반 가중치는 점프 시 앞머리가 가슴 속으로 들어가므로 채택하지 않았다.
몸체 가중치 전사와 앞가슴 여유 확대를 적용했다. 급격한 개별 정점 투영으로 생긴 돌출과
머리/상체 가중치의 급격한 전환도 채택본에서 완화했다.

자동 검사는 9개 동작 각각 61시점에서 본 호환, 가중치 합, 유한한 변형, 두피 부착과
모서리 늘어남을 측정한다. 두피 부착과 리그 호환 검사를 통과했다. 쓰러짐 동작은 일부
모서리에서 최대 약 **2.28배** 늘어나 별도 검토 대상으로 남겼다. 2배 제한의 초기 검사는
이 동작에서 실패했으며, 숫자만으로 충돌 보정 완료를 선언하지 않는다.
이는 전신 충돌 검사가 아니며, 극단적인 상체 굽힘·팔 교차·쓰러짐에서의 모든 관통을
보장하지 않는다. 갑옷·높은 옷깃·투구와의 조합은 미검증이다. 현재 적용 범위는 로컬 여성
미리보기와 편집본이며, 실제 플레이 캐릭터 등록·배포는 하지 않았다.

브라우저에서 기본 4시점·9개 동작 및 헤어 착탈을 확인했다.
프런트엔드 `npm run check`, `npm run lint`를 통과했다.
조립 합계는 몸체 22,175 + 헤어 4,386 = **26,561삼각형**이며, 가림을 추가하지 않아
숨김 포함 합계와 표시 메시 합계가 같다. 얼굴 배분 4,604삼각형은 유지했다.
기존 몸체만으로도 전체 권장 예산을 초과하며, 이번 작업에서 얼굴이나 몸체를 감축하지 않았다.

도구는 로컬 Blender 5.2.0 및 Python/Three.js다. 추가 API 비용은 0크레딧이다.
출처·이용 조건은 위 Tripo/원화 기록과 [여성 몸체 기록](modular-human-female-01.md)을 따른다.
재생성 순서:

```bash
blender -b -t 6 --python-exit-code 1 --python tools/blender-scripts/fit_female_knight_hair.py
.venv/bin/python tools/rig-female-knight-hair.py
node tools/validate-female-knight-hair.mjs
blender -b -t 6 --python-exit-code 1 --python tools/blender-scripts/review_female_knight_hair.py
```
