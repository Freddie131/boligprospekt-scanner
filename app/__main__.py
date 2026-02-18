import argparse

from app.core.config import get_settings
from app.core.db import SessionLocal, engine
from app.core.logging import configure_logging
from app.domain.models import Base
from app.jobs.weekly_job import WeeklyJobService


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app")
    sub = parser.add_subparsers(dest="command", required=True)

    run_job = sub.add_parser("run-job")
    run_job.add_argument("job_name", choices=["weekly"])

    args = parser.parse_args()
    configure_logging()
    Base.metadata.create_all(bind=engine)

    if args.command == "run-job" and args.job_name == "weekly":
        with SessionLocal() as db:
            run = WeeklyJobService(db, get_settings()).run()
            print(f"Weekly job complete: id={run.id}, html={run.report_html_path}, pdf={run.report_pdf_path}")


if __name__ == "__main__":
    main()
