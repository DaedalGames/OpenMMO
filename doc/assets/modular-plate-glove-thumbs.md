# 판금 장갑 엄지 형상 보정 — 2026-10-10

사용자가 제작 미리보기에서 판금 장갑의 엄지가 지나치게 굵다고 지적했다.
기존 손 표면을 기준으로 양손 엄지의 과한 부피를 줄이고 손바닥 쪽으로 보정량을
부드럽게 줄였다. 피부에서 약 6mm 여유를 목표로 바깥쪽 돌출만 줄여 금속 외피의
두께를 남겼다. 면이 뒤집히는 곳에서는 이동량을 완화했다.

엄지 중간·끝 영역의 축으로부터 거리 90백분위는 왼쪽 약 32→20mm, 오른쪽 33→22mm다.
이는 선택 영역의 부피 진단이며 전체 엄지를 균일하게 축소한 수치는 아니다.
왼손 77개·오른손 68개 정점이 움직였으며 최대 이동은 각각 13.45mm·13.08mm다.
1,404 triangles, UV·PBR 텍스처·본 가중치·65본 골격을 유지하고, 법선·접선을 갱신했다.
손목 테두리와 안감의 정점은 그대로 유지했다. 닫힌 메시와 면 방향 검사를 통과했다.

- 제작본: `assets/modular_human_male_01/fitted/gloves_plate.glb`
- 편집본: `assets/modular_human_male_01/fitted/plate_parts.blend`
- 게임 압축본: `client/public/models/characters/modular_male/gloves_plate.glb`
- **[미사용] 보정 전 비교·재현 원본**: `assets/modular_human_male_01/gloves/shape_sources/plate-before-thumb-v1.glb`
- [형상·보존 항목·해시](modular-plate-glove-thumbs-v1.json)
- [제작본·압축본 7동작 × 25자세 검증](modular-plate-glove-thumbs-animation-v1.json)

양손 대기·전투 대기를 확대 확인했다. 검증한 175자세에서 제작본과 게임 압축본의
정점 위치 차이는 0이며, 수정하지 않은 정점의 자세별 위치도 유지된다.
이는 모든 장비·자세의 관통 검사나 저밀도 손가락의 전면 재제작은 아니다.
검토 이미지는 `assets/modular_human_male_01/gloves/review/plate-thumb-v1/`에 저장했다.

출처와 이용 조건은 [기존 Meshy 판금 장비 기록](modular-knight-plate-sources.json)을 따른다.
새 이미지·3D 생성이나 유료 호출은 없다. 기존 아이콘·월드 모델을 재사용한다.

```sh
.venv/bin/python tools/reshape-glove-thumbs.py --part plate
blender -b -t 4 --python-exit-code 1 --python tools/blender-scripts/sync_glove_thumbs.py -- --part plate
node tools/prepare-modular-character.mjs --part gloves_plate --parts-only
node tools/validate-plate-glove-thumbs.mjs
```

형상 보정은 보존 원본에서 계산하므로 반복 실행해도 추가로 줄어들지 않는다.
기존 판금 전체를 다시 피팅할 때는 아래 순서를 따른다.

```sh
.venv/bin/python tools/fit-modular-plate.py
.venv/bin/python tools/reshape-glove-thumbs.py --part plate
blender -b --python-exit-code 1 -P tools/blender-scripts/pack_modular_plate.py
node tools/prepare-modular-character.mjs
```
