# 남성 바드 시작 복장 원화

상의의 별도 전면·후면 이미지는 [상의 제작 원화](modular-bard-parts.md)를 참고한다.

2026-10-10. 여자 바드 원화를 참조한 남성 정면 전신 초안이다. 사용자 검토 전이며 3D 생성·피팅·게임 적용은 진행하지 않았다.

![남성 바드 원화](../../assets/items/bard_starter/concepts/male-bard-front-v2.png)

- 참조: `client/public/character_concepts/female_bard.webp`. 기존 출처는 [캐릭터 기록](characters.md#bard)을 따른다.
- 제작: OpenAI Codex built-in ImageGen, **ChatGPT Pro 20x**, 2026-10-10.
- 이용 조건: OpenAI 생성 출력물 이용 조건 적용. 참조 에셋의 기존 출처·이용 조건 유지.
- 현재 원화: `assets/items/bard_starter/concepts/male-bard-front-v2.png`, 1024×1536 RGBA PNG.
- 전체 프롬프트·입출력 해시·검수: [v2 생성 기록](../../assets/items/bard_starter/concepts/generation-v2.json), [v1 생성 기록](../../assets/items/bard_starter/concepts/generation.json).

녹색 짧은 망토, 아이보리·녹색 줄무늬 소매, 갈색 가죽과 황동 장식, 교차 벨트, 녹색 바지와 긴 가죽 부츠를 유지했다. 여성 코르셋은 남성 체형의 가죽 조끼로 바꿨다. 붉은 머리와 뾰족한 귀는 참조 인물의 특징을 따른 표현이며 모듈형 몸체·헤어 확정안은 아니다.

정면과 전신 실루엣을 확인했다. 후면 구조, 파츠 소속, 실제 남성 공통 몸체의 연결부·치수는 후속 제작에서 정한다. 알파 채널 범위는 0–254이며 런타임 사용 전 투명도를 별도 검수한다.

## 늘어진 띠 제거 — v2

2026-10-10. 사용자 요청에 따라 왼쪽 허벅지 앞으로 길게 늘어진 가죽 띠와 부속 고리·장식을 제거했다. 허리 벨트와 허벅지를 감싼 두 띠는 유지했다. 얇은 부품의 생성 오류와 다리 동작 중 관통 가능성을 줄이려는 수정이며, 실제 모델 검증은 아직 진행하지 않았다. 가죽의 잔무늬와 작은 봉제선은 후속 모델에서 텍스처·노멀맵으로 표현할 수 있다.

**[미사용]** `male-bard-front-v1.png`는 비교용 이전 원화로 보존한다. v2도 OpenAI Codex built-in ImageGen, **ChatGPT Pro 20x**로 제작했으며 같은 이용 조건을 따른다.
