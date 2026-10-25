# 여성 로그 치마

[여성 로그 원화](../../client/public/character_concepts/female_rogue.webp)의 치마를 앞뒤 원화로 옮겼다.
허리에 걸친 회색 울 미니스커트(옆 솔기 패널, 뒤 지퍼)와 사각 은색 버클의 검은 가죽 벨트로 구성한다.
엉덩이 화살통·주머니, 가터 끈, 허벅지 밴드, 상의에서 내려온 세로 끈은 포함하지 않는다.

![여성 로그 치마 원화](../../assets/items/female_rogue_skirt/concept_v1/sheet.png)

## Tripo v1 원본

![Tripo v1 정면](../../assets/items/female_rogue_skirt/tripo_v1/review/front.png)

2,710 triangles, 단일 메시, 4K 컬러·노멀·ORM. 허리·밑단은 열려 있다.
[진단](../../assets/items/female_rogue_skirt/tripo_v1/review.json).
생성 원본이며, 피팅 결과는 아래 별도 파일에 보관한다.

## 피팅·리깅 v1 — 2026-10-25

- 기준 몸체: `assets/modular_human_female_01/rig_v1/female-base.glb`, 높이 1.80m,
  리그 `human_female_01_local_v1`, 기존 65본. 남성 몸체나 구형 여성 몸체에 맞추지 않았다.
- Blender 5.2.0 LTS(현재 설치본), Metric, `scale_length = 1`.
  크기를 메시 좌표에 적용했으며 몸체·의상·리그의 오브젝트 스케일과 GLB 착용 배율은 1이다.
- Tripo 원본의 회전 오프셋을 제거하고 허리 폭·앞뒤 깊이·높이를 맞췄다.
  기본 자세에서 피부와 약 5mm의 여유를 확보했다. 허리·밑단의 열린 구조를 유지했다.
- 실제 피부 삼각형의 barycentric 가중치를 전사했다. 치마 중앙에서 최근접 다리가 갑자기
  바뀌는 문제는 좌우 허벅지 가중치를 연속적으로 나누어 보정했다.
  가까운 표면끼리 가중치를 평활화하고 UV 이음의 위치·가중치·노멀을 일치시켰다.
  버클·고리 등 분리 장식은 조각별 동일 가중치를 사용하며 골반·척추를 따른다.
- 2,710 triangles, 원본 UV 삼각형, 4K 컬러·노멀·ORM의 바이트를 보존했다.
  유료 생성 요청이나 원본 몸체·Tripo 파일 수정은 없다.
- 내보낸 GLB를 실제 `bindModularPart`로 연결해 65본의 대응과 inverse bind 행렬의 일치,
  기본 자세 유지, 최대 4개 본의 가중치 정규화, 9개 동작 각각 33프레임의 유한 변형과
  모서리 늘어남을 검사했다. 이 검사는 충돌 합격 판정과 구분한다.
- 기존 로그 상의와 함께 앞·뒤·옆·사선 및 동작별 렌더를 검수했다.
  편집용 Blender에는 기준 몸체·로그 상의·치마·조명·카메라와 숨겨진 Tripo 원본이 있다.
  타임라인 1은 기본 자세이고, 10–90에는 9개 동작의 검수용 샘플 자세가 있다.
- 골반 안쪽 피부의 보수적인 가림 후보를 별도 JSON으로 저장했다.
  밑단에서 보이는 다리와 기본 하의 속옷은 유지했다. 원래 몸체 인덱스를 복원할 수 있어야 하며,
  가림 파일은 기록된 몸체 해시에만 적용한다.
- 몸체+로그 상의+치마는 숨김 포함 28,636 triangles, 가림 후보 적용 시 24,222 triangles다.
  헤어·무기는 제외했다. 기존 몸체의 Head 가중치 영역은 5,057 triangles이며,
  얼굴 앞쪽 좌표 범위로 추산한 영역은 3,489 triangles다(정확한 범위는 피팅 JSON에 기록).
  현재 검수 조합은 15,000–20,000 목표를 넘는다. 이번 작업에서는 원본 형상을 유지했다.

[리깅 GLB](../../assets/items/female_rogue_skirt/tripo_v1/fitted_v1/bottom_female_rogue.glb),
[편집용 Blender](../../assets/items/female_rogue_skirt/tripo_v1/fitted_v1/female-rogue-skirt.blend),
[피팅·리그·동작·피부 간격 통합 기록](../../assets/items/female_rogue_skirt/tripo_v1/fitted_v1/fitting.json),
[가림 후보](../../assets/items/female_rogue_skirt/tripo_v1/fitted_v1/body-occlusion.json).

![피팅 앞뒤](../../assets/items/female_rogue_skirt/tripo_v1/fitted_v1/review/fitting.png)

### 보정 이력과 남은 범위

- 처음에는 높이만으로 골반·허벅지 가중치를 나누어 달리기·앉기에서 관통이 발생했다.
  최종본은 피부 가중치 전사와 연속적인 좌우 분배를 사용한다.
- 모든 동작의 관통을 정적 메시 확장만으로 해결하려 한 결과 벨트가 휘거나 밑단이 과도하게
  벌어졌다. 해당 보정은 폐기했고, 최종본에는 원본의 짧은 치마 실루엣을 유지했다.
- 기본 자세의 정점·삼각형 중심에서 3mm를 넘는 피부 관통 후보는 0개다.
  동작 중에는 최근접 피부 검사에서 중첩 후보가 남는다. 큰 다리 굽힘·벌림 및 앉기에서는
  치마의 추가 변형 보정이 필요하므로 **게임 호환·충돌 합격본으로 취급하지 않는다**.
  검수 자세는 Blender에, 동작별 수치는 통합 기록에 남겼다.
- 여성 캐릭터 프리뷰의 하의 목록에 **로그 벨트 미니스커트**로 연결했다.
  `?character=female&top=rogue&bottom=rogue&camera=lower&hair=none`으로 로그 상의와 함께 볼 수 있다.
  브라우저에서 상의·치마 착탈 시 피부와 삼각형 수 복원, 6개 동작 전환,
  페이지 오류·리소스 로드 실패 0개를 확인했다. `npm run check`, `npm run lint`를 통과했다.
  게임 장비 등록, 혼합 장비 조합, 최종 런타임 텍스처 압축은 별도 단계다.

재현 명령은 저장소 루트에서 실행한다.

```bash
blender -b --python-exit-code 1 -P tools/blender-scripts/fit_female_rogue_skirt.py
node tools/validate-female-rogue-skirt.mjs
blender -b --python-exit-code 1 -P tools/blender-scripts/review_female_rogue_skirt.py
```

사용자가 후속 수정 전에 현재 상태 정리·커밋을 요청했다(2026-10-25).
개별 검수 렌더·동작 행렬 샘플·중복 검사 보고서 23개를 삭제하고 검사 결과는
`fitting.json`에 통합했다. 원화·생성 입력·원본 모델·현재 Blender 편집본·리깅 GLB·가림 정보와
원본 정면 및 피팅 앞뒤 문서 이미지는 보존했다. 재현 명령은 삭제한 검수 중간 파일을 다시 생성한다.

## 골반에 걸치는 타이트 핏 v2 — 2026-10-25

사용자가 치마를 몸에 더 붙이고 윗단을 낮춰 골반에 걸친 형태를 요청했다.
v1은 수정 전 보관본이며, v2는 첫 번째 골반 핏 보정본이다.

- 밑단 높이 약 0.835m를 유지하며 세로 길이를 89%로 줄여 윗단을 약 32.4mm 내렸다.
  가로·앞뒤 축소 후 피부 여유를 다시 보정했다. 최종 전체 폭은 약 443 → 410mm,
  앞뒤 두께는 약 323 → 299mm로 각각 약 7.4% 줄었다.
- 벨트·버클·고리도 같은 피팅에 포함하며, 원본 2,710 triangles와 UV·4K PBR 텍스처는 유지한다.
  기준 몸체와 65본 리그, 오브젝트 스케일 1도 유지했다. 새 생성 요청은 없다.
- 기본 자세의 정점·삼각형 중심 피부 간격은 약 4.9mm 이상이며 3mm 초과 관통 후보는 0개다.
  기존 9개 동작 각각 33프레임에서 리그·가중치·유한 변형을 재검사했다.
  큰 다리 굽힘에서 남는 관통은 v1과 마찬가지로 최종 게임 적용 전 추가 보정 범위다.
- 가림 정보는 새 형상에서 다시 계산했다. 프리뷰에서 착탈 후 피부·삼각형 수 복원,
  몸체 정점 좌표 유지와 7개 동작 전환을 확인했다. 페이지 오류·리소스 로드 실패는 0개다.
  `npm run check`, `npm run lint`를 통과했다.
- 몸체+상의+치마는 숨김 포함 28,636 triangles, 가림 적용 시 24,230 triangles다.
  기존 머리·얼굴 배분은 v1과 같다. 위에서 보이는 흰 속옷 무늬는 기본 몸체 표면에 남아 있으며,
  이번 변경에서 몸체 텍스처나 정점은 수정하지 않았다.

[검사 기록](../../assets/items/female_rogue_skirt/tripo_v1/fitted_v2/fitting.json).
**[미사용]** 중간 모델·Blender·가림 파일은 현재 보정본으로 대체해 정리했다.
앞의 재현 명령은 최신 피팅을 생성한다.

![타이트한 골반 핏 앞뒤](../../assets/items/female_rogue_skirt/tripo_v1/fitted_v2/review/fitting.png)

## 허리 밀착과 벨트 고리 보정 v3 — 2026-10-25

치마 v3는 [밑단을 줄인 상의 v2](modular-female-rogue-top.md)와 함께 검수한 이전 보정본이다.

- 허리 윗단을 피부 표면 쪽으로 추가 수렴시키고 목표 여유를 3mm로 줄였다.
  윗단 가중치는 피부 접촉 지점의 가중치를 유지해 대기 중 몸통 움직임을 따른다.
  v2의 골반 높이·밑단 위치·치마 전체 폭은 유지했다.
  기본 자세·대기 33프레임에서 검사한 앞 허리 정점의 평균 피부 간격은
  약 30.9 → 7.7mm, 최대 간격은 약 35.3 → 8.7mm로 줄었다.
- 기존의 작은 분리 장식은 허벅지 가중치를 제거하고 골반·척추에만 고정했다.
  치마 천과 다른 변형 때문에 고리가 천 안에 들어가는 문제가 있었다.
  장식을 천의 바깥면에서 최소 4mm 떨어지도록 옮기고, 해당 천 삼각형의 barycentric
  가중치를 전사했다. 고리의 정점별 가중치는 바로 아래 천의 변형을 따른다.
- 양쪽 앞 벨트 고리의 정점·삼각형 중심에서 실제 변형된 천의 바깥면을 향해 광선을 쏘아 검사했다.
  기본 자세와 대기·걷기 각 33프레임에서 묻히는 샘플 및 광선 누락은 0개이며,
  최소 간격은 약 4.1mm다. 달리기 등 다른 자세의 수치도 통합 기록에 포함했다.
- 기본 자세에서 피부 관통 후보 0개, 기존 65본 연결·9개 동작 변형 검사를 통과했다.
  브라우저에서 대기·걷기 각 5시점, 상·하의 착탈과 원상 복원, 다른 동작 전환을 확인했다.
  숨김 포함 28,636 triangles, 새 상의와 가림 적용 시 24,234 triangles다.
  머리·얼굴 배분은 v1과 같다. 큰 다리 굽힘의 기존 관통 보정 범위는 남아 있다.

[검사 기록](../../assets/items/female_rogue_skirt/tripo_v1/fitted_v3/fitting.json).
**[미사용]** 중간 모델·Blender·가림 파일은 현재 보정본으로 대체해 정리했다.

고리 검사는 `node tools/validate-female-rogue-skirt.mjs`로 동작 샘플을 만든 뒤
`blender -b --python-exit-code 1 -P tools/blender-scripts/validate_female_rogue_belt.py`로 재현한다.

![허리와 벨트 고리 보정 앞뒤](../../assets/items/female_rogue_skirt/tripo_v1/fitted_v3/review/fitting.png)

## 고리·버클 밀착과 뒤 허리 여유 보정 v4 — 2026-10-25

현재 여성 프리뷰는 치마 v4와 [앞섶 폭을 복원한 상의 v4](modular-female-rogue-top.md)를 사용한다.

- v3의 장식 전체를 바깥으로 옮기는 방식은 고리와 버클의 윗부분을 띄웠다.
  이번에는 정점별로 천 바깥면에 투영한 뒤 장식의 두께와 삼각형 중심 간격을 보정했다.
  허리밴드는 피부·속옷 바깥면의 접촉 지점에서 가중치를 직접 전사한다.
  장식도 바로 아래 천의 가중치를 전사해 같은 움직임을 따른다.
  허리 전체를 골반에 고정하는 방식은 옆 피부가 관통해 폐기했다.
- 뒤 허리는 피부와 별도 속옷 메시를 함께 기준으로 삼아 둘레 방향으로 약 7mm의 여유를 확보했다.
  최근접 면의 노멀 방향으로 밀면 뒤 허리 옆부분이 벌어져, 바깥쪽 광선으로 간격을 계산하도록 수정했다.
  몸체·속옷 원본, 골반에 걸치는 높이, 원본 UV와 텍스처는 유지했다.
- 기본 자세와 대기·걷기 각각 33프레임에서 앞 고리·버클의 바깥쪽 면 중심에서 1mm 초과 묻힘 샘플은 0개다.
  장식 뒷면은 천에 최대 약 2mm 겹치며, 검사는 3mm를 상한으로 별도 제한한다.
  실제 천 바깥면과의 최대 간격은 고리 약 5.3mm, 버클 약 6.7mm다.
  금속 앞면을 포함하므로 고리는 6mm, 버클은 7mm를 상한으로 검사한다.
  뒤 중앙 허리 정점·삼각형 중심의 속옷 관통 샘플은 0개이며, 속옷 경계를 벗어난 광선 누락은 별도 기록한다.
- 65본 연결과 9개 동작 각각 33프레임의 유한 변형·가중치 검사를 통과했다.
  브라우저의 앞·뒤·옆 확대, 대기·걷기, 착탈 복원과 리소스 로드를 확인했다.
  큰 다리 굽힘·앉기에서 남는 관통 보정 범위는 이전 버전과 같다.
- 치마 2,710 triangles, 상의 3,751 triangles를 유지한다. 조합의 숨김 포함 합계는 28,636 triangles, 가림 적용 후는 24,198 triangles다.
  머리·얼굴 배분은 v1과 같다. 검수 중간 파일은 통합 기록과 대표 이미지로 정리했다.

[현재 GLB](../../assets/items/female_rogue_skirt/tripo_v1/fitted_v4/bottom_female_rogue.glb),
[현재 Blender](../../assets/items/female_rogue_skirt/tripo_v1/fitted_v4/female-rogue-skirt.blend),
[피팅·동작·고리·속옷 간격 통합 기록](../../assets/items/female_rogue_skirt/tripo_v1/fitted_v4/fitting.json),
[가림 정보](../../assets/items/female_rogue_skirt/tripo_v1/fitted_v4/body-occlusion.json).

[정면 확대](../../assets/items/female_rogue_skirt/tripo_v1/fitted_v4/review/detail-front.png),
[옆면 확대](../../assets/items/female_rogue_skirt/tripo_v1/fitted_v4/review/detail-side.png),
[뒷면 확대](../../assets/items/female_rogue_skirt/tripo_v1/fitted_v4/review/detail-back.png).

![고리·버클과 뒤 허리 보정 앞뒤](../../assets/items/female_rogue_skirt/tripo_v1/fitted_v4/review/fitting.png)

## 출처·라이선스

- 원화: OpenAI Codex built-in ImageGen(`codex exec`, codex-cli 0.162.1), **ChatGPT Pro 20x**, 2026-10-25.
  OpenAI 출력물 이용 조건을 따른다. 참조 원화의 출처는 [캐릭터 문서](characters.md)에 있다.
  [프롬프트](../../assets/items/female_rogue_skirt/concept_v1/prompt.txt),
  [출처·해시](../../assets/items/female_rogue_skirt/concept_v1/sources.json),
  [참조 입력](../../assets/items/female_rogue_skirt/concept_v1/reference-crop.png)(원화를 흰 바탕에 합성해 `[216,470,400,250]`을 FFmpeg로 자름).
- 3D: Tripo API 유료 크레딧, 모델 `P2-20260801`, 텍스처 `v3.5-20260815`, detailed PBR, 입력 조명 제거,
  목표 3,000 triangles, seed 102502, 2026-10-25. 입력은 원화 앞 `[0,80,768,700]`·뒤 `[768,80,768,700]`을
  잘라 848×848 단색 여백에 붙인 두 장이다.
  작업 ID `76b21712-3c80-4a29-891a-38a5e3055653`, **120크레딧**(잔액 160 → 40).
  [API 문서](https://developers.tripo3d.ai/en/docs/generation-multiview-to-model/p),
  [이용 조건](https://developers.tripo3d.ai/en/terms).
  기존 작업은 재제출 없이 `tools/outfits/tripo.py`로 조회·회수한다.
- [제작 명세](../../assets/items/female_rogue_skirt/tripo_v1/build.json),
  [요청·비용·작업 기록](../../assets/items/female_rogue_skirt/tripo_v1/generation.json),
  [입력](../../assets/items/female_rogue_skirt/tripo_v1/inputs/),
  [Tripo GLB](../../assets/items/female_rogue_skirt/tripo_v1/source/model_url.glb),
  [생성 미리보기](../../assets/items/female_rogue_skirt/tripo_v1/source/rendered_image_url.png),
  [원본 Blender](../../assets/items/female_rogue_skirt/tripo_v1/source.blend)([스크립트](../../assets/items/female_rogue_skirt/tripo_v1/review_source.py)).
