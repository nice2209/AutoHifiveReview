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
        "검색 기능", "필터링", "정렬 기능", "페이지네이션", "无限滚动",
        # 프론트엔드
        "React", "Flutter", "SwiftUI", "Jetpack Compose", "TypeScript",
        "컴포넌트 설계", "상태 관리", "라우팅", "네비게이션", "애니메이션",
        "반응형 UI", "다크 모드", "테마 설정", "다국어 지원", "접근성",
        # 백엔드
        "REST API", "GraphQL", "WebSocket", "JWT 인증", "OAuth",
        "Microservices", "Docker", "CI/CD", "AWS", "Firebase",
        "데이터 동기화", "오프라인 지원", "이미지 업로드", "파일 관리", "캐싱",
        # 개발 도구/프로세스
        "Git", "코드 리뷰", "单元测试", "통합 테스트", "배포",
        "디버깅", "프로파일링", "메모리 최적화", "성능 튜닝", "보안 점검",
        "문서화", "일정 관리", "스프린트", "회고", "기획 미팅",
        # 실무
        "에러 처리", "로깅", "모니터링", "사용자 피드백", "A/B 테스트",
        "데이터 분석", "사용자 분석", "전환율 최적화", "버그 수정", "기능 개선",
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
