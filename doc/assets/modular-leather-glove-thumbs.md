# 가죽장갑 엄지 형상 보정 — 2026-10-10

사용자가 제작 미리보기에서 가죽장갑의 엄지가 지나치게 크다고 지적했다. 기본 자세에서도
실제 손보다 엄지 외피가 크게 부풀어 있어, 기존 손 표면을 기준으로 양손 엄지의 과한 부피를 줄였다.
엄지 본의 영향과 뿌리에서의 거리에 따라 보정을 부드럽게 연결하고, 피부에서 약 4mm 여유를
목표로 바깥쪽 돌출만 줄였다. 면이 뒤집히는 부분은 이동량을 완화했다.

엄지 중간·끝 영역의 축으로부터 거리 90백분위는 왼쪽 약 37→21mm, 오른쪽 41→20mm다.
이는 선택 영역의 부피 진단이며 전체 엄지를 균일하게 절반으로 축소한 것은 아니다.
1,033 triangles, UV·텍스처·스킨 가중치·65본 골격을 유지했다. 다른 손가락과 손목의
변형을 새로 만들지 않았으며 기존 저밀도 메시의 각진 모양은 남아 있다.

- 수정본: `assets/modular_human_male_01/fitted/gloves_leather.glb`
- 편집본: `assets/modular_human_male_01/fitted/character_parts.blend`
- **[미사용] 보정 전 비교·재현 원본**: `assets/modular_human_male_01/gloves/shape_sources/leather-before-thumb-v1.glb`
- [형상·보존 항목·해시](modular-leather-glove-thumbs-v1.json)
- [7동작 × 25자세 검증](modular-leather-glove-thumbs-animation-v1.json)

제작 미리보기에서 양손 대기·전투 대기 확대를 확인했다. 동작 검사는 유한 좌표, 보정량 상한,
변경하지 않은 정점의 자세별 위치 보존을 확인하며 모든 장비·자세의 관통 검사는 아니다.
현재 가죽장갑은 제작 미리보기용이며 게임 압축 파츠 목록에는 등록되어 있지 않다.

출처와 이용 조건은 [기존 Meshy 가죽장갑 기록](modular-human-male-01-sources.json)의
`gloves_leather`를 따른다. 새 이미지·3D 생성이나 유료 호출은 없다.

```sh
.venv/bin/python tools/reshape-glove-thumbs.py --part leather
blender -b -t 4 --python-exit-code 1 --python tools/blender-scripts/sync_glove_thumbs.py -- --part leather
node tools/validate-leather-glove-thumbs.mjs
```
