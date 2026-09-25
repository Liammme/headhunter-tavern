from dataclasses import dataclass

from app.crawlers.base import NormalizedJob, SourceAdapter


@dataclass(frozen=True)
class FetchJobsResult:
    fetched_jobs: list[NormalizedJob]
    source_stats: dict[str, int]
    source_health: dict[str, str]
    errors: list[str]


def fetch_jobs(adapters: dict[str, type[SourceAdapter]]) -> FetchJobsResult:
    fetched_jobs: list[NormalizedJob] = []
    source_stats: dict[str, int] = {}
    source_health: dict[str, str] = {}
    errors: list[str] = []

    for source_name, adapter_cls in adapters.items():
        adapter = adapter_cls()
        try:
            jobs = adapter.fetch()
        except Exception as exc:  # noqa: BLE001
            source_stats[source_name] = 0
            source_health[source_name] = "error"
            errors.append(f"{source_name}: {exc}")
            continue

        source_stats[source_name] = len(jobs)
        source_health[source_name] = "ok" if jobs else "empty"
        fetched_jobs.extend(jobs)

    return FetchJobsResult(
        fetched_jobs=fetched_jobs,
        source_stats=source_stats,
        source_health=source_health,
        errors=errors,
    )
