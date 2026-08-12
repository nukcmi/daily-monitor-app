# 전략투자 모니터링 Mini App (정적 버전)

Telegram Mini App으로 여는 카드형 대시보드. 지금은 `app.js` 안의
샘플 데이터를 직접 수정하는 정적 버전입니다. DB/API 연동은 다음 단계입니다.

## 구성
- `index.html` — 화면 골격
- `style.css` — 라이트 테마 스타일 (Bloomberg/투자관리 대시보드 톤)
- `app.js` — 종목 데이터 + 렌더링 로직 (지금은 여기 데이터를 손으로 갱신)

## 종목 데이터 수정하는 법

`app.js` 맨 위 `const data = [...]` 배열에서 종목별 객체 하나를 고치면 됩니다.

```js
{
  id: 'bio',              // 내부 식별자, 바꾸지 말 것
  name: '차바이오텍',      // 카드에 표시될 이름
  ticker: '085660',       // 코드/구분 표기
  g: 'B',                 // 중요도: A(긴급) / B(주시) / C(참고)
  event: '헤드라인 한 줄',
  tags: ['태그1', '태그2', '태그3'],
  thesis: '투자논리 한 문장',
  kpis: [['KPI명','값'], ...],   // 2열 그리드로 표시됨
  events: ['최근 이벤트 1', '최근 이벤트 2'],
  watch: ['관전 포인트 1', '관전 포인트 2', '관전 포인트 3'],
}
```

**루멘(LMND)은 실명을 가립니다.** `name`은 항상 "루멘", `ticker`는 "(미국)"으로
유지하고, 그 안의 KPI·watch는 반드시 보험 지표(IFP, Loss Ratio, EBITDA)만
넣습니다. 통신·인프라 관련 문구가 섞이면 안 됩니다 — 실제 다른 상장사와
혼동되는 치명적 오류입니다.

## 배포: GitHub Pages 사용 (별도 호스팅 불필요)

이미 쓰고 계신 저장소(daily-BD)에 그대로 올리면 됩니다.

1. 저장소에 `miniapp` 폴더를 만들어 이 4개 파일(`index.html`, `style.css`,
   `app.js`, `README.md`)을 업로드
2. 저장소 **Settings → Pages**
3. **Source**를 `Deploy from a branch`로, **Branch**를 `main` / `/miniapp`
   (또는 `/(root)`이면 `main`만) 선택 후 Save
4. 몇 분 뒤 `https://<사용자명>.github.io/daily-BD/miniapp/` 형태의
   주소가 생성됨 — 이게 Mini App URL

## Telegram Bot에 등록하는 법

1. Telegram에서 **@BotFather** 대화 시작
2. `/mybots` → 쓰고 계신 봇 선택
3. **Bot Settings → Menu Button → Configure Menu Button**
4. 위에서 만든 GitHub Pages 주소 입력, 버튼 이름(예: "모니터링 열기") 지정
5. 봇 대화창 좌측 하단에 메뉴 버튼이 생기고, 누르면 Mini App이 열림

## 다음 단계 (지금 안 함)
- `app.js`의 하드코딩 데이터 → 기존 `daily-BD` 파이프라인이 매일 만드는
  결과를 JSON으로 저장하고 이 앱이 그 JSON을 fetch하도록 연결
- 그다음 DB(SQLite/Supabase) + API로 확장
