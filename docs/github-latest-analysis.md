# GitHub 최신 커밋 분석 요약

확인일: 2026-06-26
기준 브랜치: `main`
기준 커밋: `212f41c Refine apartment matching prototype`

## 최근 커밋 로그

| 커밋 | 목적 | 주요 변경 |
| --- | --- | --- |
| `212f41c` | 아파트 매칭 프로토타입을 지도 중심 의사결정 화면으로 정리 | 아파트 추천 API, 지도 레이어, 상세 패널, 데이터 스냅샷 확장 |
| `8e159c3` | 생활권 매칭 UI 정리 | 입력 패널, 추천 카드, 반응형 스타일 보강 |
| `9d5c221` | 지도 UI 리팩터링 | 지도 중심 레이아웃과 사이드바 구조 정리 |
| `57fedf5` | live 데이터 신뢰도와 부동산 의사결정 강화 | 실거래가 어댑터, 위험 신호, Agent 근거 그룹 추가 |
| `c9597c1` | 아키텍처 문서화 | `architecture/` 문서와 Mermaid 다이어그램 추가 |

최신 커밋 `212f41c`의 변경 규모는 9개 파일, 3,086줄 추가, 680줄 삭제다. 핵심 변경 파일은 `app/app.js`, `app/styles.css`, `api/movevalue_api.py`, `data/apartments.seoul.snapshot.json`이다.

## 현재 서비스 구현 현황 요약표

| 영역 | 현재 구현 | 주요 파일 | 상태 |
| --- | --- | --- | --- |
| 웹 UI | 단일 지도 워크스페이스, 왼쪽 조건 입력/추천, 가운데 상세 패널, 오른쪽 Leaflet 지도 | `app/index.html`, `app/app.js`, `app/styles.css` | 구현 완료 |
| 사용자 조건 입력 | 월 주거 예산, 회사/목적지 주소, 가구 유형, 통근/주거비/SOC/안전 가중치 | `app/index.html`, `app/app.js` | 구현 완료 |
| 아파트 매칭 | 후보 아파트 단지 단위로 통근, 주거비, 생활 SOC, 안전 점수 산정 | `api/movevalue_api.py` | 구현 완료 |
| 지도 레이어 | Leaflet/OSM 지도, 단지 가격 라벨, 클러스터, 선택 단지 SOC 반경 | `app/app.js`, `api/apartment_adapters.py` | 구현 완료 |
| 부동산 상세 대시보드 | 기본정보, 가격정보, 거래추이, 전세 위험 신호, 데이터 연계 상태 | `api/property_model.py`, `api/property_adapters.py`, `app/app.js` | 구현 완료 |
| 계약 전 체크리스트 | 등기부, 보증보험, 체납/신탁, 건축물대장, 전입/확정일자 확인 항목 | `api/property_model.py`, `app/app.js` | 구현 완료 |
| AI Agent | 단지 질문에 가격, 통근, 위험, 생활권, 확인 서류 근거로 응답 | `api/property_model.py`, `api/property_adapters.py`, `app/app.js` | 구현 완료 |
| 후보 비교 | 즐겨찾기 단지의 가격, 전세가율, 위험도, 생활 SOC 비교 | `app/app.js` | 구현 완료 |
| 통근 루트 | 주소 기반 Kakao 지오코딩, ODsay/TMAP 대중교통, 거리 폴백 | `api/route_adapters.py` | 키 기반 live 구조 구현, 키 없으면 폴백 |
| 실거래가 live 보정 | 국토교통부 아파트 매매/전월세 API를 법정동 코드와 계약년월로 조회 | `api/real_estate_price_adapters.py` | 키 기반 live 구조 구현, 키 없으면 추정 |
| 공시가격 live 보정 | 공동주택 공시가격 키 감지와 문서화 | `api/real_estate_price_adapters.py` | PNU/식별자 매핑 확장 예정 |
| 건축물대장/용도지역 | 데이터 출처와 확장 계획 문서화 | `docs/data-sources.md` | 확장 예정 |
| 제출용 문서 | 신청서 초안, 아키텍처 문서, 스크린샷, 다이어그램 | `docs/`, `architecture/`, `deliverables/` | 보강 완료 |

## 주요 컴포넌트와 라우팅 구조

| 계층 | 역할 | 구현 방식 |
| --- | --- | --- |
| 정적 웹앱 | HTML/CSS/Vanilla JS 기반 SPA | `api/movevalue_api.py`가 `/`, `/app.js`, `/styles.css`를 서빙 |
| 화면 상태관리 | 전역 `state` 객체 | 예산, 목적지, 가중치, 추천 결과, 선택 단지, 경로, 즐겨찾기, Agent 응답 저장 |
| 추천 API | `/api/apartment-recommendations` | 사용자 조건을 받아 아파트 단지 점수와 추천 이유 반환 |
| 생활권 API | `/api/areas` | 서울 9개 생활권, 전월세 집계, SOC/안전 근거 반환 |
| 지도 API | `/api/apartments` | 지도 bounds/zoom 기준 단지 또는 클러스터 feature 반환 |
| 상세 API | `/api/property-detail` | 선택 단지의 기본정보, 가격, 추이, 위험, 생활권, AI 요약 반환 |
| Agent API | `/api/property-agent` | 질문 의도에 따라 설명형 답변과 근거 그룹 반환 |
| 경로 API | `/api/commute-route` | 집 주소/회사 주소를 좌표화하고 ODsay/TMAP 또는 폴백 경로 반환 |

## 데이터 처리 로직

| 데이터 | 처리 방식 | 현재 데이터 상태 |
| --- | --- | --- |
| 서울 전월세 | 2025년 서울시 전월세 파일을 생활권 법정동 기준 집계 | 9개 생활권, 매칭 114,319건 |
| 생활 SOC | 병원, 학교, 공원 좌표 스냅샷을 대표역 반경 1.6km로 집계 | 점수와 근거 수치 저장 |
| 안전/환경 | 치안시설, CCTV 집계점, 도시대기 측정망, 공원 접근성 결합 | MVP 스냅샷 기반 |
| 아파트 단지 | 서울 OpenAptInfo sample 5건 + UI 검증용 프로토타입 40건 | 총 45건, `SEOUL_OPEN_API_KEY` 연결 시 live 전환 |
| 가격 상세 | 생활권 전월세 집계로 추정하고, 키가 있으면 MOLIT 매매/전월세 API로 보정 | 키 없으면 추정값과 상태 고지 |

## 구현 완료 기능

- 사용자 조건 기반 아파트 단지 추천
- 지도 기반 후보 탐색과 마커/카드 연동
- 단지 상세 대시보드
- 실거래가/공시가격/전세가율 표시 구조
- 거래 추이 그래프
- 전세 위험 신호 점검과 계약 전 체크리스트
- 후보 단지 비교
- AI Agent 질의응답 화면
- 모바일 반응형 UI
- 키 없는 환경에서도 동작하는 폴백 구조

## 미완성 또는 개선 필요 기능

| 항목 | 현재 상태 | 다음 작업 |
| --- | --- | --- |
| 실제 대중교통 live 검증 | ODsay/TMAP 어댑터 구현, 키 없는 환경에서 폴백 | 키 주입 후 실제 주소별 응답 검증과 캐싱 |
| 전체 서울 단지 표시 | OpenAptInfo live 구조 구현, 저장소 스냅샷은 45건 | `SEOUL_OPEN_API_KEY`로 전체 단지 재생성/검증 |
| 공시가격 정밀화 | 추정값과 키 감지까지만 구현 | 공동주택 공시가격 PNU/호별 식별자 매핑 |
| 건축물대장 | 문서화 단계 | 건축HUB API로 층수, 용도, 구조, 위반건축물 확인 |
| 안전/환경 live화 | 스냅샷 기반 | CCTV, 치안시설, 대기질, 녹지율 자동 갱신 |
| AI Agent 고도화 | 규칙 기반 설명형 응답 | LLM 연결 시 RAG/출처 인용/감사 로그 추가 |
| iOS 앱 | API 재사용 구조만 고려 | SwiftUI 클라이언트 별도 구현 |
