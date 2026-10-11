# 바드 부위별 제작 원화

## 모자 원화 — 2026-10-11

사용자가 전달한 3D 모델은 [Tripo 모자 원본 검수](modular-bard-tripo-hat.md)에 기록했다.

트리포 입력용으로 정면과 **정면 그림 기준 오른쪽 측면**을 별도 이미지로 제작했다.
오른쪽 측면은 깃털이 있는 쪽이며 착용자 기준으로는 왼쪽이다. 현재 측면 v3는 v2의 잘못된 앞뒤 방향을 바로잡은 이미지다.

- [정면 PNG](../../assets/items/bard_starter/concepts/hat/hat-bard-front-v1.png)
- [오른쪽 측면 v3 PNG](../../assets/items/bard_starter/concepts/hat/hat-bard-viewer-right-side-v3.png): 정면 그림 기준 오른쪽에서 본 모습. **모자 앞은 화면 왼쪽, 뒤는 오른쪽.** 깃털도 뒤쪽인 오른쪽으로 기울어진다.
- [정면 프롬프트·참조·해시](../../assets/items/bard_starter/concepts/hat/generation-views-v1.json)
- [측면 v3 프롬프트·참조·해시](../../assets/items/bard_starter/concepts/hat/generation-side-v3.json)
- **[미사용·삭제]** 이전 측면 v1·v2는 모자 앞을 화면 오른쪽으로 지정한 오류가 있어 v3로 대체했다. 이미지 파일은 중간 결과물 정리 요청에 따라 삭제했고 제작 기록은 오류 이력으로 보존한다.

두 파일 모두 1254×1254 RGBA, 알파 범위 0–255이며 모자 한 개와 한 시점만 담는다.
깃털과 황동 장식은 착용자 왼쪽에 두었다. 이미지 생성 기반 원화이므로 정밀한 3D 투영도는 아니다.
측면의 앞뒤 깊이는 보완한 제안이며 깃털 기울기·챙 곡률·장식 세부는 3D 제작 시 원본과 정면을 우선해 정리한다.
제작 도구·등급·날짜·이용 조건은 아래 원화와 동일하다.

캐릭터 생성 화면의 남성 음유시인 복장에 맞춘 모자 초안이다.
짙은 녹색 펠트에 짧고 한쪽이 올라간 챙, 갈색 가죽띠, 황동 고정구와 밝은 깃털 한 개를 조합했다.
낮은 크라운과 짧은 챙으로 얼굴이 잘 드러나도록 의도했으며 실제 착용 비율은 후속 피팅에서 확인한다.

- [모자 3/4 원화 PNG](../../assets/items/bard_starter/concepts/hat/hat-bard-three-quarter-v1.png)
- [전체 프롬프트·해시·검수 기록](../../assets/items/bard_starter/concepts/hat/generation.json)

1254×1254 RGBA PNG이며 알파 범위는 0–255다. 단일 모자·단일 시점으로 생성했다.
현재 복장의 색상·소재를 텍스트로 참조했으며 이미지 입력은 사용하지 않았다.
원화 제안 단계다. 3D 제작 전 깃털과 가장자리, 머리·헤어와의 맞음새, 챙의 얼굴 가림을 검토한다.

제작: OpenAI Codex built-in ImageGen, **ChatGPT Pro 20x**, 2026-10-11.
OpenAI 생성 출력물 이용 조건을 적용한다.

## 캐릭터 생성 화면 적용 — 2026-10-11

남성 음유시인을 선택하고 공통 남성 몸체의 얼굴·머리·색상을 설정할 수 있다.
생성 미리보기와 시작 장비는 `worn_bard_top`, `worn_bard_pants`, `worn_bard_boots`를 사용한다.
기존 만돌린 지급은 유지하며 여성 음유시인과 기존 여성 NPC 모델도 유지한다.

- 착용 모델: `client/public/models/characters/modular_male/{top,pants,boots}_bard.glb`.
- 바닥 아이템 모델·아이콘: `client/public/models/armor/bard_{top,pants,boots}.glb`, `client/public/items/armor/bard_{top,pants,boots}.png`.
- 아이템 편집본: `assets/items/bard_{top,pants,boots}/bard_{top,pants,boots}.blend`.
- 재생성: `node tools/prepare-modular-character.mjs --bard-only`와 `blender -b --python tools/blender-scripts/export_priest_items.py -- --outfit bard`. 착용 모델 압축에는 `toktx`가 필요하다.

기존 [상의](modular-bard-tripo-top.md), [하의](modular-bard-tripo-pants.md), [부츠](modular-bard-tripo-boots.md)의 피팅 원본을 사용한다.
새 AI 생성 없이 파생 에셋만 내보냈다. 원본의 Tripo 출처·이용 조건과 미확인 구독 등급·생성일 기록을 그대로 따른다.
착용 모델은 Meshopt·512px KTX2로 압축하며 입력·출력 해시는 런타임 `manifest.json`에 기록한다.
부츠 접지 보정은 세 얼굴에서 측정한 `0.011000244302464102m`를 사용한다.
기본 얼굴·크롭 헤어·복장 3종 착용 시 무기 없이 원본 합계 26,449 triangles,
가림 적용 후 표시 18,004 triangles이며 얼굴은 3,157 triangles다.
전체 원본 수는 권장 범위를 넘지만 가려지는 몸체를 포함한 값이며 예산만을 위한 메시 축소는 하지 않았다.

브라우저에서 남녀 선택 전환, 남성 외형 설정, 능력치 굴림·생성 요청의 직업·성별 전달을 확인했다.
실제 런타임 모델의 WebGPU·WebGL 표시와 세 부위의 개별 착탈·재착용에서 로딩·렌더링 오류가 없었다.
서버 생성 테스트로 남성 복장 3종의 착용 지급, 만돌린 지급, 여성 기존 동작을 확인했다.
기존 피팅·혼합 장비 검증 기록은 각 부위 문서를 따른다.

## 제작 원화

사용자가 전달한 3D 결과와 후속 피팅·리깅은 [Tripo 상의 제작 기록](modular-bard-tripo-top.md)에 기록했다.

신발 한 짝의 정면·측면은 [부츠 원화](#부츠-한-짝-정면측면-원화--2026-10-11)를 참고한다.

2026-10-10. [남성 바드 v2](modular-bard-concept.md)를 기준으로 전면과 후면을 각각 독립 이미지로 제작했다. 원화 검토 단계이며 3D 생성·피팅·게임 적용은 진행하지 않았다.

- [전면 PNG](../../assets/items/bard_starter/concepts/top/top-bard-front-v1.png)
- [후면 PNG](../../assets/items/bard_starter/concepts/top/top-bard-back-v1.png)
- [전체 프롬프트·참조·해시](../../assets/items/bard_starter/concepts/top/generation.json)

각 이미지에는 한 시점의 상의만 있다. 두 파일 모두 1536×1024 RGBA PNG이며 알파 채널 범위는 0–254다. 실제 모델 입력 전에 투명 배경과 가장자리를 확인한다.

상의에는 짧은 녹색 어깨 망토와 앞쪽 잠금 장식, 줄무늬 셔츠, 가죽 조끼, 짧은 녹색 허리 옷자락을 포함했다. 벨트·장갑·팔 보호대·바지·부츠·몸체는 제외했다. 별도 장갑 안에 들어갈 셔츠 소매 끝은 단순한 천 커프로 연장했다. 벨트는 후속 하의 설계에서 다룬다.

앞면을 먼저 생성하고 이를 후면의 직접 참조로 사용했다. 후면의 짧은 망토, 가죽 등판 봉제선과 녹색 옷자락의 중앙 트임은 원본에 보이지 않던 부분을 보완한 제안이다. 앞뒤 소매와 옷자락 길이 및 전면 장식이 후면에 중복되지 않은 것을 확인했다. 망토의 옆 주름과 등쪽 드레이프 연결은 3D 제작 시 정리해야 한다. 문양은 얕은 텍스처·노멀 표현을 우선한다.

후속 피팅 기준은 `assets/modular_human_male_01/fitted/base.glb`, 리그 `human_male_01_mixamo_candidate_v2`, 연결부 후보 `interfaces/v1`이다. 손목은 장갑이 소매를 덮고, 허리는 상의가 바지 허리를 덮도록 설계한다. 구체적인 겹침 여유·가림·망토 처리·다른 장비와의 호환은 미검증이다. 그림을 실제 치수나 피팅 합격 증거로 사용하지 않는다.

제작 도구: OpenAI Codex built-in ImageGen, **ChatGPT Pro 20x**, 2026-10-10. OpenAI 생성 출력물 이용 조건을 적용하며 참조 에셋의 기존 출처·이용 조건을 유지한다.

## 하의 전면·후면 원화 — 2026-10-11

사용자가 전달한 3D 원본의 입수·검수는 [Tripo 하의 제작 기록](modular-bard-tripo-pants.md)에 기록했다.

[남성 바드 v2](modular-bard-concept.md)의 바지를 분리한 검토용 초안이다. 전면을 먼저 제작하고 이를 직접 참조해 후면을 생성했다.

- [전면 PNG](../../assets/items/bard_starter/concepts/pants/pants-bard-front-v1.png)
- [후면 PNG](../../assets/items/bard_starter/concepts/pants/pants-bard-back-v1.png)
- [전체 프롬프트·참조·해시](../../assets/items/bard_starter/concepts/pants/generation.json)

각 파일은 한 시점만 담은 1024×1536 RGBA PNG다. 녹색 바지, 갈색 허리·사선 골반 벨트, 착용자 왼쪽 허벅지의 두 가죽 띠를 하의에 포함했다. 상의 소속 녹색 옷자락과 부츠·무릎 장식·몸체는 제외했다. 긴 늘어진 띠는 복원하지 않았다.

가려졌던 허리·종아리와 후면 봉제 구조는 보완한 제안이다. 발목까지 좁아지는 천 밑단은 별도 부츠 안에 넣도록 구성했다. 허벅지 띠는 전면 이미지 오른쪽, 후면 이미지 왼쪽에 있으며 후면에 전면 버클과 지퍼 덮개를 반복하지 않았다. 벨트의 세부 연결과 앞뒤 치수는 3D 제작 시 정리해야 한다.

알파 채널 범위는 0–254이며 주변에 색 번짐이 보여 3D 입력 전 배경·가장자리 정리가 필요하다. 현재 원화 검토 단계로 3D 생성·피팅·게임 적용은 진행하지 않았다. 후속 피팅은 현재 `assets/modular_human_male_01/fitted/base.glb`, `human_male_01_mixamo_candidate_v2`, `interfaces/v1`을 기준으로 한다. 상의가 바지 허리를 덮고 부츠가 바지 밑단을 덮으며, 벨트 간섭·겹침 여유·가림·동작·혼합 장비 호환은 미검증이다.

제작 도구: OpenAI Codex built-in ImageGen, **ChatGPT Pro 20x**, 2026-10-11. OpenAI 생성 출력물 이용 조건을 적용하며 참조 원화의 기존 출처·이용 조건을 유지한다.

## 부츠 한 짝 정면·측면 원화 — 2026-10-11

사용자 제공 메시의 피팅·대칭 제작은 [Tripo 부츠 제작 기록](modular-bard-tripo-boots.md)에 기록했다.

[남성 바드 v2](modular-bard-concept.md)의 긴 가죽 부츠를 착용자 오른발 한 짝으로 분리했다. Tripo 입력용으로 시점마다 독립된 1024×1536 RGB PNG를 저장했다. 흰색 불투명 배경이며 몸체와 바지는 없다.

- [정면 PNG](../../assets/items/bard_starter/concepts/boots/boot-bard-right-front-v1.png)
- [바깥쪽 측면 PNG](../../assets/items/bard_starter/concepts/boots/boot-bard-right-side-v1.png): 발끝이 이미지 오른쪽을 향한다.
- [전체 프롬프트·참조·해시·검수](../../assets/items/bard_starter/concepts/boots/generation.json)

갈색 가죽, 접힌 입구, 정면 황동 마름모 장식, 정면 끈, 종아리 상단·발목 스트랩을 유지했다. 긴 끈 끝은 짧게 정리했다. 정면을 먼저 생성하고 이를 측면의 직접 참조로 사용했다. 측면에서도 장식과 끈은 앞 가장자리에 있고 버클은 바깥쪽 앞에 있다. 원본에 가려진 측면·뒤꿈치는 보완한 제안이며, 세부 봉제·주름·끈 차이는 정면을 우선해 3D에서 정리한다.

이 단계는 원화 제작이며 Tripo 생성·피팅은 아직 진행하지 않았다. 후속 작업에서는 한 짝을 생성하고 반대쪽을 3D에서 대칭 제작하며 좌우 본 대응과 면 방향도 수정한다. 현재 공통 몸체 `assets/modular_human_male_01/fitted/base.glb`, 리그 `human_male_01_mixamo_candidate_v2`, `interfaces/v1`의 `boot_calf` 후보를 기준으로 부츠가 바지를 덮도록 피팅한다. 입구 여유·겹침·가림·동작·혼합 장비 호환은 미검증이다.

제작 도구: OpenAI Codex built-in ImageGen, **ChatGPT Pro 20x**, 2026-10-11. OpenAI 생성 출력물 이용 조건을 적용하며 참조 원화의 기존 출처·이용 조건을 유지한다.
