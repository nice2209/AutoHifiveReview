# HIFIVE 실습일지 API 문서

## 개요

하이파이브(hifive.go.kr) 현장실습 LMS의 실습일지 자동화를 위한 API 문서입니다.
이 문서를 Gemini에게 주면 Web UI를 만들어줄 수 있습니다.

## 인증

### 로그인

```
GET https://www.hifive.go.kr/main/login.do
```

**파라미터:**
| 필드 | 타입 | 설명 |
|------|------|------|
| user_id | string | 아이디 |
| passwd | string | Base64 인코딩된 비밀번호 |
| callback | string | JSONP 콜백 함수명 (임의 값) |

**응답 (JSONP):**
```json
{
  "RESULT_CODE": "Y",
  "RESULT_MESSAGE": "S,259891"
}
```

- RESULT_CODE가 "Y"이면 로그인 성공
- RESULT_MESSAGE는 "사용자유형,회원번호" 형식

**비밀번호 인코딩:**
```python
import base64
passwd_b64 = base64.b64encode("비밀번호".encode()).decode()
```

### 세션 유지

로그인 후 JSESSIONID 쿠키가 발급됩니다. 이후 모든 요청에 이 쿠키가 포함됩니다.

---

## 실습 정보 조회

### 실습생 목록

```
POST https://www.hifive.go.kr/mobile/selectTraineeList.do
```

**응답:**
```json
{
  "RESULT_CODE": "Y",
  "DATA_LIST": {
    "TOTAL_COUNT": "1",
    "DATA_LIST": [
      {
        "TRAINEE_SEQ": "325204",
        "EMPLOY_NM": "주식회사 에이치앤티",
        "TRAINEE_START_DATE": "20260720",
        "TRAINEE_END_DATE": "20261016",
        "TRAINEE_MAJOR_NM": "[20] 정보통신",
        "LAST_WRITE_REPORT_WEEK": "1",
        "YEAR_SEQ": "2026",
        "TRAINEE_SUPPORT_CD": "8205",
        "END_DATA_HAS_YN": "N"
      }
    ]
  }
}
```

---

## 실습일지 API

### 일지 목록 조회

```
POST https://www.hifive.go.kr/mobile/invovedReportingList.do
```

**파라미터:**
| 필드 | 타입 | 설명 |
|------|------|------|
| trainee_seq | string | 실습생 시퀀스 |

**응답:**
```json
{
  "RESULT_CODE": "Y",
  "INFO": {
    "DATA_LIST": [/* 실습 기본 정보 */]
  },
  "DATA_LIST": {
    "TOTAL_COUNT": "128",
    "DATA_LIST": [
      {
        "REPORT_ING_SEQ": "34909415",
        "TRAINEE_SEQ": "325204",
        "WEEK_SEQ": "1",
        "REPORT_WEEK": "1",
        "TERM_CD": "7602",
        "DY": "월",
        "REPORT_DESC": "새로운 것을 배웠다",
        "WORK_FLAG": "Y",
        "START_DATE": "20260720",
        "END_DATE": "20260720",
        "REPORT_START_DATE": "20260720",
        "REPORT_END_DATE": "20260720",
        "USE_YN": "Y"
      }
    ]
  }
}
```

**TERM_CD 설명:**
| 코드 | 의미 |
|------|------|
| 7601 | 주간 요약 |
| 7602 | 일별 기록 (월~금) |
| 7603 | 토요일 |
| 7604 | 일요일 |

### 일지 저장

```
POST https://www.hifive.go.kr/mobile/saveInvolvedReporting.do
Content-Type: application/x-www-form-urlencoded
```

**파라미터:**
| 필드 | 타입 | 설명 |
|------|------|------|
| save_week | string | 주차 번호 (예: "2") |
| trainee_seq | string | 실습생 시퀀스 |
| reportDesc_{week} | string | 주간 요약 (§ 구분자) |
| reportDesc_{week}_{dayIdx} | string | 일별 내용 (§ 구분자) |
| work_flag_{week}_{dayIdx} | string | 실습 여부 ("Y" 또는 "N") |

**reportDesc 포맷:**
```
시작시간§종료시간§내용§부서
```

**예시:**
```
reportDesc_2 = "09:00§18:00§이번 주 실습 요약§개발팀"
reportDesc_2_0 = "09:00§18:00§새로운 것을 배웠다§개발팀"  (월)
reportDesc_2_1 = "09:00§17:00§신기한 것이 좋았다§개발팀"  (화)
work_flag_2_0 = "Y"
work_flag_2_1 = "Y"
work_flag_2_5 = "N"  (토요일)
work_flag_2_6 = "N"  (일요일)
```

**dayIdx 매핑:**
| 인덱스 | 요일 |
|--------|------|
| 0 | 월 |
| 1 | 화 |
| 2 | 수 |
| 3 | 목 |
| 4 | 금 |
| 5 | 토 |
| 6 | 일 |

**응답:**
```json
{
  "result": "y",
  "resultMsg": ""
}
```

### 일지 삭제

```
POST https://www.hifive.go.kr/mobile/deleteInvolvedReporting.do
```

**파라미터:**
| 필드 | 타입 | 설명 |
|------|------|------|
| trainee_seq | string | 실습생 시퀀스 |
| save_week | string | 삭제할 주차 번호 |

**응답:**
```json
{
  "result": "y",
  "resultMsg": ""
}
```

---

## 개인정보 동의

### 동의 상태 조회

```
POST https://www.hifive.go.kr/mobile/selectPersonalInfo.do
```

**응답:**
```json
{
  "DATA_LIST": {
    "DATA_LIST": [
      {
        "PERSONAL_INFO_AGREE_YN1": "Y",
        "PERSONAL_INFO_AGREE_YN2": "Y",
        "PERSONAL_INFO_AGREE_CHK_YEAR": "2026"
      }
    ]
  }
}
```

### 동의 저장

```
POST https://www.hifive.go.kr/mobile/savePersonalInfo.do
```

**파라미터:**
| 필드 | 타입 | 설명 |
|------|------|------|
| personal_info_agree_yn1 | string | 수집·이용 동의 ("Y"/"N") |
| personal_info_agree_yn2 | string | 제3자 제공 동의 ("Y"/"N") |

---

## 기타 엔드포인트

| URL | 설명 |
|-----|------|
| /mobile/bbsList2.do?bbs_id=200 | 공지사항 |
| /mobile/bbsList2.do?bbs_id=201 | 상담신청 |
| /mobile/involvedCompanyStat.do | 기업현황 |
| /sessionCheck.do | 세션 유효성 검사 |
| /main/logout.do?type=mobile_student | 로그아웃 |

---

## 주차 계산 로직

```python
from datetime import datetime

def get_week_number(start_date_str: str, ref_date: datetime = None) -> int:
    start_date = datetime.strptime(start_date_str, "%Y%m%d")
    if ref_date is None:
        ref_date = datetime.now()
    delta = (ref_date - start_date).days
    return max(1, (delta // 7) + 1)
```

---

## Web UI 구현 시 참고사항

1. **프레임워크:** React, Vue, 또는 순수 HTML/JS 모두 가능
2. **인증:** 로그인 후 세션 쿠키가 필요하므로 같은 도메인에서 요청하거나 CORS 설정 필요
3. **크로스 오리진 문제:** 로컬에서 개발 시 프록시 서버 사용 권장
4. **스케줄링:** GitHub Actions 또는 서버 크론으로 매일 실행
5. **에러 처리:** 세션 만료(30분) 시 재로그인 필요

### 추천 기능

- 실습 현황 대시보드 (진행 주차, 미작성 일지)
- 일별/주별 일지 조회
- 수동 작성/수정
- 자동 스케줄 설정
- 로그 조회
