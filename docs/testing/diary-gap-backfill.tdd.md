# Diary gap backfill TDD evidence

## User journeys

- As a trainee, I want a later successful run to fill every missed weekday, even across a week boundary, so scheduled-run failures do not leave permanent gaps.
- As a trainee, I want the automation to continue with the authenticated session when HIFIVE requires a periodic password change, so the reminder does not block diary submission.

## RED/GREEN evidence

| Guarantee | Test | RED evidence | GREEN evidence |
|---|---|---|---|
| A September 1 run fills missing August 28, August 31, and September 1 entries across weeks 9 and 10 | `BackfillTests.test_run_backfills_empty_weekdays_across_week_boundaries` | Expected save calls for weeks 9 and 10; only week 10 was called | `python -m unittest discover -s tests -v` passed |
| `PW_CHANGE` is treated as an authenticated warning state | `LoginTests.test_password_change_notice_keeps_authenticated_session_usable` | `login()` returned `False` | `python -m unittest discover -s tests -v` passed |

## Additional validation

- `python -m compileall -q auto_diary.py api_server.py sentence_generator.py tests` passed.
- `git diff --check` passed.
- `.github/workflows/diary.yml` parsed successfully with `yaml.safe_load`.

## Known gaps

- HIFIVE is an external service, so final end-to-end proof requires a real GitHub Actions run with the repository secrets.
- The password-change warning is intentionally not dismissed or changed automatically; it is logged while the already-authenticated session continues.
