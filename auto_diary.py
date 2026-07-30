"""
HIFIVE 실습일지 자동 작성 시스템
- 자동 로그인
- 실습일지 자동 제출
- 랜덤 문장 생성
- 크로스 플랫폼 (Mac/Windows)
"""

import requests
import ast
import base64
import json
import os
import sys
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path

from sentence_generator import (
    generate_daily_content,
    generate_orientation_content,
    load_words,
)

# ==================== 설정 ====================

BASE_URL = "https://www.hifive.go.kr"
SCRIPT_DIR = Path(__file__).parent
CREDENTIALS_FILE = SCRIPT_DIR / "credentials.json"
LOG_FILE = SCRIPT_DIR / "diary_log.txt"

# 일지 슬롯 구분 코드 (WEEK_GUBUN)
GUBUN_SUMMARY = "7601"  # 주간 요약 (근무시간§담당업무§부서)
GUBUN_DAILY = "7602"    # 일별 일지
GUBUN_REVIEW = "7603"   # 실습소감
GUBUN_ETC = "7604"      # 기타

DAY_NAMES = ["월", "화", "수", "목", "금", "토", "일"]

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


def weekday_index(start_date_str: str, target: datetime) -> int:
    """
    실습 시작일(start_date_str, 형식 "YYYYMMDD") 기준으로 target이
    평일(토·일 제외) 기준 몇 번째 날인지 계산한다. 시작일 자신이 1번째다.
    target이 시작일보다 이전이면 0 이하를 반환한다.
    """
    start_date = datetime.strptime(start_date_str, "%Y%m%d")
    if target.date() < start_date.date():
        return 0

    count = 0
    current = start_date
    while current.date() <= target.date():
        if current.weekday() < 5:
            count += 1
        current += timedelta(days=1)
    return count


def find_week_seq(slots: list, ref_date: datetime) -> str | None:
    """ref_date가 속한 주차 번호를 서버 슬롯 기준으로 찾는다"""
    ref = ref_date.strftime("%Y%m%d")
    for s in slots:
        if s["WEEK_GUBUN"] == GUBUN_SUMMARY and s["START_DATE"] <= ref <= s["END_DATE"]:
            return s["WEEK_SEQ"]
    return None


def parse_server_json(text: str) -> dict:
    """
    HIFIVE 저장 API는 {'result':'y'} 형태의 작은따옴표 응답을 반환한다.
    브라우저는 eval()로 처리하므로 json.loads로는 파싱되지 않는다.
    ast.literal_eval은 리터럴만 해석하고 코드를 실행하지 않으므로 eval과 달리 안전하다.
    """
    return ast.literal_eval(text.strip())


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

    week_seq = str(week_num)
    slots = get_existing_entries(session, trainee_seq)
    if not slots:
        logger.error("일지 슬롯을 조회하지 못했습니다.")
        return False

    week_slots = [s for s in slots if s["WEEK_SEQ"] == week_seq]
    if not week_slots:
        logger.error(f"{week_num}주차 슬롯이 서버에 없습니다.")
        return False

    # 저장할 내용을 요일별로 매핑
    by_day = {e["day_name"]: e for e in entries}

    # 주간 요약(근무시간§담당업무§부서)은 기존 값 우선, 없으면 직전 주차 값을 재사용
    summary_desc = next(
        (s["REPORT_DESC"] for s in week_slots
         if s["WEEK_GUBUN"] == GUBUN_SUMMARY and s["REPORT_DESC"]), ""
    )
    if not summary_desc:
        summary_desc = next(
            (s["REPORT_DESC"] for s in slots
             if s["WEEK_GUBUN"] == GUBUN_SUMMARY and s["REPORT_DESC"]), ""
        )
    if not summary_desc:
        base = next((e for e in entries if e["work_flag"] == "Y"), entries[0])
        summary_desc = (
            f"{base['start_time']}§{base['end_time']}§"
            f"{base['content']}§{base['department']}"
        )

    # 대상 주차 슬롯별로 저장할 (내용, 실습여부) 결정
    planned = {}
    for idx, s in enumerate(week_slots):
        gubun = s["WEEK_GUBUN"]
        if gubun == GUBUN_SUMMARY:
            planned[idx] = (summary_desc, "N")
        elif gubun == GUBUN_DAILY:
            entry = by_day.get(s["DY"])
            if s["REPORT_DESC"]:
                # 이미 작성된 날은 그대로 보존
                planned[idx] = (s["REPORT_DESC"], s["WORK_FLAG"] or "Y")
            elif entry and entry["work_flag"] == "Y" and entry["content"]:
                planned[idx] = (entry["content"], "Y")
            else:
                planned[idx] = ("", "N")
        else:
            # 실습소감/기타는 기존 값 유지
            planned[idx] = (s["REPORT_DESC"], "N")

    for idx, s in enumerate(week_slots):
        desc, flag = planned[idx]
        logger.info(f"  [{s['WEEK_GUBUN']}] {s['DY']} {s['START_DATE']} "
                    f"flag={flag} desc={desc[:40]}")

    # 브라우저는 폼 전체($('#bodyFORM').serializeArray())를 전송한다.
    # 필드명에 인덱스가 붙지 않고 같은 이름이 슬롯 순서대로 반복되므로
    # 전체 주차 슬롯을 동일한 순서로 재구성해야 한다.
    form_data = [
        ("save_week", week_seq),
        ("file_seq", ""),
        ("trainee_support_cd_8205", "N"),
        ("personal_info_agree_yn_chk", ""),
        ("fund_status_chk", "N"),
        ("trainee_seq", str(trainee_seq)),
        ("kind", "1"),
    ]
    week_cursor = 0
    for s in slots:
        form_data.append(("report_week", s["WEEK_SEQ"]))
        form_data.append(("term_cd", s["WEEK_GUBUN"]))
        form_data.append(("report_start_date", s["START_DATE"]))
        form_data.append(("report_end_date", s["END_DATE"]))
        if s["WEEK_SEQ"] == week_seq:
            desc, flag = planned[week_cursor]
            week_cursor += 1
        else:
            # 다른 주차는 서버에 저장된 값을 그대로 되돌려보내 보존한다
            desc, flag = s["REPORT_DESC"], (s["WORK_FLAG"] or "N")
        form_data.append(("reportDesc", desc))
        form_data.append(("work_flag", flag))
        form_data.append(("teacher_name", s.get("TEACHER_NAME", "")))

    # 실습여부 체크박스 (값은 주차 내 슬롯 인덱스)
    for idx, s in enumerate(week_slots):
        if planned[idx][1] == "Y":
            form_data.append((f"work_flag_temp_{week_seq}", str(idx)))

    resp = session.post(
        f"{BASE_URL}/mobile/saveInvolvedReporting.do",
        data=form_data,
        timeout=15,
    )

    try:
        result = parse_server_json(resp.text)
    except (ValueError, SyntaxError) as e:
        logger.error(f"저장 응답 파싱 실패: {e} | 응답 본문: {resp.text[:300]!r}")
        return False

    if result.get("result") == "y":
        logger.info(f"{week_num}주차 실습일지 저장 성공!")
        return True

    logger.error(
        f"서버가 저장을 거부했습니다: result={result.get('result')} "
        f"msg={result.get('resultMsg', '(없음)')}"
    )
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
        return True

    # 세션 생성
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    })

    # 로그인
    creds = load_credentials()
    if not login(session, creds["user_id"], creds["password"]):
        return False

    # 실습 정보 조회
    trainee_info = get_trainee_info(session)
    if not trainee_info:
        return False

    trainee_seq = trainee_info["TRAINEE_SEQ"]

    # 기존 슬롯 조회 후 대상 날짜가 속한 주차를 서버 기준으로 판정
    slots = get_existing_entries(session, trainee_seq)
    week_seq = find_week_seq(slots, target_date)
    if week_seq is None:
        logger.error(f"{target_date.strftime('%Y-%m-%d')}은 실습 기간에 포함되지 않습니다.")
        return False

    logger.info(f"대상 주차: {week_seq}주차")

    week_slots = [s for s in slots if s["WEEK_SEQ"] == week_seq]
    target_str = target_date.strftime("%Y%m%d")
    words = load_words()

    # 근무시간/부서는 기존 주간 요약을 따른다 (없으면 기본값)
    summary = next(
        (s["REPORT_DESC"] for s in slots
         if s["WEEK_GUBUN"] == GUBUN_SUMMARY and s["REPORT_DESC"]), ""
    )
    parts = summary.split("§") if summary else []
    start_time = parts[0] if len(parts) > 0 else "8"
    end_time = parts[1] if len(parts) > 1 else "17"
    department = parts[3] if len(parts) > 3 else "개발"

    # 대상 날짜까지의 평일 중 비어 있는 날만 새로 채운다.
    # HIFIVE는 미래 날짜의 일지 입력란을 readonly로 막으므로 미리 쓰지 않는다.
    entries = []
    to_write = []
    for s in week_slots:
        if s["WEEK_GUBUN"] != GUBUN_DAILY:
            continue
        day_name = s["DY"]
        slot_date = datetime.strptime(s["START_DATE"], "%Y%m%d")

        if s["REPORT_DESC"]:
            entry = {
                "date": slot_date, "day_name": day_name,
                "content": s["REPORT_DESC"], "work_flag": s["WORK_FLAG"] or "Y",
                "start_time": start_time, "end_time": end_time,
                "department": department,
            }
        elif day_name in ("토", "일") or s["START_DATE"] > target_str:
            entry = {
                "date": slot_date, "day_name": day_name,
                "content": "", "work_flag": "N",
                "start_time": "", "end_time": "", "department": "",
            }
        else:
            w_idx = weekday_index(trainee_info["TRAINEE_START_DATE"], slot_date)
            if w_idx == 1:
                content = generate_orientation_content(0)
            elif w_idx == 2:
                content = generate_orientation_content(1)
            else:
                content = generate_daily_content(words)
            entry = {
                "date": slot_date, "day_name": day_name,
                "content": content, "work_flag": "Y",
                "start_time": start_time, "end_time": end_time,
                "department": department,
            }
            to_write.append(entry)
        entries.append(entry)

    if not to_write:
        logger.info("작성할 새로운 항목이 없습니다. (이미 작성 완료)")
        return True

    logger.info(f"작성 대상: {len(to_write)}개 항목")
    for e in to_write:
        logger.info(f"  {e['date'].strftime('%m-%d')} ({e['day_name']}): {e['content']}")

    if dry_run:
        logger.info("[DRY RUN] 실제로 저장하지 않습니다.")
        return True

    # 저장
    success = save_diary_entry(session, trainee_seq, week_seq, entries)

    if success:
        logger.info(f"{week_seq}주차 실습일지 자동 작성 완료!")
    else:
        logger.error(f"{week_seq}주차 실습일지 저장 실패")
    return success


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

    # 저장 실패 시 종료 코드 1 — GitHub Actions에서 실패로 표시되어야 한다
    ok = run(target_date=target_date, dry_run=args.dry_run)
    sys.exit(0 if ok else 1)
