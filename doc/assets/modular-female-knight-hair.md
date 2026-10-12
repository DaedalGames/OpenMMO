# 여성 나이트 헤어 원화

**[미사용 · 보관] 2026-10-12:** 사용자 요청으로 긴 헤어의 추가 작업을 보류했다.
원화·Tripo 원본·후면 보정본·피팅 GLB·Blender 편집본과 재현 스크립트를 보존한다.
미리보기에서는 기본 착용을 해제하고 `긴 금발 (보관본)`으로 선택할 때만 표시한다.
다음 버전은 어깨에 닿지 않는 턱 아래 길이의 금발 헤어로 진행한다.

단발 [정면 원화 후보](../images/characters/modular_human_female_01/parts/knight/hair_female_knight-bob-front-v1.png)를
OpenAI Codex built-in ImageGen, **ChatGPT Pro 20x**로 2026-10-12 생성했다.
[프롬프트·출처·해시](modular-female-knight-bob-sources.json). 사용자 요청에 따라 이 단계에서 먼저 커밋한다.
측면·후면 원화, 후두부 덮임 검토, Tripo 생성과 피팅은 다음 작업이다.

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
