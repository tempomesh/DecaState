"""Phase 0 environment probe; writes no model or inference state."""

from decastate.cli.doctor import doctor_report


if __name__ == "__main__":
    doctor_report()
