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
from functools import lru_cache
from datetime import datetime, timedelta
from pathlib import Path

from holidays import country_holidays
from holidays.constants import PUBLIC

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

    result_code = result.get("RESULT_CODE")
    result_message = result.get("RESULT_MESSAGE", "")

    if result_code == "Y":
        mem_seq = result["RESULT_MESSAGE"].split(",")[1]
        logger.info(f"로그인 성공! (mem_seq={mem_seq})")
        return True

    # HIFIVE 공식 로그인 화면도 PW_CHANGE 응답을 받은 뒤 인증이 필요한
    # 비밀번호 변경 화면으로 이동한다. 즉 세션은 이미 인증된 상태이므로
    # 자동 작성은 계속 진행하되 사용자에게 변경 필요성을 경고한다.
    if result_code == "PW_CHANGE":
        logger.warning(f"비밀번호 변경 안내: {result_message} (인증 세션으로 계속 진행)")
        return True

    logger.error(f"로그인 실패: {result_message}")
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


@lru_cache(maxsize=None)
def get_korean_public_holidays(year: int):
    """해당 연도의 대한민국 법정·대체·임시 공휴일 달력을 반환한다."""
    return country_holidays(
        "KR",
        years=year,
        observed=True,
        language="ko",
        categories=PUBLIC,
    )


def get_public_holiday_name(target: datetime) -> str | None:
    """target이 대한민국 공휴일이면 명칭을, 아니면 None을 반환한다."""
    target_date = target.date()
    return get_korean_public_holidays(target_date.year).get(target_date)


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
        if current.weekday() < 5 and get_public_holiday_name(current) is None:
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
    overwrite: bool = False,
) -> bool:
    """
    실습일지를 저장한다.

    overwrite=True면 서버에 이미 저장된 일별 내용도 entries 값으로 덮어쓴다.

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
            if entry and entry.get("force_clear"):
                planned[idx] = ("", "N")
            elif overwrite and entry and entry["work_flag"] == "Y" and entry["content"]:
                planned[idx] = (entry["content"], "Y")
            elif s["REPORT_DESC"]:
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

    # 주말·공휴일이면 스킵
    if target_date.weekday() >= 5:
        logger.info("주말이므로 실습일지 작성 스킵")
        return True
    if holiday_name := get_public_holiday_name(target_date):
        logger.info(f"공휴일({holiday_name})이므로 실습일지 작성 스킵")
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

    logger.info(f"현재 대상 주차: {week_seq}주차")

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

    # 현재 주차에 한정하지 않고 대상 날짜까지 비어 있는 모든 평일 주차를
    # 복구한다. 예약 실행이 며칠 실패하거나 주차 경계를 넘겨도 다음 실행이
    # 누락분을 스스로 채운다.
    pending_weeks = set()
    for slot in slots:
        if slot["WEEK_GUBUN"] != GUBUN_DAILY or slot["START_DATE"] > target_str:
            continue
        slot_date = datetime.strptime(slot["START_DATE"], "%Y%m%d")
        if slot["DY"] in ("토", "일"):
            continue
        holiday_name = get_public_holiday_name(slot_date)
        if not holiday_name and not slot["REPORT_DESC"]:
            pending_weeks.add(slot["WEEK_SEQ"])
    pending_weeks = sorted(pending_weeks, key=int)

    if not pending_weeks:
        logger.info("작성할 새로운 항목이 없습니다. (이미 작성 완료)")
        return True

    logger.info(f"누락 복구 대상 주차: {', '.join(pending_weeks)}주차")
    all_ok = True

    for pending_week in pending_weeks:
        week_slots = [s for s in slots if s["WEEK_SEQ"] == pending_week]
        entries = []
        to_write = []

        for s in week_slots:
            if s["WEEK_GUBUN"] != GUBUN_DAILY:
                continue
            day_name = s["DY"]
            slot_date = datetime.strptime(s["START_DATE"], "%Y%m%d")
            holiday_name = (
                get_public_holiday_name(slot_date)
                if s["START_DATE"] <= target_str
                else None
            )

            if holiday_name:
                if s["REPORT_DESC"]:
                    entry = {
                        "date": slot_date, "day_name": day_name,
                        "content": s["REPORT_DESC"], "work_flag": s["WORK_FLAG"] or "Y",
                        "start_time": start_time, "end_time": end_time,
                        "department": department,
                    }
                else:
                    entry = {
                        "date": slot_date, "day_name": day_name,
                        "content": "", "work_flag": "N",
                        "start_time": "", "end_time": "", "department": "",
                    }
            elif s["REPORT_DESC"]:
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

        logger.info(f"{pending_week}주차 작성 대상: {len(to_write)}개 항목")
        for entry in to_write:
            logger.info(
                f"  {entry['date'].strftime('%m-%d')} ({entry['day_name']}): "
                f"{entry['content']}"
            )
        if dry_run:
            logger.info(f"[DRY RUN] {pending_week}주차를 실제로 저장하지 않습니다.")
            continue

        if save_diary_entry(session, trainee_seq, pending_week, entries):
            logger.info(f"{pending_week}주차 실습일지 자동 작성 완료!")
        else:
            logger.error(f"{pending_week}주차 실습일지 저장 실패")
            all_ok = False

    return all_ok


def clear_holiday_entries(until: datetime = None, dry_run: bool = False) -> bool:
    """명시적으로 요청한 경우에만 과거 공휴일의 기존 일지를 비운다."""
    if until is None:
        until = datetime.now()

    logger.info("=" * 60)
    logger.info("공휴일 기존 일지 정리 시작")
    logger.info(f"대상 범위: 실습 시작일 ~ {until.strftime('%Y-%m-%d')}")
    logger.info("=" * 60)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    })

    creds = load_credentials()
    if not login(session, creds["user_id"], creds["password"]):
        return False

    trainee_info = get_trainee_info(session)
    if not trainee_info:
        return False

    trainee_seq = trainee_info["TRAINEE_SEQ"]
    slots = get_existing_entries(session, trainee_seq)
    until_str = until.strftime("%Y%m%d")
    target_weeks = sorted(
        {
            slot["WEEK_SEQ"]
            for slot in slots
            if slot["WEEK_GUBUN"] == GUBUN_DAILY
            and slot["START_DATE"] <= until_str
            and slot["REPORT_DESC"]
            and get_public_holiday_name(datetime.strptime(slot["START_DATE"], "%Y%m%d"))
        },
        key=int,
    )
    if not target_weeks:
        logger.info("정리할 공휴일 일지가 없습니다.")
        return True

    all_ok = True
    for week_seq in target_weeks:
        entries = []
        cleared = []
        for slot in (s for s in slots if s["WEEK_SEQ"] == week_seq and s["WEEK_GUBUN"] == GUBUN_DAILY):
            slot_date = datetime.strptime(slot["START_DATE"], "%Y%m%d")
            holiday_name = (
                get_public_holiday_name(slot_date)
                if slot["START_DATE"] <= until_str
                else None
            )
            if holiday_name and slot["REPORT_DESC"]:
                entries.append({
                    "date": slot_date, "day_name": slot["DY"],
                    "content": "", "work_flag": "N",
                    "start_time": "", "end_time": "", "department": "",
                    "force_clear": True,
                })
                cleared.append((slot_date, holiday_name))
            else:
                entries.append({
                    "date": slot_date, "day_name": slot["DY"],
                    "content": slot["REPORT_DESC"],
                    "work_flag": slot["WORK_FLAG"] or ("Y" if slot["REPORT_DESC"] else "N"),
                    "start_time": "", "end_time": "", "department": "",
                })

        for slot_date, holiday_name in cleared:
            logger.info(f"  {slot_date.strftime('%m-%d')}: 공휴일({holiday_name}) 기존 일지 삭제")

        if dry_run:
            logger.info(f"[DRY RUN] {week_seq}주차 {len(cleared)}개 항목 - 저장하지 않습니다.")
            continue

        if save_diary_entry(session, trainee_seq, week_seq, entries):
            logger.info(f"{week_seq}주차 공휴일 정리 완료 ({len(cleared)}개 항목)")
        else:
            logger.error(f"{week_seq}주차 공휴일 정리 실패")
            all_ok = False

    return all_ok


def rewrite_entries(until: datetime = None, dry_run: bool = False) -> bool:
    """
    이미 작성된 과거 일지를 최신 형식으로 다시 작성한다.

    실습 시작일 기준 첫날/둘째날은 의무교육 본문으로, 나머지 평일은
    업무 중심 3~4문장 본문으로 교체한다.
    until(기본 오늘) 이후 날짜와 주말은 건드리지 않는다.
    """
    if until is None:
        until = datetime.now()

    logger.info("=" * 60)
    logger.info("기존 실습일지 보강 시작")
    logger.info(f"대상 범위: 실습 시작일 ~ {until.strftime('%Y-%m-%d')}")
    logger.info("=" * 60)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    })

    creds = load_credentials()
    if not login(session, creds["user_id"], creds["password"]):
        return False

    trainee_info = get_trainee_info(session)
    if not trainee_info:
        return False

    trainee_seq = trainee_info["TRAINEE_SEQ"]
    start_date_str = trainee_info["TRAINEE_START_DATE"]
    slots = get_existing_entries(session, trainee_seq)

    # 근무시간/부서는 기존 주간 요약을 따른다 (없으면 기본값)
    summary = next(
        (s["REPORT_DESC"] for s in slots
         if s["WEEK_GUBUN"] == GUBUN_SUMMARY and s["REPORT_DESC"]), ""
    )
    parts = summary.split("§") if summary else []
    start_time = parts[0] if len(parts) > 0 else "8"
    end_time = parts[1] if len(parts) > 1 else "17"
    department = parts[3] if len(parts) > 3 else "개발"

    words = load_words()
    until_str = until.strftime("%Y%m%d")

    # 내용이 있는 일별 슬롯을 가진 주차만 보강 대상으로 삼는다
    target_weeks = sorted(
        {s["WEEK_SEQ"] for s in slots
         if s["WEEK_GUBUN"] == GUBUN_DAILY and s["REPORT_DESC"]
         and s["START_DATE"] <= until_str},
        key=int,
    )
    if not target_weeks:
        logger.info("보강할 기존 일지가 없습니다.")
        return True

    logger.info(f"보강 대상 주차: {', '.join(target_weeks)}주차")

    all_ok = True
    for week_seq in target_weeks:
        week_slots = [s for s in slots if s["WEEK_SEQ"] == week_seq]
        entries = []
        rewritten = 0

        for s in week_slots:
            if s["WEEK_GUBUN"] != GUBUN_DAILY:
                continue
            day_name = s["DY"]
            slot_date = datetime.strptime(s["START_DATE"], "%Y%m%d")

            if day_name in ("토", "일") or s["START_DATE"] > until_str:
                entries.append({
                    "date": slot_date, "day_name": day_name,
                    "content": "", "work_flag": "N",
                    "start_time": "", "end_time": "", "department": "",
                })
                continue

            if holiday_name := get_public_holiday_name(slot_date):
                logger.info(
                    f"  [{s['START_DATE']} {day_name}] 공휴일({holiday_name}) - 기존 값 보존"
                )
                entries.append({
                    "date": slot_date, "day_name": day_name,
                    "content": s["REPORT_DESC"],
                    "work_flag": s["WORK_FLAG"] or ("Y" if s["REPORT_DESC"] else "N"),
                    "start_time": start_time, "end_time": end_time,
                    "department": department,
                })
                continue

            w_idx = weekday_index(start_date_str, slot_date)
            if w_idx == 1:
                content = generate_orientation_content(0)
            elif w_idx == 2:
                content = generate_orientation_content(1)
            else:
                content = generate_daily_content(words)

            logger.info(f"  [{s['START_DATE']} {day_name}] 기존: {s['REPORT_DESC'] or '(비어 있음)'}")
            logger.info(f"  [{s['START_DATE']} {day_name}] 신규: {content}")

            entries.append({
                "date": slot_date, "day_name": day_name,
                "content": content, "work_flag": "Y",
                "start_time": start_time, "end_time": end_time,
                "department": department,
            })
            rewritten += 1

        if not rewritten:
            continue

        if dry_run:
            logger.info(f"[DRY RUN] {week_seq}주차 {rewritten}개 항목 - 저장하지 않습니다.")
            continue

        if save_diary_entry(session, trainee_seq, week_seq, entries, overwrite=True):
            logger.info(f"{week_seq}주차 보강 완료 ({rewritten}개 항목)")
        else:
            logger.error(f"{week_seq}주차 보강 실패")
            all_ok = False

    return all_ok


# ==================== CLI ====================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="HIFIVE 실습일지 자동 작성")
    parser.add_argument("--date", type=str, help="작성할 날짜 (YYYY-MM-DD)", default=None)
    parser.add_argument("--rewrite", action="store_true",
                        help="이미 작성된 과거 일지를 최신 형식으로 다시 작성")
    parser.add_argument("--clear-holidays", action="store_true",
                        help="기존 공휴일 일지를 명시적으로 비우기")
    parser.add_argument("--dry-run", action="store_true", help="저장하지 않고 출력만")
    parser.add_argument("--week", type=int, help="작성할 주차 번호", default=None)

    args = parser.parse_args()

    if args.date:
        target_date = datetime.strptime(args.date, "%Y-%m-%d")
    else:
        target_date = datetime.now()

    # 저장 실패 시 종료 코드 1 — GitHub Actions에서 실패로 표시되어야 한다
    if args.clear_holidays:
        ok = clear_holiday_entries(until=target_date, dry_run=args.dry_run)
    elif args.rewrite:
        ok = rewrite_entries(until=target_date, dry_run=args.dry_run)
    else:
        ok = run(target_date=target_date, dry_run=args.dry_run)
    sys.exit(0 if ok else 1)
