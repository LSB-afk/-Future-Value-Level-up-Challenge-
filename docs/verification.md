# Verification Log

확인일: 2026-06-11

## 완료한 확인

- `python3 scripts/build_real_dataset.py` 실행 성공: `data/areas.actual.json` 9개 생활권 생성
- `python3 -m json.tool data/areas.actual.json` 통과
- `node --check app/app.js` 통과
- `python3 -m py_compile api/movevalue_api.py scripts/build_real_dataset.py scripts/build_application_docx.py` 통과
- API 서버 실행: `python3 api/movevalue_api.py --port 5173 --quiet`
- `GET /api/health` 응답 확인: `ok=true`, 생활권 9개, 2025 서울시 전월세 출처 메타 포함
- `GET /api/recommendations` 응답 확인: 예산·목적지·가구 유형·가중치 기반 랭킹 반환
- 루트 웹 페이지 `HEAD /`, `GET /` 응답 확인: `200 OK`
- 인앱 브라우저 검증: 기본 로딩 시 생활권 9개, 지도 마커 9개, 추천 카드 정상 표시
- 인앱 브라우저 상호작용 검증: 목적지를 `판교`로 변경하면 추천 카드와 상세 근거가 재계산됨
- 브라우저 콘솔 오류: 없음
- `deliverables/MoveValue_참가신청서_기획서_초안.docx` 최신 문구로 재생성
- DOCX 렌더링 성공: `qa/docx-render/page-1.png` ~ `page-4.png`
- 렌더 이미지 육안 확인: 큰 텍스트 겹침, 표 잘림, 빈 페이지, 심각한 페이지 넘김 문제 없음

## 확인된 제한

- 현재 주거비는 서울시 2025 전월세 파일의 15~85㎡ 거래 중앙값 기반이다.
- 통근시간은 주요 목적지별 MVP 검증용 테이블이며, 배포 단계에서는 대중교통 경로 API 또는 GTFS 기반 라우팅으로 교체해야 한다.
- 생활 SOC, 안전, 환경 점수 일부는 MVP 프록시다. 추후 생활시설·안전·대기·녹지 공공데이터 어댑터를 추가해야 한다.
- 전화번호, 서명, 개인정보 수집·이용 동의 체크는 신청자가 제출 전 직접 기재해야 한다.
