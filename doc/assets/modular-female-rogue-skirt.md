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
