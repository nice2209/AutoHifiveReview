"""
HIFIVE 실습일지 자동 작성 시스템
- 자동 로그인
- 실습일지 자동 제출
- 랜덤 문장 생성
- 크로스 플랫폼 (Mac/Windows)
"""

import requests
import base64
import json
import os
import sys
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path

from sentence_generator import generate_daily_entry, generate_weekly_summary, generate_week_entries

# ==================== 설정 ====================

BASE_URL = "https://www.hifive.go.kr"
SCRIPT_DIR = Path(__file__).parent
CREDENTIALS_FILE = SCRIPT_DIR / "credentials.json"
LOG_FILE = SCRIPT_DIR / "diary_log.txt"

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# ==================== 인증 ====================

def load_credentials() -> dict:
    """credentials.json 또는 환경변수에서 로그인 정보 로드"""
    # 환경변수 우선 (GitHub Actions용)
    env_user = os.environ.get("HIFIVE_USER_ID")
    env_pass = os.environ.get("HIFIVE_PASSWORD")
    if env_user and env_pass:
        logger.info("환경변수에서 인증 정보 로드")
        return {"user_id": env_user, "password": env_pass}

    # 파일에서 로드 (로컬 실행용)
    if not CREDENTIALS_FILE.exists():
        logger.error(f"credentials.json 파일을 찾을 수 없습니다: {CREDENTIALS_FILE}")
        sys.exit(1)

    with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
        creds = json.load(f)

    if not creds.get("user_id") or not creds.get("password"):
        logger.error("credentials.json에 user_id 또는 password가 없습니다.")
        sys.exit(1)

    return creds


def login(session: requests.Session, user_id: str, password: str) -> bool:
    """HIFIVE 로그인 (JSONP 방식)"""
    logger.info(f"로그인 시도: {user_id}")

    # 로그인 페이지 접속 (쿠키 확보)
    resp = session.get(
        f"{BASE_URL}/main/loginPage.do?rootMenuId=08&menuId=0801", timeout=15
    )
    if resp.status_code != 200:
        logger.error(f"로그인 페이지 접속 실패: {resp.status_code}")
        return False

    # 로그인 요청 (Base64 인코딩된 비밀번호)
    passwd_b64 = base64.b64encode(password.encode()).decode()
    resp = session.get(
        f"{BASE_URL}/main/login.do",
        params={"user_id": user_id, "passwd": passwd_b64, "callback": "cb"},
        timeout=15,
    )

    try:
        json_str = resp.text.split("(", 1)[1].rsplit(")", 1)[0]
        result = json.loads(json_str)
    except (IndexError, json.JSONDecodeError):
        logger.error(f"로그인 응답 파싱 실패: {resp.text[:200]}")
        return False

    if result.get("RESULT_CODE") == "Y":
        mem_seq = result["RESULT_MESSAGE"].split(",")[1]
        logger.info(f"로그인 성공! (mem_seq={mem_seq})")
        return True
    else:
        logger.error(f"로그인 실패: {result.get('RESULT_MESSAGE')}")
        return False


# ==================== 실습 정보 ====================

def get_trainee_info(session: requests.Session) -> dict | None:
    """실습생 정보 조회"""
    resp = session.post(f"{BASE_URL}/mobile/selectTraineeList.do", data={}, timeout=15)
    result = resp.json()

    total = int(result.get("DATA_LIST", {}).get("TOTAL_COUNT", 0))
    if total == 0:
        logger.error("등록된 실습 이력이 없습니다.")
        return None

    info = result["DATA_LIST"]["DATA_LIST"][0]
    logger.info(
        f"실습 정보: {info['EMPLOY_NM']} | "
        f"{info['TRAINEE_START_DATE']}~{info['TRAINEE_END_DATE']} | "
        f"마지막 주차: {info['LAST_WRITE_REPORT_WEEK']}주차"
    )
    return info


def get_existing_entries(session: requests.Session, trainee_seq: str) -> list:
    """기존 실습일지 목록 조회"""
    resp = session.post(
        f"{BASE_URL}/mobile/invovedReportingList.do",
        data={"trainee_seq": str(trainee_seq)},
        timeout=15,
    )
    result = resp.json()
    entries = result.get("DATA_LIST", {}).get("DATA_LIST", [])
    logger.info(f"기존 일지 항목 수: {len(entries)}")
    return entries


def get_current_week_number(start_date_str: str, ref_date: datetime = None) -> int:
    """주차 번호 계산 (ref_date 기준)"""
    start_date = datetime.strptime(start_date_str, "%Y%m%d")
    if ref_date is None:
        ref_date = datetime.now()
    delta = (ref_date - start_date).days
    week_num = (delta // 7) + 1
    return max(1, week_num)


# ==================== 실습일지 저장 ====================

def save_diary_entry(
    session: requests.Session,
    trainee_seq: str,
    week_num: int,
    entries: list,
) -> bool:
    """
    실습일지를 저장한다.

    entries: [
        {
            "date": datetime,
            "day_name": str,
            "content": str,
            "work_flag": str (Y/N),
            "start_time": str,
            "end_time": str,
            "department": str,
        }, ...
    ]
    """
    logger.info(f"{week_num}주차 실습일지 저장 시도...")

    # 폼 데이터 구성
    form_data = {
        "save_week": str(week_num),
        "trainee_seq": str(trainee_seq),
    }

    # 주간 요약 (TERM_CD=7601)
    weekly_content = generate_weekly_summary(entries)
    # reportDesc 포맷: 시작시간§종료시간§담당업무§부서
    first_valid = next((e for e in entries if e["work_flag"] == "Y"), entries[0])
    weekly_report_desc = (
        f"{first_valid['start_time']}§{first_valid['end_time']}§"
        f"{weekly_content}§{first_valid['department']}"
    )
    form_data[f"reportDesc_{week_num}"] = weekly_report_desc

    # 일별 항목
    day_names = ["월", "화", "수", "목", "금", "토", "일"]
    for i, entry in enumerate(entries):
        day_name = entry["day_name"]
        day_idx = day_names.index(day_name)

        # 실습여부 플래그
        form_data[f"work_flag_{week_num}_{day_idx}"] = entry["work_flag"]

        # 일별 내용
        if entry["work_flag"] == "Y":
            # 일별 reportDesc: 시작시간§종료시간§내용§부서
            day_report_desc = (
                f"{entry['start_time']}§{entry['end_time']}§"
                f"{entry['content']}§{entry['department']}"
            )
        else:
            day_report_desc = ""

        form_data[f"reportDesc_{week_num}_{day_idx}"] = day_report_desc

    logger.info(f"전송 데이터: {json.dumps(form_data, ensure_ascii=False, indent=2)}")

    # 저장 요청
    resp = session.post(
        f"{BASE_URL}/mobile/saveInvolvedReporting.do",
        data=form_data,
        timeout=15,
    )

    try:
        result = resp.json()
        if result.get("result") == "y":
            logger.info(f"{week_num}주차 실습일지 저장 성공!")
            return True
        else:
            logger.error(f"저장 실패: {result.get('resultMsg', '알 수 없는 오류')}")
            return False
    except Exception as e:
        logger.error(f"저장 응답 처리 실패: {e}")
        return False


# ==================== 메인 실행 ====================

def run(target_date: datetime = None, dry_run: bool = False):
    """
    실습일지 자동 작성 실행

    Args:
        target_date: 작성할 날짜 (None이면 오늘)
        dry_run: True면 실제로 저장하지 않고 출력만
    """
    if target_date is None:
        target_date = datetime.now()

    logger.info("=" * 60)
    logger.info(f"HIFIVE 실습일지 자동 작성 시작")
    logger.info(f"대상 날짜: {target_date.strftime('%Y-%m-%d')} ({['월','화','수','목','금','토','일'][target_date.weekday()]})")
    logger.info("=" * 60)

    # 주말이면 스킵
    if target_date.weekday() >= 5:
        logger.info("주말이므로 실습일지 작성 스킵")
        return

    # 세션 생성
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    })

    # 로그인
    creds = load_credentials()
    if not login(session, creds["user_id"], creds["password"]):
        return

    # 실습 정보 조회
    trainee_info = get_trainee_info(session)
    if not trainee_info:
        return

    trainee_seq = trainee_info["TRAINEE_SEQ"]
    start_date_str = trainee_info["TRAINEE_START_DATE"]
    start_date = datetime.strptime(start_date_str, "%Y%m%d")
    last_week = int(trainee_info["LAST_WRITE_REPORT_WEEK"])

    # 현재 주차 계산
    current_week = get_current_week_number(start_date_str, target_date)
    logger.info(f"현재 주차: {current_week}주차 (마지막 작성: {last_week}주차)")

    # 이미 최신 주차까지 작성했는지 확인
    if current_week <= last_week:
        logger.info(f"{current_week}주차는 이미 작성 완료됨. 스킵.")
        return

    # 기존 일지 확인
    existing = get_existing_entries(session, trainee_seq)

    # 해당 주차의 기존 일지가 있는지 확인
    existing_week_entries = [
        e for e in existing
        if e.get("REPORT_WEEK") == str(current_week) and e.get("REPORT_DESC")
    ]

    if existing_week_entries:
        logger.info(f"{current_week}주차에 이미 {len(existing_week_entries)}개 항목 존재")
        # 이미 작성된 항목 제외하고 미작성분만 채우기

    # 주차별 일일 항목 생성
    entries = generate_week_entries(start_date, current_week)

    # 이미 작성된 항목과 병합
    day_names = ["월", "화", "수", "목", "금", "토", "일"]
    for existing_entry in existing_week_entries:
        day_name = existing_entry.get("DY", "")
        if day_name in day_names:
            day_idx = day_names.index(day_name)
            # 기존 항목이 있으면 해당 날짜는 스킵
            if existing_entry.get("WORK_FLAG") == "Y":
                entries[day_idx] = {
                    "date": entries[day_idx]["date"],
                    "day_name": day_name,
                    "content": "",
                    "work_flag": "N",  # 이미 작성됨
                    "start_time": "",
                    "end_time": "",
                    "department": "",
                }

    # 작성할 항목 확인
    to_write = [e for e in entries if e["work_flag"] == "Y" and e["content"]]
    if not to_write:
        logger.info("작성할 새로운 항목이 없습니다.")
        return

    logger.info(f"작성 대상: {len(to_write)}개 항목")
    for e in to_write:
        logger.info(f"  {e['date'].strftime('%m-%d')} ({e['day_name']}): {e['content']}")

    if dry_run:
        logger.info("[DRY RUN] 실제로 저장하지 않습니다.")
        return

    # 저장
    success = save_diary_entry(session, trainee_seq, current_week, entries)

    if success:
        logger.info(f"{current_week}주차 실습일지 자동 작성 완료!")
    else:
        logger.error(f"{current_week}주차 실습일지 저장 실패")


# ==================== CLI ====================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="HIFIVE 실습일지 자동 작성")
    parser.add_argument("--date", type=str, help="작성할 날짜 (YYYY-MM-DD)", default=None)
    parser.add_argument("--dry-run", action="store_true", help="저장하지 않고 출력만")
    parser.add_argument("--week", type=int, help="작성할 주차 번호", default=None)

    args = parser.parse_args()

    if args.date:
        target_date = datetime.strptime(args.date, "%Y-%m-%d")
    else:
        target_date = datetime.now()

    run(target_date=target_date, dry_run=args.dry_run)
