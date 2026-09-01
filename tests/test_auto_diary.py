import json
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

import auto_diary


class FakeResponse:
    def __init__(self, *, status_code=200, text=""):
        self.status_code = status_code
        self.text = text


class LoginTests(unittest.TestCase):
    def test_password_change_notice_keeps_authenticated_session_usable(self):
        session = Mock()
        session.get.side_effect = [
            FakeResponse(status_code=200),
            FakeResponse(
                text="cb("
                + json.dumps(
                    {
                        "RESULT_CODE": "PW_CHANGE",
                        "RESULT_MESSAGE": "비밀번호를 변경한지 [61]일이 지났습니다. 비밀번호를 변경하세요.",
                    },
                    ensure_ascii=False,
                )
                + ")"
            ),
        ]

        self.assertTrue(auto_diary.login(session, "student", "password"))


class BackfillTests(unittest.TestCase):
    def test_run_backfills_empty_weekdays_across_week_boundaries(self):
        slots = [
            {
                "WEEK_SEQ": "9",
                "WEEK_GUBUN": auto_diary.GUBUN_SUMMARY,
                "START_DATE": "20260824",
                "END_DATE": "20260830",
                "DY": "",
                "REPORT_DESC": "8§17§업무§개발",
                "WORK_FLAG": "N",
            },
            {
                "WEEK_SEQ": "9",
                "WEEK_GUBUN": auto_diary.GUBUN_DAILY,
                "START_DATE": "20260828",
                "END_DATE": "20260828",
                "DY": "금",
                "REPORT_DESC": "",
                "WORK_FLAG": "N",
            },
            {
                "WEEK_SEQ": "10",
                "WEEK_GUBUN": auto_diary.GUBUN_SUMMARY,
                "START_DATE": "20260831",
                "END_DATE": "20260906",
                "DY": "",
                "REPORT_DESC": "8§17§업무§개발",
                "WORK_FLAG": "N",
            },
            {
                "WEEK_SEQ": "10",
                "WEEK_GUBUN": auto_diary.GUBUN_DAILY,
                "START_DATE": "20260831",
                "END_DATE": "20260831",
                "DY": "월",
                "REPORT_DESC": "",
                "WORK_FLAG": "N",
            },
            {
                "WEEK_SEQ": "10",
                "WEEK_GUBUN": auto_diary.GUBUN_DAILY,
                "START_DATE": "20260901",
                "END_DATE": "20260901",
                "DY": "화",
                "REPORT_DESC": "",
                "WORK_FLAG": "N",
            },
        ]
        trainee = {
            "TRAINEE_SEQ": "123",
            "TRAINEE_START_DATE": "20260701",
        }

        with (
            patch.object(auto_diary, "load_credentials", return_value={"user_id": "u", "password": "p"}),
            patch.object(auto_diary, "login", return_value=True),
            patch.object(auto_diary, "get_trainee_info", return_value=trainee),
            patch.object(auto_diary, "get_existing_entries", return_value=slots),
            patch.object(auto_diary, "load_words", return_value={}),
            patch.object(auto_diary, "generate_daily_content", return_value="자동 생성 내용"),
            patch.object(auto_diary, "save_diary_entry", return_value=True) as save,
        ):
            result = auto_diary.run(target_date=datetime(2026, 9, 1))

        self.assertTrue(result)
        self.assertEqual([call.args[2] for call in save.call_args_list], ["9", "10"])
        saved_dates = [
            entry["date"].strftime("%Y%m%d")
            for call in save.call_args_list
            for entry in call.args[3]
            if entry["content"]
        ]
        self.assertEqual(saved_dates, ["20260828", "20260831", "20260901"])

    def test_run_preserves_existing_public_holiday_entry_without_explicit_cleanup(self):
        slots = [
            {
                "WEEK_SEQ": "5",
                "WEEK_GUBUN": auto_diary.GUBUN_SUMMARY,
                "START_DATE": "20260817",
                "END_DATE": "20260823",
                "DY": "",
                "REPORT_DESC": "8§17§업무§개발",
                "WORK_FLAG": "N",
            },
            {
                "WEEK_SEQ": "5",
                "WEEK_GUBUN": auto_diary.GUBUN_DAILY,
                "START_DATE": "20260817",
                "END_DATE": "20260817",
                "DY": "월",
                "REPORT_DESC": "잘못 작성된 자동 일지",
                "WORK_FLAG": "Y",
            },
            {
                "WEEK_SEQ": "5",
                "WEEK_GUBUN": auto_diary.GUBUN_DAILY,
                "START_DATE": "20260818",
                "END_DATE": "20260818",
                "DY": "화",
                "REPORT_DESC": "정상 근무일 일지",
                "WORK_FLAG": "Y",
            },
        ]
        trainee = {
            "TRAINEE_SEQ": "123",
            "TRAINEE_START_DATE": "20260720",
        }

        with (
            patch.object(auto_diary, "load_credentials", return_value={"user_id": "u", "password": "p"}),
            patch.object(auto_diary, "login", return_value=True),
            patch.object(auto_diary, "get_trainee_info", return_value=trainee),
            patch.object(auto_diary, "get_existing_entries", return_value=slots),
            patch.object(auto_diary, "load_words", return_value={}),
            patch.object(auto_diary, "save_diary_entry", return_value=True) as save,
        ):
            result = auto_diary.run(target_date=datetime(2026, 8, 18))

        self.assertTrue(result)
        save.assert_not_called()

    def test_explicit_cleanup_clears_holidays_and_preserves_regular_entries(self):
        slots = [
            {
                "WEEK_SEQ": "5",
                "WEEK_GUBUN": auto_diary.GUBUN_SUMMARY,
                "START_DATE": "20260817",
                "END_DATE": "20260823",
                "DY": "",
                "REPORT_DESC": "8§17§업무§개발",
                "WORK_FLAG": "N",
            },
            {
                "WEEK_SEQ": "5",
                "WEEK_GUBUN": auto_diary.GUBUN_DAILY,
                "START_DATE": "20260817",
                "END_DATE": "20260817",
                "DY": "월",
                "REPORT_DESC": "잘못 작성된 자동 일지",
                "WORK_FLAG": "Y",
            },
            {
                "WEEK_SEQ": "5",
                "WEEK_GUBUN": auto_diary.GUBUN_DAILY,
                "START_DATE": "20260818",
                "END_DATE": "20260818",
                "DY": "화",
                "REPORT_DESC": "정상 근무일 일지",
                "WORK_FLAG": "Y",
            },
        ]
        trainee = {
            "TRAINEE_SEQ": "123",
            "TRAINEE_START_DATE": "20260720",
        }

        with (
            patch.object(auto_diary, "load_credentials", return_value={"user_id": "u", "password": "p"}),
            patch.object(auto_diary, "login", return_value=True),
            patch.object(auto_diary, "get_trainee_info", return_value=trainee),
            patch.object(auto_diary, "get_existing_entries", return_value=slots),
            patch.object(auto_diary, "save_diary_entry", return_value=True) as save,
        ):
            result = auto_diary.clear_holiday_entries(until=datetime(2026, 8, 18))

        self.assertTrue(result)
        entries = save.call_args.args[3]
        holiday_entry = next(e for e in entries if e["date"].strftime("%Y%m%d") == "20260817")
        regular_entry = next(e for e in entries if e["date"].strftime("%Y%m%d") == "20260818")
        self.assertEqual(holiday_entry["content"], "")
        self.assertEqual(holiday_entry["work_flag"], "N")
        self.assertTrue(holiday_entry["force_clear"])
        self.assertEqual(regular_entry["content"], "정상 근무일 일지")

    def test_rewrite_does_not_generate_new_content_for_a_public_holiday(self):
        slots = [
            {
                "WEEK_SEQ": "5",
                "WEEK_GUBUN": auto_diary.GUBUN_SUMMARY,
                "START_DATE": "20260817",
                "END_DATE": "20260823",
                "DY": "",
                "REPORT_DESC": "8§17§업무§개발",
                "WORK_FLAG": "N",
            },
            {
                "WEEK_SEQ": "5",
                "WEEK_GUBUN": auto_diary.GUBUN_DAILY,
                "START_DATE": "20260817",
                "END_DATE": "20260817",
                "DY": "월",
                "REPORT_DESC": "수동 휴일 근무 기록",
                "WORK_FLAG": "Y",
            },
            {
                "WEEK_SEQ": "5",
                "WEEK_GUBUN": auto_diary.GUBUN_DAILY,
                "START_DATE": "20260818",
                "END_DATE": "20260818",
                "DY": "화",
                "REPORT_DESC": "기존 평일 기록",
                "WORK_FLAG": "Y",
            },
        ]
        trainee = {
            "TRAINEE_SEQ": "123",
            "TRAINEE_START_DATE": "20260720",
        }

        with (
            patch.object(auto_diary, "load_credentials", return_value={"user_id": "u", "password": "p"}),
            patch.object(auto_diary, "login", return_value=True),
            patch.object(auto_diary, "get_trainee_info", return_value=trainee),
            patch.object(auto_diary, "get_existing_entries", return_value=slots),
            patch.object(auto_diary, "load_words", return_value={}),
            patch.object(auto_diary, "generate_daily_content", return_value="새 자동 내용"),
            patch.object(auto_diary, "save_diary_entry", return_value=True) as save,
        ):
            result = auto_diary.rewrite_entries(until=datetime(2026, 8, 18))

        self.assertTrue(result)
        entries = save.call_args.args[3]
        holiday_entry = next(e for e in entries if e["date"].strftime("%Y%m%d") == "20260817")
        self.assertEqual(holiday_entry["content"], "수동 휴일 근무 기록")


class HolidayTests(unittest.TestCase):
    def test_recognizes_chuseok_and_substitute_holidays(self):
        self.assertIn("추석", auto_diary.get_public_holiday_name(datetime(2026, 9, 24)))
        self.assertEqual(auto_diary.get_public_holiday_name(datetime(2026, 9, 25)), "추석")
        self.assertIn("대체", auto_diary.get_public_holiday_name(datetime(2026, 8, 17)))
        self.assertIsNone(auto_diary.get_public_holiday_name(datetime(2026, 9, 28)))

    def test_recognizes_2026_public_holiday_categories(self):
        for day in (
            datetime(2026, 3, 2),   # 삼일절 대체공휴일
            datetime(2026, 5, 1),   # 노동절
            datetime(2026, 5, 25),  # 부처님오신날 대체공휴일
            datetime(2026, 6, 3),   # 지방선거일
            datetime(2026, 7, 17),  # 제헌절
            datetime(2026, 10, 5),  # 개천절 대체공휴일
        ):
            with self.subTest(day=day):
                self.assertIsNotNone(auto_diary.get_public_holiday_name(day))

    def test_run_skips_public_holiday_before_login(self):
        with patch.object(auto_diary, "login") as login:
            result = auto_diary.run(target_date=datetime(2026, 8, 17))

        self.assertTrue(result)
        login.assert_not_called()

    def test_weekday_index_excludes_public_holidays(self):
        # 8/14(금)=1일차, 8/17(월)=광복절 대체공휴일, 8/18(화)=2일차.
        self.assertEqual(auto_diary.weekday_index("20260814", datetime(2026, 8, 18)), 2)

    def test_save_force_clear_sends_empty_content_and_non_working_flag(self):
        slots = [
            {
                "WEEK_SEQ": "5",
                "WEEK_GUBUN": auto_diary.GUBUN_SUMMARY,
                "START_DATE": "20260817",
                "END_DATE": "20260823",
                "DY": "월",
                "REPORT_DESC": "8§17§업무§개발",
                "WORK_FLAG": "N",
                "TEACHER_NAME": "",
            },
            {
                "WEEK_SEQ": "5",
                "WEEK_GUBUN": auto_diary.GUBUN_DAILY,
                "START_DATE": "20260817",
                "END_DATE": "20260817",
                "DY": "월",
                "REPORT_DESC": "잘못 작성된 자동 일지",
                "WORK_FLAG": "Y",
                "TEACHER_NAME": "",
            },
            {
                "WEEK_SEQ": "5",
                "WEEK_GUBUN": auto_diary.GUBUN_DAILY,
                "START_DATE": "20260818",
                "END_DATE": "20260818",
                "DY": "화",
                "REPORT_DESC": "정상 근무일 일지",
                "WORK_FLAG": "Y",
                "TEACHER_NAME": "",
            },
        ]
        entries = [
            {
                "date": datetime(2026, 8, 17),
                "day_name": "월",
                "content": "",
                "work_flag": "N",
                "start_time": "",
                "end_time": "",
                "department": "",
                "force_clear": True,
            }
        ]
        session = Mock()
        session.post.return_value = FakeResponse(text="{'result':'y'}")

        with patch.object(auto_diary, "get_existing_entries", return_value=slots):
            result = auto_diary.save_diary_entry(session, "123", "5", entries)

        self.assertTrue(result)
        form_data = session.post.call_args.kwargs["data"]
        self.assertEqual(
            [value for key, value in form_data if key == "reportDesc"],
            ["8§17§업무§개발", "", "정상 근무일 일지"],
        )
        self.assertEqual([value for key, value in form_data if key == "work_flag"], ["N", "N", "Y"])


if __name__ == "__main__":
    unittest.main()
