# 여성 바바리안 가죽 하이힐 샌들 — 2026-10-15

여성 바바리안 원화에서 신발을 분리해 Tripo로 생성하고 여성 공통 몸체에 피팅했다.
현재 **피팅 v3**를 여성 미리보기에 연결했다. 장비 등록은 하지 않았다.
신발의 뒤꿈치 방향과 발목 고리 간격을 조정했다. 일부 동작의 앞끈과 왼발 뒤꿈치 옆 끈 관통은 추가 피팅이 필요하다.

![앞·옆·뒤 원화](../../assets/items/female_barbarian_boots/concept_v1/sheet.png)

## 출처와 생성

- 디자인: [여성 바바리안 원화](../../client/public/character_concepts/female_barbarian.webp).
  굽 형태는 [여성 기사 판금 부츠](modular-female-knight-boots.md)를 참조했다.
- 원화 제작: OpenAI Codex built-in ImageGen(`codex exec`, codex-cli 0.162.1),
  **ChatGPT Pro 20x**, 2026-10-15. OpenAI 출력물 이용 조건을 따른다.
  참조 원화의 출처는 [캐릭터 문서](characters.md)에 있다.
- [프롬프트](../../assets/items/female_barbarian_boots/concept_v1/prompt.txt),
  [참조·분리 영역·해시 기록](../../assets/items/female_barbarian_boots/concept_v1/sources.json).
  앞·옆·뒤 입력은 같은 배율의 800×800 흰 정사각형으로 분리했다.
  2026-10-16 원화 폴더의 앞·옆·뒤 중복 사본 3개는 삭제하고, 동일한 입력 이미지는 `tripo_v1/inputs/`에 보존했다.
  원화 시트·참조 이미지·프롬프트·출처 기록과 시점별 분리 좌표는 유지한다.
- Tripo API 유료 크레딧, 모델 `P2-20260801`, 텍스처 `v3.5-20260815`, detailed PBR,
  입력 조명 제거, 한 짝 목표 1,500 triangles, seed 101502.
  [API 문서](https://developers.tripo3d.ai/en/docs/generation-multiview-to-model/p),
  [이용 조건](https://developers.tripo3d.ai/en/terms).
- 작업 ID `a4ac552f-032f-4822-9978-fad40d1ff10e`, **120크레딧 사용**.
  [제작 명세](../../assets/items/female_barbarian_boots/tripo_v1/build.json),
  [요청·비용·작업 기록](../../assets/items/female_barbarian_boots/tripo_v1/generation.json).
  추가 유료 생성 없이 기존 결과를 사용했다.

착용자 오른쪽 한 짝을 생성했다. 앞이 트인 갈색 가죽 샌들, 발목 고리 세 줄,
리벳·버클, 넓은 앞끈과 가는 스틸레토 굽으로 구성한다. 폴더 이름은 장비 슬롯(`boots`)에 맞췄다.
원본은 메시 1개, **1,664 triangles**, 4K 컬러·노멀·ORM 텍스처다.
연결 성분 9개, 경계선 3개, 퇴화 면·UV 붕괴 0개로 진단했다.

![Tripo 원본 검토](../../assets/items/female_barbarian_boots/tripo_v1/review/strip.png)

| 보존 원본 | 파일 |
| --- | --- |
| Tripo GLB | [model_url.glb](../../assets/items/female_barbarian_boots/tripo_v1/source/model_url.glb) |
| 원본 Blender | [source.blend](../../assets/items/female_barbarian_boots/tripo_v1/source.blend) |
| 생성 미리보기 | [rendered_image_url.png](../../assets/items/female_barbarian_boots/tripo_v1/source/rendered_image_url.png) |
| 원본 진단 | [review.json](../../assets/items/female_barbarian_boots/tripo_v1/review.json), [재현 스크립트](../../assets/items/female_barbarian_boots/tripo_v1/review_source.py) |

## 현재 피팅 v3

기준 몸체는 `assets/modular_human_female_01/rig_v1/female-base.glb`,
리그는 `human_female_01_local_v1` 65본이다. 몸체·공통 발 코드·애니메이션 파일을 유지한다.
기존 기사 부츠와 같은 `tools/outfits/female_boot_pose.py`의 굽 자세(Foot +30°, ToeBase −30°)에서 피팅한다.

- 신발을 기존 Foot→ToeBase 방향에서 바깥쪽으로 **7°** 더 회전해 뒤꿈치가 밑창 중심에 맞게 했다.
  최종 각도는 착용자 오른쪽 **−17.954°**, 왼쪽 **+17.954°**다.
  길이·폭 정렬도 이 좌표계에서 다시 계산하고 발목 고리와 끈을 재피팅했다.
- 왼발은 같은 각도를 유지한 채 밑창·굽을 발의 가로축을 따라 바깥쪽으로
  **0.0055 source unit(9.9mm)** 옮겨 발 중심선에 맞췄다. 발목 고리까지 이동량을
  부드럽게 줄여 고리 위치를 유지했다.
- 왼발은 각도·가로축 정렬을 유지하며 밑창·굽을 뒤꿈치 방향으로
  **0.003 source unit(5.4mm)** 옮겼다. 발목 고리는 유지하고 앞끈의 피부 여유를
  다시 확보했다. 이 조정에서 오른쪽 신발의 형상·웨이트는 그대로다.
- 오른쪽 밑창 앞끝은 발가락 아래에 가까워지도록 정지 기준 최대 **5.4mm** 들어 올렸다.
  앞끝으로 갈수록 완만하게 높이고, 밑창 윗면의 정점·면 내부 표본에서 피부까지의
  수직 여유를 계산해 피부와 틈이 남도록 들림을 제한했다.
  발볼 접지·뒤꿈치·발목 고리와 왼쪽 신발은 유지했다.
- 오른쪽 앞끝에만 기존 발가락 동작을 최대 **0.45** 비율로 추가 전사했다.
  발가락이 들릴 때 앞 밑창도 함께 올라가며 발볼 접지는 Foot을 유지한다.
  과하게 말린 앞끝을 완화하도록 정지 들림을 7.2→5.4mm, 동작 전사를 0.55→0.45로 줄였다.
- 앞끝 들림과 발가락 웨이트는 이차 곡선으로 점진적으로 증가시켜 밑창의 급한 꺾임을 줄였다.
  오른쪽 발등 스트랩 윗부분은 최대 **7.2mm** 올리고, 밑창에 닿는 부분까지 이동량을
  부드럽게 줄여 연결을 유지했다. 피부 표면 방향으로 최대 **1.8mm** 여유도 추가했다.
- 발목 고리의 각도는 고리 자체 중심에서 계산한 뒤 다리 피부에 맞춘다.
  오른발 형상을 대칭한 후 왼발 피부에서 별도로 피팅하고 웨이트를 전사한다.
- 발목 고리의 기본 반경 여유를 **11.7→5.4mm**로 줄였다.
  왼쪽은 고리와 앞끈의 여유를 따로 적용하고, 고리 정점 사이의 면 내부도 피부와
  비교해 보정했다. 정점만 맞췄을 때 생기던 왼쪽 고리의 피부 관통을 줄인다.
- 왼쪽 발목 앞쪽에 남은 틈은 세 줄 고리를 최대 **9mm** 뒤로 당겨 줄였다.
  실제 왼쪽 다리 단면을 기준으로 옆쪽까지 이동량을 부드럽게 줄인다.
  아래 고리의 가장자리도 함께 옮겨 가죽 단면을 유지하고, 앞쪽 표면의 여유는
  **3.6mm**를 기준으로 재보정했다. 오른쪽 신발과 왼쪽 밑창·앞끈·굽의
  전체 메시 속성, 피부 가림은 이전 결과와 같음을 확인했다.
- Tripo에서 빠진 뒤쪽 세로 연결끈을 두께 있는 메시로 추가했다.
  한 짝 148 triangles 증가, 두 짝 **3,624 triangles**다. 기존 굽의 가죽 UV 영역을 재사용한다.
- 뒤 연결끈과 가로 고리가 교차해 깜빡이던 부분을 수정했다.
  처음에는 양쪽의 실제 고리 면을 연결끈 구간에 투영해, 연결끈을 고리 바깥면보다 **2.7mm** 뒤에 놓았다.
  교차는 줄었지만 연결부가 떠 보여 아래의 접촉 피팅으로 대체했다.
  이 연결끈 조정 당시 기존 고리·버클·앞끈·밑창·굽의 정점 속성과 피부 가림은 유지했다.
- 연결끈 옆 가운데 가로 고리에도 별도의 깜빡임이 남아 있었다.
  피부 여유를 확보하면서 고리 내·외면이 거의 같은 위치로 눌린 것이 원인이었다.
  원본의 안쪽 벽을 노멀과 방사선 첫 교점으로 구분하고, 안쪽 피팅을 유지하며 바깥 벽의
  두께를 정지 기준 오른쪽 **5.4mm**, 왼쪽 **2.7mm** 이상 확보했다.
  바깥 벽의 웨이트도 대응하는 안쪽 면에서 전사해 발목이 꺾일 때 함께 움직이게 했다.
  가운데 고리의 바깥 벽과 연결끈 배치를 갱신했으며, 위·아래 고리와 앞끈·밑창·굽은 유지했다.
- 뒤 세로 연결끈은 세 고리의 실제 뒷면에 붙도록 다시 피팅했다.
  끈 안쪽을 고리 표면에 **0.36mm** 묻고, 접점 사이를 보간한다.
  가죽 두께는 최소 **2.7mm**를 유지하며, 바깥 면만 별도로 고리 면과 비교해 정리했다.
  안쪽 접촉을 유지하므로 바깥 면의 여유가 연결부 전체를 띄우지 않는다.
  접점 웨이트는 해당 고리 삼각형에서 전사하고, 양쪽 두께 정점에 같은 웨이트를 적용했다.
  기존 신발의 모든 정점 속성과 피부 가림은 그대로다.
- 발목은 피부의 Leg/Foot 비율을 공간상 0.004 source unit 반경에서 다듬고,
  버클은 주변 고리 평균을 쓴다. 뒤꿈치 끈은 Foot에서 아래 고리로 점진적으로 전환한다.
  뒤 세로 연결끈은 접점의 고리 웨이트를 전사하고 고리 사이 구간을 보간한다.
- 아래 고리와 뒤꿈치를 잇는 양옆 끈의 꺾임을 줄였다.
  각 끈의 앞·뒤 가장자리와 두께 정점을 함께 정리하고 위아래 연결점은 유지했다.
  피부 여유가 적은 앞쪽 가장자리는 일부 곡률을 남겼다. 모든 가장자리를 완전히 일직선으로
  펴는 후보는 피부 관통 때문에 채택하지 않았다. UV·본·웨이트와 다른 부위의 정점 속성은 그대로다.
- 아래 가죽 고리의 뒤쪽이 넓어 보이는 부분은 세로 폭을 최대 **16%** 줄였다.
  고리 중심을 유지하며 위아래 가장자리를 모으고 옆쪽으로 갈수록 조정량을 부드럽게 줄였다.
  피부와의 가로 간격과 기존 UV·본·웨이트는 유지하고, 뒤 세로 연결끈은 바뀐 고리에 다시 붙였다.
- 아래 링 뒷면에도 안쪽 가죽이 바깥 면을 뚫고 보이는 문제가 있었다.
  뒤쪽 바깥 면 23개를 안쪽 면에서 수평으로 분리하고, 정지 기준 목표 간격을 **3.6mm**로 잡았다.
  앞서 줄인 세로 폭과 안쪽 피부 피팅은 유지한다. 바깥 면의 UV 이음새를 포함한 61정점에는
  대응하는 안쪽 면의 웨이트를 전사하고, 같은 위치의 중복 정점도 함께 움직이게 했다.
  뒤 세로 연결끈은 다시 접촉 피팅했다. 앞쪽 버클·다른 고리·밑창·굽의 형상과 웨이트는 유지했다.
- 앞쪽 발등 끈도 안쪽 면이 위로 드러나 검은 가죽과 금속색 조각이 끼어 보였다.
  안쪽 13면과 바깥쪽 92면의 수평 투영을 비교해 겹치는 다각형 전체에서 윗면 높이를 보정했다.
  안쪽 피팅과 가로 폭은 유지하고, 두 면이 이어지는 가장자리에서는 목표 간격 **2.7mm**를 0까지 줄인다.
  필요한 들림의 제곱합을 최소화해 바깥 면을 정리하고, UV 이음새를 포함한 양발 각 172정점에
  대응 안쪽 면의 웨이트를 전사했다. 본래 발가락 애니메이션과 다른 부위의 정점 속성은 유지했다.
- 앞끈 양옆의 세워진 가죽에도 별도 겹침이 남아 있었다. 윗면 검사에 포함되지 않았던
  양옆 바깥 11면·14면과 안쪽 각 4면을 신발의 가로 방향으로 분리했다.
  안쪽 면과 전체 정점의 높이는 유지하고, 이음새 웨이트를 맞춘 뒤 윗면도 다시 검사했다.
- 오른발의 표시된 옆면은 바깥 면끼리도 접혀 겹쳤다. 기존 내·외면 검사만으로는 검출되지 않았다.
  해당 14면의 투영 외곽을 한 겹으로 다시 연결하고, 기존 전용 정점 슬롯 14개를 재사용했다.
  고정된 안쪽 면과 인접 마감 면 3개에서 간격을 확보하고, 기존 아틀라스의 가죽 영역으로 UV를 이어 붙였다.
  전체 삼각형 수 **3,624개**, 왼발의 모든 정점 속성과 면 연결, 다른 부위의 위치·UV·웨이트는 유지했다.
- 앞끈의 ToeBase 영향은 밑창 위 높이에 따라 최대 0.35다.
  오른쪽 앞끝을 제외한 밑창·굽은 Foot을 유지한다.
  v2에서 추가했던 `fixed_toe_quaternions`와 공통 런타임의 전용 처리를 제거했다.
  발가락 본은 원래 애니메이션에 기존 공통 굽 오프셋만 적용한다.
- 밑창 가장자리가 굽 끝의 바닥 높이 아래로 내려가지 않게 고정했다.
  정지 자세 루트 보정은 기사 부츠와 같은 **0.0302733 source unit**이다.
- 양쪽의 실제 피팅 형상으로 발바닥 아래 91면만 가리는 가역 마스크를 사용한다. 발목 고리 사이와 발등은 유지하며
  장비를 벗거나 로딩에 실패하면 원래 피부를 복원한다.

좌표는 정규화된 여성 몸체의 source unit이다. 실제 1.8m 캐릭터에서는 거리 값에 1.8을 곱한다.
`clearance_m`에는 변환한 값을 기록한다. 새 연결끈은 기존 Tripo 텍스처를 쓰는 직접 제작 메시로
원본과 같은 출처·라이선스를 따른다.

2026-10-16 검토 이미지 12개(현재 피팅 스트립 1개·수정 전후 비교 11개)와 `fitted_v3/review/` 폴더를 삭제했다.
현재 부츠 모델·Blender·피팅 입력·마스크와 수정 수치·검증 기록은 유지한다.

| 현재 파일 | 경로 |
| --- | --- |
| 신발 GLB | [boots_female_barbarian.glb](../../assets/items/female_barbarian_boots/tripo_v1/fitted_v3/boots_female_barbarian.glb) |
| 편집용 Blender | [female-barbarian-boots-fitted.blend](../../assets/items/female_barbarian_boots/tripo_v1/fitted_v3/female-barbarian-boots-fitted.blend) |
| 피부 가림 | [body-occlusion.json](../../assets/items/female_barbarian_boots/tripo_v1/fitted_v3/body-occlusion.json) |
| 피팅·리깅 기록 | [modular-female-barbarian-boots-fitting-v3.json](modular-female-barbarian-boots-fitting-v3.json) |
| 후속 검사용 형상·웨이트 | [fit-data.npz](../../assets/items/female_barbarian_boots/tripo_v1/fitted_v3/fit-data.npz) |
| 동작별 굽 보정 | [heel-animation-offsets.json](../../assets/items/female_barbarian_boots/tripo_v1/fitted_v3/heel-animation-offsets.json) |

현재 몸체 22,175 + 단발 2,436 + 샌들 3,624 = 전체 **28,235 triangles**,
발바닥 가림 후 **28,144 triangles**다. 얼굴 앞면은 속눈썹을 포함해 **4,604 triangles**다.
기존 몸체만으로 모듈형 목표 예산을 넘는 상태이며 이번 작업에서 임의로 축소하지 않았다.

## 검증과 남은 작업

- [리그·동작 검사](../../assets/items/female_barbarian_boots/tripo_v1/fitted_v3/runtime-validation.json):
  14동작 × 61시점. 65본 bind 일치, 정규화 웨이트, 반대쪽 다리 영향 없음,
  피부 가림 복원, 원래 발가락 애니메이션 유지, 발 자세 누적 없음, 굽 접지 검사를 통과했다.
  접지 평면은 굽 끝과 Foot에 고정된 발볼로 검사해 움직이는 앞끝을 제외한다.
- 브라우저 기록:
  오류 없음, 착탈 반복 시 24,611 ↔ 28,144 triangles로 복원됨을 확인했다.
- 오른쪽 발목 검사,
  왼쪽 발목 검사:
  각 **855시점**(정지 + 14동작 × 61시점)에서 고리·버클·뒤 연결끈을 검사해 통과했다.
  기존 허용오차는 0.0002 source unit(0.36mm)이며, 최저 발목 거리는 오른쪽 −0.12mm,
  왼쪽 +2.63mm다. 발목 목표 여유는 모든 동작의 실제 최단 거리와 같지는 않다.
  아래 링 뒷면 수정 후 양발 855시점을 다시 검사했다.
- 오른쪽 연결끈 겹침 검사,
  왼쪽 연결끈 겹침 검사:
  접촉 피팅 후 양발 각 855시점에서 **노출된 바깥 면**과 고리·버클의 모서리→면 교차를
  양방향으로 검사해 **0건**을 확인했다. 바깥 면의 최단 표본 거리는 오른쪽 **0.82mm**, 왼쪽 **1.86mm**다.
  안쪽 면은 접합을 위해 의도적으로 묻으므로 전체 연결끈의 무교차를 요구하지 않는다.
  오른쪽 25개·왼쪽 27개 접점을 대응하는 실제 포즈의 고리 삼각형과 비교했다.
  정지 접점 거리는 0.36mm이고, 전체 동작의 최대 거리는 오른쪽 **2.70mm**, 왼쪽 **1.31mm**다.
  접촉 피팅 보존 검사에서
  당시 기존 신발의 모든 정점 속성과 피부 가림이 일치함을 확인했다.
  아래 링 뒷면 수정 후에도 연결끈 겹침 검사를 양발 855시점에서 다시 실행했다.
  앞선 연결끈 보존 검사는
  연결끈만 조정한 이전 시점의 기록이다. 이 검사는 고리 자체의 내·외면 겹침을 확인하지 않아
  가운데 고리의 남은 깜빡임을 잡지 못했다.
- 오른쪽 가운데 고리 검사,
  왼쪽 가운데 고리 검사:
  양발 각 **855시점**에서 내·외면의 양방향 모서리→면 교차 **0건**을 확인했다.
  최단 표본 거리는 오른쪽 **1.86mm**, 왼쪽 **0.84mm**다. 수정 전 왼발은 비교한 29시점 모두 교차했다.
  브라우저 표시 검사에서는
  표시 구간의 바깥 면 4곳 × 인접 각도 5개 × 대기 시점 3개를 추적했다.
  안쪽 면이 먼저 보이던 표본이 수정 전 **30/60 → 수정 후 0/60**으로 줄었다.
  가운데 고리 보존 검사는
  가운데 고리를 수정한 이전 시점의 기록이다. 이후 접촉 피팅에서 기존 고리의 정점 속성이
  모두 같음을 확인하고 내·외면 검사 결과를 재사용했다.
  이번 양옆 끈 수정에서도 검사에 참여하는 고리 정점 속성과 토폴로지가 정확히 같아
  내·외면 검사 결과를 재사용했다. 브라우저의 60개 표본 검사는 양옆 끈 수정 전 기록이다.
  이후 아래 링 폭 수정에서는 공유되는 가장자리 정점이 바뀌어 양발 855시점을 다시 검사했다.
  다른 고리·금속 장식의 모든 자체 교차나 연속 시점 전체의 무관통을 보장하는 검사는 아니다.
- 오른쪽 발등 스트랩 검사:
  정지 자세와 대기 동작의 전체 61시점에서 스트랩의 정점·면 중심·모서리 중간 지점을 검사했다.
- 오른쪽 앞끈 내·외면 검사,
  왼쪽 앞끈 내·외면 검사:
  양발 각 **855시점**에서 양방향 모서리→면 교차가 **0건**이다. 수정 전 비교한 양발 29시점은 모두 교차했다.
  두 면이 붙는 공통 가장자리의 정점·모서리는 간격 표본에서 제외했다. 그 밖의 최단 표본 거리는
  오른쪽 **0.52mm**, 왼쪽 **0.64mm**이고 검사 하한은 **0.09mm**다. 고리처럼 완전히 분리된 두 벽과 달리
  가장자리가 이어져 있으므로 경계에서 간격이 줄어든다.
  브라우저 표시 검사는
  양발의 앞쪽 인접 각도 5개와 대기 동작의 시작·중간·끝에서 바깥 면 중심을 추적했다.
  윗면 수정 당시 안쪽 면이 먼저 보이는 표본이 **1,233건 → 0건**으로 줄었다. 이 브라우저 기록은 옆면 수정 전이다.
  보존 검사에서
  끈의 가로 위치·안쪽 면·UV·토폴로지·피부 가림과 나머지 정점 속성이 정확히 같으며,
  양발 각 UV 이음새 62그룹의 위치·웨이트가 일치함을 확인했다.
  피부 관통 비교에서는
  정지·대기 62시점은 양발 모두 통과했지만, 전체 동작 피부 간격은 미완료다.
  각 171시점의 관통 프레임 수는 오른쪽 **82→82**, 왼쪽 **79→77**이며 새로 관통하는 시점은 없다.
  이미 관통하던 일부 시점은 최대 오른쪽 **1.87mm**, 왼쪽 **1.24mm** 깊어져 추가 피팅이 필요하다.
- 앞끈 양옆 검사는 각 옆면·양발의 **855시점**에서 면 교차 **0건**을 확인했다.
  현재 한쪽 옆면의 최단 표본 거리는 오른발 **1.02mm**, 왼발 **1.62mm**이고,
  반대쪽은 오른발 **2.03mm**, 왼발 **1.21mm**다. 윗면 검사도 양발 855시점을 통과했다.
  옆면 브라우저 검사에서
  양발의 좌우 시점·인접 각도 5개·대기 시작/중간/끝을 비교했다. 안쪽 면 노출 표본은 **135건 → 0건**이다.
  옆면 보존 검사는
  원래 높이·안쪽 면·UV·토폴로지·피부 가림과 다른 부위의 정점 속성을 확인했다.
  UV 이음새는 양발 각 66그룹의 위치·웨이트가 일치하며, 기존 정점 중 64개의 bind 위치가 바뀌었다.
  피부 비교에서
  양발 정지·대기 62시점은 통과했다. 전체 171시점은 기존 관통이 남아 있으나 새로 관통하는 시점은 없으며,
  기존 관통 깊이 증가는 오른발 0mm, 왼발 최대 **0.11mm**다.
- 오른발 자체 겹침 수정 후 바깥 면 검사는
  **855시점**에서 양의 면적을 가진 근접 겹침과 면 교차가 모두 **0건**이다.
  실제 오른발 브라우저 검사는
  사용자 시점 쪽 인접 각도 3개·대기 시작/중간/끝에서 총 126표본을 비교했다.
  모든 렌더 면 중 첫 두 교차점이 **0.09mm**보다 가까운 표본은 **48→0건**이다.
  오른발 윗면과 양옆 내·외면 검사도 각 855시점에서 교차 0건이며,
  왼발 기록은 전체 속성·면 연결 일치 증명에 따라 재사용했다.
  정지·대기 62시점은 통과했다. 피부 관통 비교의
  전체 171시점에는 기존 관통 **82→82시점**이 남아 있고, 새 관통 시점은 없다.
  이미 관통하던 일부 시점의 깊이는 최대 **1.55mm** 증가해 별도 피팅이 필요하다.
- 오른쪽 아래 링 검사,
  왼쪽 아래 링 검사:
  뒷부분 내·외면을 양방향 모서리→면 교차로 검사해 양발 각 **855시점 모두 0건**을 확인했다.
  최단 표본 거리는 오른쪽 **2.55mm**, 왼쪽 **2.44mm**다.
  수정 전에는 양발 모두 비교한 29시점에서 교차했다. 기존 가운데 링 검사는 이 부분을 포함하지 않았다.
  브라우저 표시 검사는
  양발의 뒤쪽 두 방향, 인접 각도 5개와 대기 시점 3개에서 정면을 향한 바깥 면 중심을 추적했다.
  안쪽 면이 먼저 보이는 표본은 **수정 전 75건 → 수정 후 0건**이다.
  보존 검사에서
  기존 정점의 높이·안쪽 면 위치·UV·토폴로지·피부 가림을 유지하고, 양발 각각 UV 이음새
  25그룹의 위치와 웨이트가 일치함을 확인했다. 다른 부위의 자체 교차까지 보장하는 검사는 아니다.
- 뒤꿈치 양옆 끈 비교 검사:
  양발 각 855시점을 수정 전과 비교했다. 양발 정지·대기 62시점은 통과했고,
  오른발 전체 855시점의 최저 거리는 **+0.10mm**다.
  왼발은 기존 관통이 있던 **73시점이 그대로 남았으며**, 새로 관통하는 시점은 없다.
  왼발 전체 최저 거리는 수정 전후 모두 **−2.90mm**다. 이미 관통하던 시점에서는
  최소 거리 기준 최대 **0.078mm**, 관통 표본 수 최대 24개의 증가가 있어 전체 동작 통과로 보지 않는다.
  보존 검사에서
  양발 각각 위치가 바뀐 58정점 외 형상과 모든 UV·본·웨이트, 피부 가림을 확인했다.
- 아래 링 폭 보존 검사:
  양발 각각 아래 링 뒤쪽 215정점의 높이와 노멀을 조정하고, 세로 연결끈을 다시 피팅했다.
  기존 신발에서 그 밖의 모든 정점 속성, 전체 UV·본·웨이트·토폴로지와 피부 가림은 정확히 같다.
  동작 비교 검사에서
  양발 각 855시점을 비교했다. 기존 왼발 뒤꿈치 끈 관통 73시점은 남았으며 새로 관통하는 시점은 없다.
- 오른발 끈 검사,
  왼발 끈 검사:
  각 171시점에서 발목·뒤 연결끈은 허용오차 내이지만 **앞끈은 미완료**다.
  오른발은 공격·달리기, 왼발은 걷기·횃불 달리기에서 피부 관통 표본이 남았다.
  아래 링 뒷면 수정 후 발목·뒤 연결끈·뒤꿈치 끈을 다시 검사했다. 앞끈은 검사 참여 정점의
  위치·노멀·본·웨이트·토폴로지가 정확히 같아 이전 표본 결과를 재사용했다.
  이후 앞끈 내·외면 수정에서 앞끈 표본을 다시 계산했다. 발목·뒤 연결끈·뒤꿈치 끈은
  검사 참여 정점 속성과 토폴로지가 정확히 같아 해당 결과를 재사용했다.
  발을 바꾸지 않고 신발 쪽을 추가 피팅할 과제다.
- 끈 검사는 정점·면 중심·모서리 중간 지점과 가리지 않은 피부 삼각형을 비교한다.
  밑창 내부 접촉이나 모든 연속 시점의 무관통을 보장하지 않는다.
- Tripo 텍스처의 넓은 금속색 얼룩도 남아 있다. 장비 등록과 프로덕션 적용은 하지 않았다.

## 이전 후보와 정리

2026-10-16 사용자 요청으로 상세 브라우저·관통·보존·수정 전후 검사 기록 54개를 삭제했다.
아래 과거 정리 시점의 보관 설명과 달리, 현재 `fitted_v3/`에는 부츠 GLB·Blender·fit-data·피부 가림 정보·
하이힐 동작 보정값·검토 스크립트가 읽는 `runtime-validation.json` 6개만 남긴다.
위 검사 수치와 남은 관통 문제는 요약 기록이며, 삭제한 프레임별 상세 결과 전체를 포함하지 않는다.

- **[미사용] v1**: 정면 축 기준 피팅, 3,328 triangles. 발목 고리 방향 계산과 뒤 연결끈 누락이 남았다.
  [피팅 기록](modular-female-barbarian-boots-fitting-v1.json)을 보존한다.
- **[미사용] v2**: 고리·연결끈과 접지를 보정했지만 발가락 자세 고정을 사용했다.
  사용자 지시에 따라 v3에서 이를 제거했다. [피팅 기록](modular-female-barbarian-boots-fitting-v2.json)을 보존한다.
- **[미사용] 앞 밑창 전체 ToeBase 전사 시도**: 밑창 모양과 늘어남이 악화되어 채택하지 않았다.
- v1/v2 피팅 바이너리, 중간 Blender, ARAP 캐시, 임시 몸체 GLB, 개별 렌더와 브라우저 비교 이미지는 삭제했다.
  현재 v3 GLB·Blender·후속 검사용 fit-data, 원화·입력·생성 원본·출처와 검증 기록은 보존했다.
  원본 검토 스트립은 유지하며 현재 피팅 스트립과 비교 이미지는 2026-10-16 추가 정리했다.
- 이번 중간 저장에서는 추가 피팅의 비교 이미지·후보 백업·임시 스크립트와 로그
  **251개(약 300MiB)**를 정리하고 현재 피팅과 원본·검증 기록을 보존했다.

## 미리보기와 재현

`/modular-character-preview.html?character=female&camera=feet&boots=barbarian&motion=idle1`에서 확인한다.
Python 의존성은 프로젝트 `.venv`의 NumPy, SciPy, trimesh 5.1.1, rtree 1.4.1, Shapely 2.1.2다.
저장소 루트에서 실행한다.

```bash
.venv/bin/python tools/fit-female-barbarian-boots.py
node tools/validate-female-barbarian-boots.mjs
node tools/export-female-barbarian-boots-poses.mjs
node tools/export-female-barbarian-boots-poses.mjs assets/items/female_barbarian_boots/tripo_v1/fitted_v3 left
.venv/bin/python tools/validate-female-barbarian-boots-clearance.py --stride 5
.venv/bin/python tools/validate-female-barbarian-boots-clearance.py --side left --stride 5
.venv/bin/python tools/validate-female-barbarian-boots-clearance.py --regions ankle connector --output ankle-validation.json
.venv/bin/python tools/validate-female-barbarian-boots-clearance.py --side left --regions ankle connector --output ankle-left-validation.json
.venv/bin/python tools/validate-female-barbarian-boots-clearance.py --regions heel --output heel-straps-right-validation.json
.venv/bin/python tools/validate-female-barbarian-boots-clearance.py --side left --regions heel --output heel-straps-left-validation.json
.venv/bin/python tools/validate-female-barbarian-connector-clearance.py
.venv/bin/python tools/validate-female-barbarian-connector-clearance.py --side left
.venv/bin/python tools/validate-female-barbarian-ring-walls.py
.venv/bin/python tools/validate-female-barbarian-ring-walls.py --side left
.venv/bin/python tools/validate-female-barbarian-ring-walls.py --ring lower
.venv/bin/python tools/validate-female-barbarian-ring-walls.py --ring lower --side left
.venv/bin/python tools/validate-female-barbarian-ring-walls.py --ring front
.venv/bin/python tools/validate-female-barbarian-ring-walls.py --ring front --side left
.venv/bin/python tools/validate-female-barbarian-ring-walls.py --ring front-side --panel 0
.venv/bin/python tools/validate-female-barbarian-ring-walls.py --ring front-side --panel 1
.venv/bin/python tools/validate-female-barbarian-ring-walls.py --ring front-side --panel 0 --side left
.venv/bin/python tools/validate-female-barbarian-ring-walls.py --ring front-side --panel 1 --side left
.venv/bin/python tools/validate-female-barbarian-panel-overlap.py
.venv/bin/python tools/validate-female-barbarian-boots-clearance.py --motions rest idle1 --output instep-idle-validation.json
blender -b --python-exit-code 1 --python tools/blender-scripts/review_female_barbarian_boots.py
```

현재 끈 관통 검사는 앞끈 문제를 검출하면 실패 종료한다. 피팅 재실행은 검증 기록을 새 후보로 갱신하므로
작업 후 리그 검사와 끈 검사를 다시 실행해야 한다. 임시 포즈 추출·렌더 파일은 재현 후 정리한다.
