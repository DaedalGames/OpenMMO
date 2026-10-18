# 여성 기사 판금 부츠

여성 기준 몸체 65본 리그에 연결한 높은 굽 판금 부츠다. 한쪽을 만들어 좌우 대칭으로 제작했다.
채택본은 `fitted_v5`이며 좌표는 미터 단위다([전환 기록](female-knight-runtime.md#원본-미터-단위-전환--2026-10-17)).
양쪽 **20,586삼각형**이다.

## 최종 파일

- [GLB](../../assets/items/female_knight_boots/fitted_v5/boots_female_knight.glb),
  [Blender 편집본](../../assets/items/female_knight_boots/fitted_v5/female-knight-boots-fitted.blend)
- [피팅 기록](../../assets/items/female_knight_boots/fitted_v5/fitting.json),
  [피부 가림](../../assets/items/female_knight_boots/fitted_v5/body-occlusion.json),
  [굽 자세](../../assets/items/female_knight_boots/fitted_v5/heel-pose.json),
  [동작별 굽 보정](../../assets/items/female_knight_boots/fitted_v5/heel-animation-offsets.json)
- [측면 형상 기록](../../assets/items/female_knight_boots/fitted_v5/side-profile.json),
  [동작 검사](../../assets/items/female_knight_boots/fitted_v5/runtime-validation.json),
  [브라우저 검사](../../assets/items/female_knight_boots/fitted_v5/browser-review.json),
  [조립 예산](../../assets/items/female_knight_boots/fitted_v5/assembled-budget.json)

착용 자세는 Foot 30도 족저굴곡, ToeBase 반대 방향 30도다. 메시는 공통 bind 자세로 저장돼 있어
정상 실루엣에는 GLB scene extras의 `heel_pose` 적용이 필요하다. 대기 계열 동작에서는 접지면을 수평으로 보정한다.

## 재현

입력은 승인된 한쪽 원본 [boot_right.glb](../../assets/items/female_knight_boots/sole_v3/boot_right.glb)
([편집본](../../assets/items/female_knight_boots/sole_v3/boot_right.blend),
[편집 기록](../../assets/items/female_knight_boots/sole_v3/edit.json))이다.
`fit-female-knight-boots.py`가 [fitted_v4](../../assets/items/female_knight_boots/fitted_v4/boots_female_knight.glb)를,
`shape-female-knight-boots.py`가 v4에서 `fitted_v5`를 만든다. Blender 검수는 동작 검사가 만든 `heel-animation-offsets.json`을 읽으므로 그 뒤에 실행한다.

```bash
.venv/bin/python tools/fit-female-knight-boots.py
.venv/bin/python tools/shape-female-knight-boots.py
node tools/validate-female-knight-boots.mjs
blender -b --python-exit-code 1 --python tools/blender-scripts/review_female_knight_boots.py
```

## 출처·라이선스

- 원화: OpenAI Codex ImageGen, **ChatGPT Pro 20x**, 2026-10-13. OpenAI 출력물 이용 조건 적용.
  [원화 시트](../../assets/items/female_knight_boots/concept_v1/sheet.png),
  [프롬프트](../../assets/items/female_knight_boots/concept_v1/prompt.txt),
  [출처·해시](../../assets/items/female_knight_boots/concept_v1/sources.json).
  Tripo 입력은 1536×1024 시트를 FFmpeg로 512×1024씩 나눈 정면·측면·후면이다.
- 원화 참고: [사용자 이미지](../../assets/items/female_knight_boots/concept_v1/user-reference.png). 원저작자·라이선스 미확인.
- 메시: Tripo API 유료 크레딧, 2026-10-13. 모델 `P2-20260801`, 텍스처 `v3.5-20260815`, detailed PBR,
  한쪽 목표 2,000삼각형(실제 2,106). 작업 ID `20653499-69ca-4be6-bfa0-76ac6ad77323`, **120크레딧**.
  [Tripo 이용 조건](https://developers.tripo3d.ai/en/terms).
  [요청 명세](../../assets/items/female_knight_boots/tripo_v1/build.json),
  [작업·비용 기록](../../assets/items/female_knight_boots/tripo_v1/generation.json),
  [원본 GLB](../../assets/items/female_knight_boots/tripo_v1/source/model_url.glb),
  [PBR 추출 기록](../../assets/items/female_knight_boots/tripo_v1/texture-extraction.json).
- 형상 수정 참고: `assets/items/female_knight_boots/references/`의 사용자 제공 이미지(밑창·측면 윤곽·굽·재질 지시 등).
  원저작자·라이선스 미확인이며 형상 참고로만 사용했다.
- 굽·밑창·피팅·리깅·재질 수정은 로컬 작업이며 추가 생성 비용은 없다.

## 제한

- `body-occlusion.json`의 `cuff_heights`는 미터 전환 전 제작 단위 값이다.
- 걷기에서 발목 판금 사이가 벌어지고, 깊은 무릎 굽힘에서 검은 관절 틈과 선형 스키닝 압축이 남는다.
- 전용 하이힐 보행, 다른 복장 혼합 착용, 출시 예산 정리는 미완료다.
