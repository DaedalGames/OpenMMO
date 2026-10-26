# 여성 로그 가터 스트랩

2026-10-26. [여성 로그 원화](../../client/public/character_concepts/female_rogue.webp)의 검은 가죽과
작은 은색 버클을 참고해 양쪽 다리의 앞뒤에 치마와 부츠를 잇는 스트랩 4개를 만들었다.
현재 여성 제작용 프리뷰에서 로그 치마와 로그 부츠를 함께 착용하면 표시된다.

![앞 가터 스트랩](../../assets/items/female_rogue_garters/fitted_v1/review/idle1-front.png)

![뒤 가터 스트랩](../../assets/items/female_rogue_garters/fitted_v1/review/idle1-back.png)

## 모델·연결

- 폭 14mm, 두께 1.8mm의 가죽 스트랩과 폭 18mm의 은색 조절 버클 4개다.
  앞 스트랩은 기존 부츠 윗단의 은색 장식 아래로 끝나며 뒤 스트랩은 뒤 윗단에 연결된다.
  위쪽은 치마 밑단 안쪽에 약 8mm 겹쳐 넣었다. 별도 허벅지 둘레 띠는 추가하지 않았다.
- 기준은 현재 여성 몸체 `human_female_01_local_v1`, 기존 65본과 정확한 inverse bind 행렬이다.
  미터 단위·배율 1을 유지하며 치마 v6와 부츠 v3는 수정하지 않았다.
- 피부 가중치를 옮기고 위쪽은 실제 치마 삼각형, 아래쪽은 부츠 윗단의 가중치와 연결했다.
  기본 가중치 0인 `pose_sit_idle` 모프가 치마의 앉기 보정과 부츠 윗단의 내려감을 함께 따른다.
  조절 버클도 보정된 스트랩의 방향과 위치를 따른다.
- 가죽 색은 기존 검은 부츠에서 가져온 값을 사용하고 새 텍스처는 추가하지 않았다.
  가죽·금속 두 개 메시, 두 개 PBR 재질이며 GLB는 약 60KB다. 추가 도형은 **768 triangles**다.
- 몸체·로그 상의·치마·부츠·가터의 합계는 숨김 포함 **33,614 triangles**, 가림 적용 후 **26,006 triangles**다.
  기존 머리 가중치 영역 5,057개와 앞 얼굴 추정 3,489개를 유지하며 헤어·무기는 포함하지 않는다.
  기존 몸체 가림 인덱스는 변경하지 않았다.
- 로그 치마와 부츠가 실제로 표시된 뒤에만 스트랩을 한 번 불러와 캐시한다.
  어느 하나를 벗거나 다른 장비로 바꾸면 숨기며, 로딩 중 해제해도 뒤늦게 나타나지 않는다.

## 검수

- 실제 프리뷰의 14개 동작 각각 61시점에서 기존 발 자세·앉기 다리 보정을 함께 적용했다.
  65본 연결과 정규화된 최대 4개 가중치, 유한 변형, 앉기 모프 적용·해제를 확인했다.
  스트랩 끝 중심과 실제 변형된 치마·부츠 연결점을 비교한 최대 오차는 치마 약 0.51mm,
  부츠 0.001mm 미만이다.
- 기본 자세와 14개 동작의 61시점에서 보이는 스트랩 정점·면 중심을 같은 다리의 허벅지와 검사했다.
  최소 간격은 약 4.95mm이며 1mm 초과 관통 샘플은 0개다.
  옷에 넣은 끝단, 손·다른 사지와의 접촉, 의자 충돌은 이 검사에 포함하지 않는다.
- 브라우저에서 대기·걷기·달리기·점프·앉기의 각 5시점과 앞뒤 시점을 확인했다.
  다른 하의·부츠로 교체, 로딩 중 해제, 3회 반복 착탈과 가림·삼각형 수 복원을 확인했다.
  앉기 뒤 검수에서는 의자를 숨겨 연결부를 확인했다. 페이지 오류·리소스 실패는 0개다.
  `npm run check`, `npm run lint`를 통과했다.

[리깅 GLB](../../assets/items/female_rogue_garters/fitted_v1/garters_female_rogue.glb),
[편집용 Blender](../../assets/items/female_rogue_garters/fitted_v1/female-rogue-garters.blend),
[제작·검사 통합 기록](../../assets/items/female_rogue_garters/fitted_v1/fitting.json).

```bash
node tools/validate-female-rogue-boots.mjs
blender -b --python-exit-code 1 -P tools/blender-scripts/build_female_rogue_garters.py
node tools/validate-female-rogue-garters.mjs
blender -b --python-exit-code 1 -P tools/blender-scripts/validate_female_rogue_garters.py
```

## 출처·라이선스

- 형상: Codex가 로컬 제작 스크립트로 직접 모델링했다. 유료 생성 요청은 없다.
- 디자인 참조: 기존 여성 로그 원화. 출처는 [캐릭터 제작 기록](characters.md)을 따른다.
- 색상·리그·피팅 참조: [여성 로그 부츠](modular-female-rogue-boots.md),
  [여성 로그 치마](modular-female-rogue-skirt.md), [여성 기준 몸체](modular-human-female-01.md).
  기존 원화·Tripo 출력의 이용 조건은 각 문서에 기록된 조건을 따른다.
