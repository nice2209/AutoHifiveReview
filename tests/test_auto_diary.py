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


if __name__ == "__main__":
    unittest.main()
