"""
HIFIVE 실습일지 랜덤 문장 생성기
- 기존 스타일: "~를 배웠다", "~이 좋았다" 등
- words.json에서 단어 리스트 커스터마이징 가능
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

WORDS_FILE = Path(__file__).parent / "words.json"

# ==================== 기본 단어 리스트 ====================

DEFAULT_WORDS = {
    "adjectives": [
        "새로운", "신기한", "흥미로운", "유익한", "보람있는",
        "도전적인", "체계적인", "전문적인", "실용적인", "효과적인",
        "창의적인", "정확한", "빠른", "안정적인", "효율적인",
        "섬세한", "꼼꼼한", "성실한", "적극적인", "진지한",
        "활발한", "자세한", "명확한", "실질적인", "구체적인",
        "핵심적인", "중요한", "필수적인", "기초적인", "심화된",
        "발전된", "향상된", "즐거운", "활기찬", "보이는",
    ],
    "nouns": [
        # 앱 개발 핵심
        "API 개발", "UI/UX 디자인", "데이터베이스 설계", "서버 통신", "캐시 처리",
        "Push 알림", "로그인 기능", "회원가입 화면", "메인 화면", "상세 페이지",
        "검색 기능", "필터링", "정렬 기능", "페이지네이션", "무한 스크롤",
        # 프론트엔드
        "React", "Flutter", "SwiftUI", "Jetpack Compose", "TypeScript",
        "컴포넌트 설계", "상태 관리", "라우팅", "네비게이션", "애니메이션",
        "반응형 UI", "다크 모드", "테마 설정", "다국어 지원", "접근성",
        # 백엔드
        "REST API", "GraphQL", "WebSocket", "JWT 인증", "OAuth",
        "Microservices", "Docker", "CI/CD", "AWS", "Firebase",
        "데이터 동기화", "오프라인 지원", "이미지 업로드", "파일 관리", "캐싱",
        # 개발 도구/프로세스
        "Git", "코드 리뷰", "단위 테스트", "통합 테스트", "배포",
        "디버깅", "프로파일링", "메모리 최적화", "성능 튜닝", "보안 점검",
        "문서화", "일정 관리", "스프린트", "회고", "기획 미팅",
        # 실무
        "에러 처리", "로깅", "모니터링", "사용자 피드백", "A/B 테스트",
        "데이터 분석", "사용자 분석", "전환율 최적화", "버그 수정", "기능 개선",
    ],
    # 웹 개발 중심 추가 명사 (담당업무가 웹 개발이라 앱/임베디드 계열이 튀지 않도록 보강)
    "web_nouns": [
        "Next.js", "Node.js", "Express", "MySQL", "PostgreSQL",
        "REST API 설계", "프론트엔드 배포", "백엔드 배포", "웹 접근성 개선", "SEO 최적화",
        "폼 유효성 검사", "세션 관리", "쿠키 처리", "CORS 설정", "환경변수 관리",
    ],
    # 문장 패턴 ({p}=을/를, {sp}=이/가)
    "patterns": [
        "{adj} 것을 배웠다",
        "{adj} 것이 좋았다",
        "{adj} 경험을 했다",
        "{noun}{sp} 재미있었다",
        "{noun}에 대해 배웠다",
        "{noun}{p} 직접 해보았다",
        "{noun}{sp} 신기했다",
        "{noun}{p} 알게 되었다",
        "오늘은 {noun}{p} 배웠다",
        "{noun}에 대해 이해했다",
        "{adj} 하루였다",
        "{noun}{p} 사용해보았다",
        "{noun}에 대해 알게 되었다",
        "{adj} 것을 알게 되었다",
        "{noun}{sp} 흥미로웠다",
        "{noun}{p} 배우는 시간이었다",
        "오늘도 {adj} 실습이었다",
        "{noun}을 개선해보았다",
        "{noun}에 집중했다",
    ],
    "departments": [
        "개발팀", "프로그래밍팀", "SW개발팀", "하드웨어팀", "임베디드팀",
        "인프라팀", "운영팀", "시험팀", "품질팀", "생산팀",
        "설계팀", "연구개발팀", "기술지원팀",
    ],
}


def load_words() -> dict:
    """words.json에서 단어 리스트 로드 (없으면 기본값 사용)"""
    if WORDS_FILE.exists():
        try:
            with open(WORDS_FILE, "r", encoding="utf-8") as f:
                custom = json.load(f)
            # 기본값과 병합 (커스텀이 우선)
            merged = DEFAULT_WORDS.copy()
            merged.update(custom)
            return merged
        except Exception:
            pass
    return DEFAULT_WORDS


def save_default_words():
    """기본 words.json 파일 생성 (커스터마이징용)"""
    with open(WORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_WORDS, f, ensure_ascii=False, indent=2)
    print(f"words.json 생성됨: {WORDS_FILE}")
    print("단어를 자유롭게 수정한 후 다시 실행하세요.")


def _get_particle(noun: str) -> str:
    """명사 종성에 따라 을/를 반환 (영어 단어는 '을' 사용)"""
    last_char = noun[-1]
    code = ord(last_char) - 0xAC00
    if 0 <= code < 11172:
        return "를" if code % 28 == 0 else "을"
    # 영어/숫자로 끝나면 받침 있다고 간주
    if last_char.isascii():
        return "을"
    return "를"


def _get_subject_particle(noun: str) -> str:
    """명사 종성에 따라 이/가 반환 (영어 단어는 '이' 사용)"""
    last_char = noun[-1]
    code = ord(last_char) - 0xAC00
    if 0 <= code < 11172:
        return "가" if code % 28 == 0 else "이"
    if last_char.isascii():
        return "이"
    return "가"


def generate_sentence(words: dict) -> str:
    """랜덤 문장 생성"""
    pattern = random.choice(words["patterns"])
    noun = random.choice(words["nouns"])
    adj = random.choice(words["adjectives"])

    # 조사 자동 처리
    p = _get_particle(noun)
    sp = _get_subject_particle(noun)

    return pattern.format(
        adj=adj,
        noun=noun,
        p=p,        # 을/를
        sp=sp,      # 이/가
    )


# ==================== 업무 중심 일일 본문 (3~4문장) ====================

# 구현/동작 서술과 어울리지 않는 활동성 명사 (작업 문장에서는 제외한다)
ACTIVITY_NOUNS = {
    "코드 리뷰", "단위 테스트", "통합 테스트", "배포", "디버깅", "프로파일링",
    "메모리 최적화", "성능 튜닝", "보안 점검", "문서화", "일정 관리",
    "스프린트", "회고", "기획 미팅", "모니터링", "사용자 피드백",
    "A/B 테스트", "데이터 분석", "사용자 분석", "전환율 최적화",
    "버그 수정", "기능 개선",
}

# 업무 서술형 문장 패턴 (도입/작업/마무리 3그룹, {p}=을/를, {sp}=이/가)
DAILY_CONTENT_PATTERNS = {
    "intro": [
        "오전에는 {noun} 관련 작업을 진행했다.",
        "오늘은 {noun} 관련 업무로 하루를 시작했다.",
        "출근 후 {noun} 관련 이슈를 먼저 확인했다.",
        "오전 중에 {noun} 작업 계획을 세웠다.",
        "오늘 일정은 {noun} 작업으로 시작되었다.",
        "아침 회의에서 {noun} 관련 업무를 배정받았다.",
    ],
    "work": [
        "{noun} 기능을 직접 구현하며 동작 방식을 익혔다.",
        "사수님의 피드백을 반영해 {noun} 부분을 수정했다.",
        "{noun} 진행 중 발생한 오류를 확인하고 원인을 파악했다.",
        "{noun} 기능을 테스트하며 예외 상황을 점검했다.",
        "{noun} 관련 코드를 리뷰하고 개선점을 반영했다.",
        "{noun} 부분이 예상대로 동작하지 않아 원인을 분석했다.",
    ],
    "closing": [
        "오후에는 {noun} 문서를 정리하고 팀에 공유했다.",
        "내일은 {noun} 작업을 이어서 진행할 예정이다.",
        "퇴근 전 {noun} 관련 작업 내용을 정리했다.",
        "{noun} 작업 결과를 사수님께 보고했다.",
        "오늘 진행한 {noun} 작업을 마무리하고 다음 계획을 세웠다.",
        "{noun} 관련 남은 작업은 내일 이어서 처리하기로 했다.",
    ],
}


def generate_daily_content(words: dict = None) -> str:
    """업무 중심 3~4문장 본문 생성 (도입/작업/마무리 구조, 같은 본문 내 명사 중복 없음)"""
    if words is None:
        words = load_words()

    noun_pool = list(words["nouns"]) + list(words.get("web_nouns", []))
    tech_pool = [n for n in noun_pool if n not in ACTIVITY_NOUNS]
    used_nouns: list = []

    def pick_noun(pool: list) -> str:
        candidates = [n for n in pool if n not in used_nouns] or pool
        noun = random.choice(candidates)
        used_nouns.append(noun)
        return noun

    def build(pattern: str, pool: list = None) -> str:
        noun = pick_noun(pool if pool is not None else noun_pool)
        return pattern.format(
            noun=noun,
            p=_get_particle(noun),
            sp=_get_subject_particle(noun),
        )

    # 작업 문장은 1~2개를 서로 다른 패턴으로 뽑아 같은 문장이 반복되지 않게 한다
    work_patterns = random.sample(DAILY_CONTENT_PATTERNS["work"], random.choice([1, 2]))

    sentences = [build(random.choice(DAILY_CONTENT_PATTERNS["intro"]))]
    sentences += [build(pattern, tech_pool) for pattern in work_patterns]
    sentences.append(build(random.choice(DAILY_CONTENT_PATTERNS["closing"])))

    return " ".join(sentences)


# ==================== 실습 첫날/둘째날 의무교육 본문 ====================

# 첫날: 오리엔테이션 + 산업안전보건교육 중심 (순서 고정, 3~4문장 중 선택)
ORIENTATION_DAY0_SENTENCES = [
    "실습 첫날을 맞아 회사 소개와 조직 구성에 대한 오리엔테이션을 받았다.",
    "실습 일정 및 근무 수칙에 대한 전반적인 안내를 들었다.",
    "산업안전보건교육을 이수하고 안전수칙을 숙지했다.",
    "비상 상황 발생 시 대피 경로와 행동 요령을 안내받았다.",
    "실습 부서에 배치되어 담당 사수님과 인사를 나누었다.",
]

# 둘째날: 나머지 법정 의무교육 중심 (순서 고정, 3~4문장 중 선택)
ORIENTATION_DAY1_SENTENCES = [
    "직장 내 성희롱 예방교육을 수강했다.",
    "직장 내 괴롭힘 예방교육을 통해 관련 규정을 확인했다.",
    "개인정보보호 교육을 이수하고 취급 시 유의사항을 익혔다.",
    "보안서약서를 작성하고 정보 보안 수칙을 안내받았다.",
    "사내 규정 및 근무수칙에 대한 안내를 받았다.",
]


def generate_orientation_content(day_index: int) -> str:
    """실습 첫날(0)/둘째날(1) 의무교육 본문 생성 (3~4문장)"""
    sentences = ORIENTATION_DAY0_SENTENCES if day_index == 0 else ORIENTATION_DAY1_SENTENCES
    count = random.choice([3, 4])
    return " ".join(sentences[:count])


def generate_daily_entry(date: datetime = None, words: dict = None) -> dict:
    """날짜별 실습 일지 항목 생성"""
    if words is None:
        words = load_words()

    if date is None:
        date = datetime.now()

    day_of_week = date.weekday()
    day_names = ["월", "화", "수", "목", "금", "토", "일"]

    if day_of_week >= 5:
        return {
            "date": date,
            "day_name": day_names[day_of_week],
            "content": "",
            "work_flag": "N",
            "start_time": "",
            "end_time": "",
            "department": "",
        }

    start_hour = random.choice([8, 9])
    end_hour = random.choice([17, 18])

    return {
        "date": date,
        "day_name": day_names[day_of_week],
        "content": generate_sentence(words),
        "work_flag": "Y",
        "start_time": f"{start_hour:02d}:00",
        "end_time": f"{end_hour:02d}:00",
        "department": random.choice(words["departments"]),
    }


def generate_weekly_summary(week_entries: list) -> str:
    """이번 주 요약 문장 생성"""
    words = load_words()
    return generate_sentence(words)


def generate_week_entries(start_date: datetime, week_num: int) -> list:
    """주차별 일일 항목 리스트 생성"""
    words = load_words()
    week_start = start_date + timedelta(weeks=week_num - 1)
    return [generate_daily_entry(week_start + timedelta(days=i), words) for i in range(7)]


# ==================== CLI ====================

if __name__ == "__main__":
    import sys

    if "--init" in sys.argv:
        save_default_words()
        sys.exit(0)

    words = load_words()

    print("=" * 50)
    print("랜덤 문장 테스트 (10개)")
    print("=" * 50)
    for i in range(10):
        print(f"  {i+1}. {generate_sentence(words)}")

    print(f"\n총 패턴 수: {len(words['patterns'])}")
    print(f"총 형용사 수: {len(words['adjectives'])}")
    print(f"총 명사 수: {len(words['nouns'])}")
    print(f"\nwords.json 수정: python sentence_generator.py --init")
