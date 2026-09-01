# Korean public holiday safeguards TDD evidence

## User journey

As a trainee, I want automatic diary generation to skip Korean public holidays, including substitute holidays and Chuseok, so days off are not recorded as workdays.

## RED/GREEN evidence

| Guarantee | Test | RED evidence | GREEN evidence |
|---|---|---|---|
| Chuseok and substitute holidays are recognized | `HolidayTests.test_recognizes_chuseok_and_substitute_holidays` | `get_public_holiday_name` did not exist | Test passed with `holidays` 0.103 |
| Training-day numbering excludes public holidays | `HolidayTests.test_weekday_index_excludes_public_holidays` | August 18 was incorrectly counted as day 3 instead of day 2 | Test passed |
| Normal runs preserve an existing holiday entry, while explicit cleanup clears it without changing a regular entry | `BackfillTests.test_run_preserves_existing_public_holiday_entry_without_explicit_cleanup`, `BackfillTests.test_explicit_cleanup_clears_holidays_and_preserves_regular_entries` | Normal runs deleted existing content and no explicit cleanup function existed | Tests passed |
| The HIFIVE save form sends blank content and `work_flag=N` for a forced holiday cleanup | `HolidayTests.test_save_force_clear_sends_empty_content_and_non_working_flag` | New save behavior had no implementation | Test passed |
| `--rewrite` never generates new work content for a public holiday | `BackfillTests.test_rewrite_does_not_generate_new_content_for_a_public_holiday` | Rewrite replaced a holiday record with generated content | Test passed |

## Validation

- `python -m unittest discover -s tests -v`
- `python -m compileall -q auto_diary.py api_server.py sentence_generator.py tests`

## Known gap

Company-specific shutdowns or personal leave are not public holidays and require an explicit custom-date list if needed later.
