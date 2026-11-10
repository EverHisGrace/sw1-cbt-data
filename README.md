# sw1-cbt-data
「사회복지사 1급 기출」 앱이 읽는 시험일 정보와 개인정보 처리방침 페이지.

- `exam-dates.json` — 앱이 하루 한 번 읽어 D-day에 반영
- `.github/workflows/update-exam-dates.yml` + `update.py` — 매주 월요일 공단 API로 자동 갱신
- 필요한 설정: Settings → Secrets and variables → Actions → **DATA_GO_KR_KEY** (공공데이터포털 인증키, Decoding)
