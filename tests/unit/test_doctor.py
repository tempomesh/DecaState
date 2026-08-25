from decastate.cli.doctor import doctor_report


def test_doctor_reports_python() -> None:
    assert doctor_report()["python"] != "unknown"
