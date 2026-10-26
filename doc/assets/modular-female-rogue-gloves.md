# 여성 로그 장갑

2026-10-26. 새 Tripo 장갑의 가죽·봉제선·스냅을 여성 양손에 맞추고 기존 여성 65본 리그에 연결했다.
현재 파일은 `assets/items/female_rogue_gloves/tripo_v1/fitted_v1/`이다.
여성 미리보기의 **로그 검은 가죽 반장갑**은 이 새 피팅본을 사용한다.

![새 장갑 착용](../../assets/items/female_rogue_gloves/tripo_v1/fitted_v1/review/preview.png)

## 최종 파일

- [GLB](../../assets/items/female_rogue_gloves/tripo_v1/fitted_v1/gloves_female_rogue.glb)
- [Blender 편집본](../../assets/items/female_rogue_gloves/tripo_v1/fitted_v1/female-rogue-gloves-fitted.blend)
- [피팅 기록](../../assets/items/female_rogue_gloves/tripo_v1/fitted_v1/fitting.json),
  [출처·라이선스](../../assets/items/female_rogue_gloves/tripo_v1/fitted_v1/sources.json),
  [피부 가림](../../assets/items/female_rogue_gloves/tripo_v1/fitted_v1/body-occlusion.json)
- [동작 검사](../../assets/items/female_rogue_gloves/tripo_v1/fitted_v1/runtime-validation.json),
  [피부 간격 검사](../../assets/items/female_rogue_gloves/tripo_v1/fitted_v1/clearance-validation.json),
  [브라우저 검사](../../assets/items/female_rogue_gloves/tripo_v1/fitted_v1/browser-validation.json)
- [조립 삼각형 수](../../assets/items/female_rogue_gloves/tripo_v1/fitted_v1/assembly-counts.json),
  [파일 해시](../../assets/items/female_rogue_gloves/tripo_v1/fitted_v1/local-artifacts.json)

착용 미리보기:
`/modular-character-preview.html?character=female&gloves=rogue&top=rogue&bottom=rogue&boots=rogue&camera=right-hand`.
원본 단독 보기는 `?asset=female-rogue-glove`이며 착용 보기 링크도 제공한다.

## 피팅·리깅

- 기준 몸체: `assets/modular_human_female_01/rig_v1/female-base.glb`, 키 약 1.8m.
  `human_female_01_local_v1`, 65본, 기존 기준 자세와 inverse bind를 유지했다.
  Blender Metric, `scale_length = 1`, 메시·리그 스케일 1, 런타임 배율 1이다.
- 오른손 1,179삼각형(손 표면 1,075 + 원본 스냅 104), 왼손 1,171삼각형(1,067 + 104),
  양손 합계 **2,350삼각형**이다. 예산 수치를 맞추기 위한 데시메이션은 하지 않았다.
- 원본의 굽은 손가락을 직접 변형하면 손바닥 연결부가 접히고 피부가 노출됐다.
  최종 손 표면은 실제 여성 피부와 가중치를 따라 재구성했다. 좌우 손을 각각 사용하며,
  손가락 입구 5개와 손목 입구를 열고 손가락 끝은 남긴다.
- 겹치는 원본 안쪽 면·손목 표면은 새 손 표면으로 대체했다. 두 원본 금속 스냅 조각은 보존했다.
- 스냅을 개별 방사 방향으로 밀어내던 피팅 때문에 두 단추가 커프에서 떠 보였다.
  손등·손바닥 쪽 커프 표면에 각각 배치하고, 단추 뒷면을 가죽 곡률에 맞춰 접촉시켰다.
  각 접촉 위치의 가중치를 옮겨 손목을 움직일 때 가죽과 함께 변형된다.
- 새 Tripo의 컬러·ORM·노멀을 연속된 손등·손바닥 UV로 옮겼다.
  노멀 벡터를 새 UV의 탄젠트 공간에 맞춰 회전해 UV 경계의 면 음영을 줄였다.
  최종 아틀라스는 각 **4096×2048**, 손등·손바닥 차트는 각각 1024²다.
  원본 4096² 맵과 생성 GLB는 별도로 보존했다. 새 AI 텍스처나 유료 요청은 없다.
- 손을 감싸는 표면은 피부에서 최대 3mm 띄우며 엄지·검지 사이는 얇게 연결한다.
  장갑 안의 피부 1,534삼각형을 개구부에서 6mm 여유를 두고 가린다.
  장갑을 벗으면 복원하며 칠부 소매와 장갑 사이의 팔뚝은 남긴다.

## 검증

실제 `bindModularPart`에서 65본·inverse bind 일치, 정규화된 최대 4개 가중치,
반대 손 가중치 유입 방지와 UV 이음을 확인했다. 14개 동작을 각각 33시점에서 검사했다.
기본 자세와 동작별 9시점, 총 **127자세 × 양손**의 정점·삼각형 중심 검사에서
2mm 초과 피부 관통 후보는 0개다. 최근접 면을 이용한 표본 검사이며 연속 동작의 모든 충돌을 보장하지 않는다.

[스냅 접촉 검사](../../assets/items/female_rogue_gloves/tripo_v1/fitted_v1/snap-validation.json)는
양손의 앞뒤 단추를 같은 127자세에서 별도로 검사한다.
단추 뒷면 정점과 실제 장갑 사이의 최대 양의 간격은 0.34mm 미만이다.

브라우저에서 착탈·다른 장갑 교체와 검·횃불 장착을 확인했고 페이지 오류와 실패 요청은 0개다.
`npm run check`, `npm run lint`를 통과했다. 현재 연결 범위는 여성 캐릭터 미리보기다.

몸체+로그 상의·치마·부츠·장갑·자동 가터는 숨김 포함 35,964삼각형,
가림 적용 후 26,822삼각형이다. 헤어·무기·망토는 제외했다.
기존 얼굴 앞쪽 범위 추정치는 3,489삼각형이며 얼굴 메시·텍스처는 변경하지 않았다.

```bash
.venv/bin/python tools/fit-female-rogue-tripo-gloves.py
node tools/validate-female-rogue-gloves.mjs
.venv/bin/python tools/validate-female-rogue-gloves-clearance.py
.venv/bin/python tools/validate-female-rogue-glove-snaps.py
blender -b -t 8 --python-exit-code 1 -P tools/blender-scripts/review_female_rogue_gloves.py
```

## 생성·출처

- 원화: [피부 없는 반장갑 concept_v2](../../assets/items/female_rogue_gloves/concept_v2/sheet.png),
  OpenAI Codex built-in ImageGen, **ChatGPT Pro 20x**, 2026-10-26.
  OpenAI 생성 출력물 이용 조건 적용. [프롬프트·기록](../../assets/items/female_rogue_gloves/concept_v2/sources.json).
- 원화 참조: [여성 로그](../../client/public/character_concepts/female_rogue.webp).
- 새 메시: Tripo API **유료 크레딧**, `P2-20260801`, 1,800삼각형 목표(실제 1,848),
  상세 PBR `v3.5-20260815`, 입력 조명 제거. 손등을 front, 손바닥을 back으로 별도 제출했다.
- 작업 ID `f0c5fc77-42b0-4b9a-a6f6-435bf6f7534b`, **120크레딧**, 2026-10-26.
  [제출 명세](../../assets/items/female_rogue_gloves/tripo_v1/build.json),
  [작업·비용](../../assets/items/female_rogue_gloves/tripo_v1/generation.json).
  [Tripo 이용 조건](https://developers.tripo3d.ai/en/terms)을 따른다.
- [생성 GLB](../../assets/items/female_rogue_gloves/tripo_v1/source/model_url.glb),
  [Blender 원본](../../assets/items/female_rogue_gloves/tripo_v1/source.blend),
  [원본 텍스처](../../assets/items/female_rogue_gloves/tripo_v1/source/textures.json),
  [원본 진단](../../assets/items/female_rogue_gloves/tripo_v1/review.json).
- 손 표면은 [여성 공통 몸체](modular-human-female-01.md)의 출처·이용 조건을 따른다.

## 이전 시도

- **[미사용] `fitted_v1/`**: 남성 메시 재사용본. 사용자가 재질 표현을 보고 새 Tripo 생성을 요청했다.
  [이전 출처·작업 기록](../../assets/items/female_rogue_gloves/fitted_v1/sources.json)은 보존하고,
  사용하지 않는 피팅 GLB·Blender·텍스처·검수 출력은 삭제했다.
- **[미사용] concept_v1**: 손과 피부를 함께 그려 장갑 단독 3D 생성 입력으로 부적합했다.
- 새 원본 전체를 직접 피팅하던 중 손가락·손바닥 접힘, 안쪽 면 겹침과 동작 늘어남을 발견했다.
  실제 손 표면과 원래 가중치, 연속 UV의 PBR 투영으로 보정했다.

커밋 전 반복 검수 렌더와 피팅 캐시·포즈 덤프를 정리했다. 원화·Tripo 원본·최종 편집본과
문서용 이미지는 보존했다. 검증용 캐시는 위 제작·검증 명령 순서로 다시 생성한다.
