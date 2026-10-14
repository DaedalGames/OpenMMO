# 여성 미리보기 로딩 최적화

2026-10-12. 여성 미리보기에서 매번 실행하던 동작 보정을 미리 저장하고, 선택한 헤어만
불러오도록 변경했다. 얼굴 확대 검수용 2K 컬러와 1K 노멀·ORM 파생본을 사용한다.
원본 GLB, 원본 텍스처, Blender 편집본은 보존한다. 속눈썹 알파 이미지는 원본 해상도·데이터를 유지한다.

출처·라이선스·생성 도구 및 요금제는 [여성 베이스](modular-human-female-01.md)와
[여성 헤어](modular-female-knight-hair.md)의 원본 기록을 따른다. 이번 파생 작업은
로컬 sharp/libvips, glTF Transform, Three.js로 처리했으며 외부 API 비용은 없다.
텍스처 축소·압축만 적용하고 폴리곤, UV, 본, 가중치, 원본 동작 accessor 데이터는 유지한다.
몸체 22,175 + 단발 2,436 = 24,611삼각형이다. 숨김 마스크와 두상 영역 배분도 바뀌지 않았다.

## 로딩과 갱신

- 경량 모델: `assets/modular_human_female_01/preview/{base,bob,knight}.glb`.
- 보정된 시선·횃불 동작 7개: 같은 디렉터리의 `animations.json`; 전송 시 gzip 적용.
- 서버 경로: `/__female-preview/{base,bob,knight}.glb`, `/__female-preview/animations.json`.
- `private, no-cache`와 ETag를 사용한다. 새로고침 시 서버에 변경 여부를 확인하고, 같으면 304로 재사용한다.
- `preview/`는 로컬 생성물이며 HF·`assets.lock`에 올리지 않는다(2026-10-14부터). 없으면 첫 요청이나 도구 실행 시 생성한다.
- 원본·변환 스크립트가 바뀌면 해당 파생본을 자동 재생성한다. 첫 생성이나 수정 직후에는 변환 대기가 있다.
  생성 실패 시 요청이 실패하며, 다음 요청에서 재시도한다. 동일 파일의 동시 요청은 하나의 준비 작업을 공유한다.
- 첫 화면은 선택된 헤어 하나만 요청한다. `없음`이면 헤어 요청을 하지 않는다.
  다른 헤어는 선택 시 불러오고 같은 화면에서는 재사용한다. 늦게 끝난 요청은 최신 선택을 덮어쓰지 않는다.
- 모델·텍스처를 불러오는 동안 진행 상태를 표시한다. 헤어 전환 실패 시 이전 선택을 유지하고 재선택할 수 있다.

수동 준비·검증:

```bash
node tools/build-female-preview.mjs
node tools/validate-female-preview.mjs
```

`base`, `bob`, `knight`, `animations` 인자로 하나만 재생성할 수도 있다.
의존성은 기존 `tools/optimize-modular-part.mjs`와 같은 로컬 glTF Transform·sharp 환경을 사용한다.
각 `.manifest.json`에 입력 해시·갱신 판단 정보·출력 해시·텍스처 크기를 저장한다.

## 측정과 검증

로컬 headless Chromium/SwiftShader에서 첫 화면 준비 시간은 기존 약 **4.92초**에서
**0.44–0.57초**로 줄었다. 기존 시간 중 약 **4.37초**가 횃불 발 높이 보정이었다.
첫 다운로드는 약 **56.0MiB → 13.1MiB**, 약 **77% 감소**했다. 새로고침에서는 모델과 동작 요청이
304로 처리됐다. 다시 페이지를 만드는 브라우저 비용까지 포함한 재로딩 준비 시간은 약 1.4초였다.
이 수치는 로컬 측정이며 사용자 앱의 포워딩 경로·장치에서 같은 시간을 보장하지 않는다.

몸체 약 25.4 → 5.9MiB, 단발 약 12.9 → 2.6MiB, 긴 헤어 약 13.4 → 2.9MiB다.
얼굴 확대에서 눈·속눈썹·입술과 가르마를 확인했다. 컬러는 WebP quality 94,
노멀·ORM은 축소 후 무손실 WebP다. 원본 4K보다 세부 텍셀 밀도는 낮아진다.

- [측정·입출력 해시·브라우저 기록](modular-female-preview-performance.json)
- [기존 동작 계산과 저장된 동작 비교](modular-female-preview-validation.json): 7개 보정 동작의 키프레임 오차 0.
- 본 결합 호환, 전체 accessor 값 보존, 헤어 착탈 및 삼각형 표시 확인.
- 대머리 첫 진입, 헤어 전환 재사용, 지연 응답 중 선택 변경, 실패 후 재시도 확인.
- 횃불 대기·걷기·달리기·전투 대기 화면 확인. 타입 검사와 린트 통과.
- 초기 파생본 검증에서 accessor 순서를 그대로 비교한 진단이 과도한 메모리를 사용해 프로세스가 종료됐다.
  저장 과정의 accessor 재정렬을 허용하는 데이터 지문 비교로 바꾸고 파생본 생성을 완료했다.

[경량본 얼굴 검수](../../assets/modular_human_female_01/preview/optimized-face.png).
