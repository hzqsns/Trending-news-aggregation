from app.platform.scheduler import SchedulerKernel
from app.scheduler import (
    job_anomaly_check,
    job_cleanup,
    job_evening_report,
    job_fetch_news,
    job_fetch_twitter,
    job_morning_report,
    job_push_digest,
    job_push_important,
    job_twitter_digest,
)


def register_investment_jobs(kernel: SchedulerKernel) -> None:
    kernel.add_agent_job("investment", "fetch_news", job_fetch_news, "interval", minutes=15)
    kernel.add_agent_job("investment", "push_important", job_push_important, "interval", minutes=5)
    kernel.add_agent_job("investment", "push_digest", job_push_digest, "interval", minutes=30)
    kernel.add_agent_job("investment", "anomaly_check", job_anomaly_check, "interval", minutes=10)
    kernel.add_agent_job("investment", "morning_report", job_morning_report, "cron", hour=7, minute=30)
    kernel.add_agent_job("investment", "evening_report", job_evening_report, "cron", hour=22, minute=0)
    kernel.add_agent_job("investment", "cleanup", job_cleanup, "cron", hour=3, minute=0)
    kernel.add_agent_job("investment", "fetch_twitter", job_fetch_twitter, "interval", minutes=30)
    kernel.add_agent_job("investment", "twitter_digest", job_twitter_digest, "cron", hour=9, minute=0)


__all__ = ["register_investment_jobs"]
