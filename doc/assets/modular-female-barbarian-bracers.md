# 여성 바바리안 손목대

[여성 바바리안 원화](../../client/public/character_concepts/female_barbarian.webp)의 손목대를 착용자 오른쪽 한 짝의 3면 원화로 옮기고
Tripo로 생성해 여성 공통 몸체(`human_female_01_local_v1` 65본)의 양 팔뚝에 피팅했다. 채택본은 Tripo v1의 `fitted_v1`이며 장갑 칸에 쓴다.
각 짝은 자기 `ForeArm`에 100% 연결하고 철판이 손등 쪽을 향한다. 왼쪽은 왼팔 뼈에서 거울 좌표로 다시 맞췄다.
은빛 기사 갑옷과 함께 입으면 기사 소매를 유지하며, 소매 가림은 은빛 기사 판금 장갑에만 적용한다.
게임 적용은 [여성 야만용사 런타임](female-knight-runtime.md#여성-야만용사-적용--2026-10-16)을 따른다.

![등쪽·옆·손바닥쪽 원화](../../assets/items/female_barbarian_bracers/concept_v1/sheet.png)

## 최종 파일

| 용도 | 파일 |
| --- | --- |
| 손목대 한 쌍 | [gloves_female_barbarian.glb](../../assets/items/female_barbarian_bracers/tripo_v1/fitted_v1/gloves_female_barbarian.glb) (3,408 triangles, 4K 컬러·노멀·ORM) |
| Blender | [female-barbarian-bracers-fitted.blend](../../assets/items/female_barbarian_bracers/tripo_v1/fitted_v1/female-barbarian-bracers-fitted.blend) |
| 몸체 가림 | [body-occlusion.json](../../assets/items/female_barbarian_bracers/tripo_v1/fitted_v1/body-occlusion.json) (손목대 안쪽 팔뚝 피부 208 triangles, 손은 가리지 않음) |
| 기록 | [피팅](modular-female-barbarian-bracers-fitting-v1.json), [동작 검사](../../assets/items/female_barbarian_bracers/tripo_v1/fitted_v1/animation-validation.json) |

## 재현

```bash
.venv/bin/python tools/fit-female-barbarian-bracers.py
node tools/validate-female-barbarian-bracers.mjs
blender -b --python-exit-code 1 -P tools/blender-scripts/review_female_barbarian_bracers.py
```

## 출처·라이선스

- 원화: OpenAI Codex built-in ImageGen(`codex exec`, codex-cli 0.162.1), **ChatGPT Pro 20x**, 2026-10-15.
  OpenAI 출력물 이용 조건을 따른다. 참조 원화의 출처는 [캐릭터 문서](characters.md)에 있다.
  [프롬프트](../../assets/items/female_barbarian_bracers/concept_v1/prompt.txt),
  [참조·분리 영역·해시](../../assets/items/female_barbarian_bracers/concept_v1/sources.json),
  참조 입력 [오른쪽(주)](../../assets/items/female_barbarian_bracers/concept_v1/reference-right.png)·[왼쪽(보조)](../../assets/items/female_barbarian_bracers/concept_v1/reference-left.png)
  (원화 손목을 흰 배경에 잘라 4배 확대). 손바닥쪽 버클 끈은 원래 원화에 없는 부분이라 새로 정했다.
- 3D: Tripo API 유료 크레딧, 모델 `P2-20260801`, 텍스처 `v3.5-20260815`, detailed PBR, 입력 조명 제거,
  한 짝 목표 1,500 triangles, seed 101503, 2026-10-15. 작업 ID `717bfa61-3371-4695-957b-9d90f20f8520`, **120크레딧**.
  입력은 원화 3면을 반시계 90° 돌린 것이다(등쪽=front, 옆=right, 손바닥쪽=back).
  [API 문서](https://developers.tripo3d.ai/en/docs/generation-multiview-to-model/p),
  [이용 조건](https://developers.tripo3d.ai/en/terms).
- [제작 명세](../../assets/items/female_barbarian_bracers/tripo_v1/build.json),
  [요청·비용·작업 기록](../../assets/items/female_barbarian_bracers/tripo_v1/generation.json),
  [입력](../../assets/items/female_barbarian_bracers/tripo_v1/inputs/),
  [Tripo GLB](../../assets/items/female_barbarian_bracers/tripo_v1/source/model_url.glb) (한 짝 1,704 triangles),
  [생성 미리보기](../../assets/items/female_barbarian_bracers/tripo_v1/source/rendered_image_url.png),
  [원본 Blender](../../assets/items/female_barbarian_bracers/tripo_v1/source.blend),
  [원본 진단](../../assets/items/female_barbarian_bracers/tripo_v1/review.json)([스크립트](../../assets/items/female_barbarian_bracers/tripo_v1/review_source.py)).

## 제한

- 손바닥쪽 버클은 생성 결과에서 뚜렷하지 않다.
- 같은 팔 피부 관통은 미리보기 클립 14개 모두 0이다. `walk`·`sit_idle`·`dying`에서는 맨팔의 팔뚝–허벅지 간격이
  손목대 두께보다 좁아 엉덩이·허벅지와 겹친다. 해당 동작의 팔 위치를 바꿔야 해결된다.
- 낚시·승마·대검 등 런타임 전용 클립은 검사하지 않았다. `.blend` 편집본은 미터 전환 전 제작 단위(리그 높이 1)다.
