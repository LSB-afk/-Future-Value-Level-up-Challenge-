# MoveValue - 국토교통 서비스 발굴 경연 작업공간

`MoveValue`는 주거비, 이동시간, 대중교통 접근성, 생활 SOC, 안전·환경 지표를 함께 계산해 국민이 체감할 수 있는 생활권 선택을 돕는 국토교통 데이터 기반 서비스 모델입니다.

## 웹 서비스 구성

웹 화면은 단일 페이지 서비스로, 상단 메뉴(추천 · 지도 · 데이터 근거 · API · 사업모델 · 제출자료)로 이동합니다.

- **추천**: 예산·목적지·가구 유형·우선순위 기반 생활권 랭킹. 카드마다 "왜 추천됐는지" 한 줄 근거를 표시하고, 전체 후보 9개 중 상위 6개를 기본 노출합니다.
- **지도**: Leaflet + OpenStreetMap 타일 실제 지도. 생활권 9개 마커를 점수별 색상·크기로 표시하고, 카드 선택과 양방향 연동됩니다. 지도 로딩 실패 시 분포도 폴백으로 전환됩니다.
- **데이터 근거**: 서울시 2025 전월세 실데이터의 생활권별 매칭 거래 건수, 월세·보증금·전세 중앙값 표와 MVP 프록시 지표의 한계 고지.
- **API**: `/api/health`, `/api/areas`, `/api/recommendations` 설명과 호출 예시, B2B/B2G 확장 방향.
- **사업모델**: B2C/B2B/B2G/데이터 마켓 수익 채널과 서비스 밸류체인.
- **제출자료**: 참가신청서 DOCX 위치와 문서 경로 안내.

## 현재 산출물

- `api/`: 추천 계산과 정적 웹앱 제공을 담당하는 Python API 서버
- `app/`: API를 호출하는 브라우저 실행 프로토타입 (Leaflet 지도 포함)
- `data/areas.actual.json`: 서울시 2025 전월세 스냅샷 기반 생활권 데이터
- `scripts/build_real_dataset.py`: 실제 공공데이터 다운로드·정규화 파이프라인
- `docs/competition-brief.md`: 공모전 공고·양식 확인 요약
- `docs/data-sources.md`: 실제 연계 가능한 공공데이터 근거
- `docs/api-development.md`: API 구조, 실행 방법, 지도 제공자 교체 가이드
- `docs/service-model.md`: 사업모델, 밸류체인, 구현계획
- `docs/product-roadmap.md`: 선정 후 구체화 단계 개발 순서
- `docs/verification.md`: 실행·브라우저·데이터 검증 로그
- `docs/application-draft.md`: 참가신청서 및 기획서 작성 초안
- `deliverables/`: 제출용 문서 산출물 저장 위치

## API 웹 서비스 실행

별도 패키지 설치 없이 Python 표준 라이브러리만 사용합니다.

```bash
python3 api/movevalue_api.py --port 5173
```

그 다음 브라우저에서 `http://127.0.0.1:5173/`를 엽니다.

## 지도

지도는 API 키가 필요 없는 Leaflet + OpenStreetMap 타일을 사용합니다. VWorld·카카오·네이버 지도로 교체하는 방법은 `docs/api-development.md`의 "지도 제공자 교체" 절을 참고하세요. 타일 로딩에 실패하면 좌표 기반 분포도 폴백이 유지됩니다.

## 실제 데이터 갱신

서울시 열린데이터광장 전월세 파일을 내려받아 생활권별 월세·보증금·전세 중앙값을 다시 계산합니다. 원천 ZIP은 `data/raw/`에 저장되며 Git에는 포함하지 않습니다.

```bash
python3 scripts/build_real_dataset.py
```

## 주요 API

- `GET /api/health`: 데이터 로딩 상태 확인
- `GET /api/areas`: 실제 기반 생활권 데이터 전체 조회
- `GET /api/recommendations`: 예산, 목적지, 가구 유형, 가중치 기반 추천 랭킹 조회

## 데이터 기반과 한계

주거비(월세·보증금·전세 중앙값)는 서울시 2025 전월세 실데이터에서 집계한 값입니다. 통근시간·생활 SOC·안전·환경 점수는 MVP 검증용 프록시이며, 선정 후 구체화 단계에서 실제 API로 고도화합니다(`docs/product-roadmap.md` 참고).

## 제출 전 확인 필요

신청서에는 개인정보, 전화번호, 서명, 개인정보 수집·이용 동의가 포함됩니다. 이 항목은 사용자가 직접 확인하고 서명해야 하므로 초안에서는 `제출 전 기재`로 표시했습니다.
