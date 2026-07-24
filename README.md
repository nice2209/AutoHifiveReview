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

## 파일 구조

```
AutoHifiveReview/
├── auto_diary.py          # 메인 자동화 스크립트
├── sentence_generator.py  # 랜덤 문장 생성기
├── config.json            # API 엔드포인트 설정
├── credentials.json       # 로그인 정보 (Git 제외)
├── requirements.txt       # Python 의존성
├── .github/
│   └── workflows/
│       └── diary.yml      # GitHub Actions 워크플로우
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
