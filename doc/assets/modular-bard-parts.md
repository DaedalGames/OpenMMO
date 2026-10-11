# 바드 상의·하의 전면·후면 원화

사용자가 전달한 3D 결과와 후속 피팅·리깅은 [Tripo 상의 제작 기록](modular-bard-tripo-top.md)에 기록했다.

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
