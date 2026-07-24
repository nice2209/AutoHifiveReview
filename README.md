# HIFIVE 실습일지 자동 작성 시스템

하이파이브(hifive.go.kr) 현장실습 LMS에서 실습일지를 자동으로 작성하는 시스템입니다.

## 기능

- 자동 로그인 (JSONP 방식)
- 랜덤 문장 생성 (매번 다른 일지)
- 주차별 자동 저장
- GitHub Actions로 매일 자동 실행
- 크로스 플랫폼 (Mac/Windows/Linux)

## 설정 방법

### 1. GitHub Secrets 설정

GitHub 저장소 → Settings → Secrets and variables → Actions → New repository secret

| Secret 이름 | 값 |
|-------------|-----|
| `HIFIVE_USER_ID` | 하이파이브 아이디 |
| `HIFIVE_PASSWORD` | 하이파이브 비밀번호 |

### 2. 로컬 실행 (선택)

```bash
# 인증 정보 파일 생성
echo '{"user_id":"아이디","password":"비밀번호","saved_at":"2026-07-24"}' > credentials.json

# 실행
python auto_diary.py

# 테스트 (저장하지 않고 출력만)
python auto_diary.py --dry-run
```

## Web UI 관리 도구 (React)

실습 일지를 시각적으로 모니터링하고, 수동 작성/AI 자동 작성을 결합하여 제어할 수 있는 아름다운 React 기반 Web UI 대시보드입니다.

### 기능
- **실습 현황 대시보드**: 실습 기관명, 실습 기간, 총 진행 주차 대비 현재 작성 완료된 주차 정보와 개인정보 제공 동의 상태를 직관적으로 시각화합니다.
- **실습일지 관리 & 수동 작성**: 주차별 일지 목록을 한눈에 조회 및 삭제할 수 있으며, 일자별 내용 수정 및 AI 랜덤 일지 생성 버튼을 활용해 손쉽게 일지를 보강하여 직접 HIFIVE 서버로 즉각 전송할 수 있습니다.
- **랜덤 단어 사전 커스터마이징**: 형용사, 명사(실습 업무), 문장 패턴, 실습 부서 목록을 대시보드 내에서 손쉽게 추가하고 삭제할 수 있어 생성되는 실습일지 문맥을 본인에게 완벽히 맞춤화할 수 있습니다.
- **자동화 제어 및 로그 조회**: 대시보드 내에서 즉각적으로 스크립트 실행(테스트 또는 실제 제출)이 가능하며, 실시간 실행 로그를 확인할 수 있습니다.

### 실행 방법

1. **API 서버 실행 (React 빌드 결과물 내장)**:
   ```bash
   python api_server.py
   ```
2. 웹 브라우저에서 **[http://localhost:5000](http://localhost:5000)**에 접속하여 대시보드를 사용합니다.

*참고: 개발 모드로 실행 시, `web-ui` 폴더에서 `npm run dev`를 실행하고 `http://localhost:5173`으로 접속할 수 있습니다.*

## 파일 구조

```
AutoHifiveReview/
├── auto_diary.py          # 메인 자동화 스크립트
├── sentence_generator.py  # 랜덤 문장 생성기
├── api_server.py          # React Web UI용 로컬 API 서버
├── config.json            # API 엔드포인트 설정
├── credentials.json       # 로그인 정보 (Git 제외)
├── requirements.txt       # Python 의존성
├── .github/
│   └── workflows/
│       └── diary.yml      # GitHub Actions 워크플로우
├── web-ui/                # React Web UI 프로젝트 폴더
│   ├── src/               # React 컴포넌트 및 스타일 소스
│   ├── dist/              # 빌드된 정적 HTML/JS 리소스
│   └── vite.config.js
└── README.md
```

## 스케줄

- **매일 오후 6시 (KST)** 자동 실행
- 주말 자동 스킵
- 이미 작성된 주차는 자동 스킵
- 수동 실행: GitHub → Actions → HIFIVE 자동 실습일지 → Run workflow

## 동작 원리

1. HIFIVE 로그인 (Base64 인코딩된 비밀번호)
2. 실습 정보 조회 (기업, 기간, 주차)
3. 미작성 주차 확인
4. 랜덤 문장으로 일일 일지 생성
5. API로 저장 (POST `/mobile/saveInvolvedReporting.do`)
