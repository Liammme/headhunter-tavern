from __future__ import annotations

from app.crawlers.adapters.bonjour_bio import BonjourBioAdapter


LISTING_HTML = """
<html>
  <body>
    <script>
      self.__next_f.push([1, "3:[{\\"id\\":\\"job-1\\",\\"teamSlug\\":\\"acme-ai\\",\\"descriptionMarkdown\\":\\"Inline JD from listing\\\\nAI agent work\\\\nApply via hiring@acme.ai\\"}]"]);
    </script>
    <div class="jp-job-row">
      <a class="jp-job-cover" aria-label="查看 Acme AI 的 Agent Engineer 职位" href="/jobs-mapping/jobs/job-1?src=list">查看职位详情</a>
      <a class="jp-team" href="/jobs-mapping/team/acme-ai?from=%2Fjobs">
        <div class="jp-team-name">Acme AI</div>
      </a>
      <div class="jp-role-title">Agent Engineer</div>
      <div class="jp-meta">
        <span class="jp-loc">Remote</span>
        <span class="jp-loc">Senior</span>
      </div>
    </div>
    <div class="jp-job-row">
      <a class="jp-job-cover" aria-label="查看 Acme AI 的 Agent Engineer 职位" href="/jobs-mapping/jobs/job-1?src=list">查看职位详情</a>
      <a class="jp-team" href="/jobs-mapping/team/acme-ai?from=%2Fjobs">
        <div class="jp-team-name">Acme AI</div>
      </a>
      <div class="jp-role-title">Agent Engineer</div>
    </div>
  </body>
</html>
"""

LISTING_HTML_WITHOUT_EMBEDDED = LISTING_HTML.replace(
    """    <script>
      self.__next_f.push([1, "3:[{\\"id\\":\\"job-1\\",\\"teamSlug\\":\\"acme-ai\\",\\"descriptionMarkdown\\":\\"Inline JD from listing\\\\nAI agent work\\\\nApply via hiring@acme.ai\\"}]"]);
    </script>
""",
    "",
)


def test_bonjour_bio_fetches_jobs_from_listing_only(monkeypatch):
    calls: list[str] = []

    def fake_fetch_html(url: str, timeout: int = 30) -> str:
        calls.append(url)
        if url == "https://bonjour.bio/jobs-mapping/jobs":
            return LISTING_HTML_WITHOUT_EMBEDDED
        if url == "https://bonjour.bio/jobs-mapping/jobs/job-1?src=list":
            raise AssertionError("detail page should not be fetched by default")
        if url == "https://bonjour.bio/jobs-mapping/team/acme-ai?from=%2Fjobs":
            raise AssertionError("team page should not be fetched by default")
        raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr("app.crawlers.adapters.bonjour_bio.fetch_html", fake_fetch_html)

    jobs = BonjourBioAdapter().fetch()

    assert len(jobs) == 1
    job = jobs[0]
    assert job.source_job_id == "job-1"
    assert job.canonical_url == "https://bonjour.bio/jobs-mapping/jobs/job-1?src=list"
    assert job.title == "Agent Engineer"
    assert job.company == "Acme AI"
    assert job.location == "Remote / Senior"
    assert job.remote_type == "remote"
    assert "Agent Engineer" in job.description
    assert job.raw_payload == {
        "site": "bonjour_bio",
        "team_slug": "acme-ai",
        "team_url": "https://bonjour.bio/jobs-mapping/team/acme-ai?from=%2Fjobs",
        "company_url": "",
    }
    assert calls.count("https://bonjour.bio/jobs-mapping/jobs/job-1?src=list") == 0
    assert calls.count("https://bonjour.bio/jobs-mapping/team/acme-ai?from=%2Fjobs") == 0


def test_bonjour_bio_keeps_job_when_team_page_fails(monkeypatch):
    calls: list[str] = []

    def fake_fetch_html(url: str, timeout: int = 30) -> str:
        calls.append(url)
        if url == "https://bonjour.bio/jobs-mapping/jobs":
            return LISTING_HTML_WITHOUT_EMBEDDED
        if url == "https://bonjour.bio/jobs-mapping/jobs/job-1?src=list":
            raise AssertionError("detail page should not be fetched by default")
        if url == "https://bonjour.bio/jobs-mapping/team/acme-ai?from=%2Fjobs":
            raise AssertionError("team page should not be fetched by default")
        raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr("app.crawlers.adapters.bonjour_bio.fetch_html", fake_fetch_html)

    jobs = BonjourBioAdapter().fetch()

    assert len(jobs) == 1
    assert "Agent Engineer" in jobs[0].description
    assert "hiring@acme.ai" not in jobs[0].description
    assert jobs[0].raw_payload["company_url"] == ""
    assert calls.count("https://bonjour.bio/jobs-mapping/jobs/job-1?src=list") == 0


def test_bonjour_bio_uses_embedded_listing_description_before_detail(monkeypatch):
    def fake_fetch_html(url: str, timeout: int = 30) -> str:
        if url == "https://bonjour.bio/jobs-mapping/jobs":
            return LISTING_HTML
        if url == "https://bonjour.bio/jobs-mapping/jobs/job-1?src=list":
            raise AssertionError("detail page should not be fetched when listing has description")
        if url == "https://bonjour.bio/jobs-mapping/team/acme-ai?from=%2Fjobs":
            raise AssertionError("team page should not be fetched by default")
        raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr("app.crawlers.adapters.bonjour_bio.fetch_html", fake_fetch_html)

    jobs = BonjourBioAdapter().fetch()

    assert len(jobs) == 1
    assert "Inline JD from listing" in jobs[0].description
    assert "AI agent work" in jobs[0].description
    assert "hiring@acme.ai" in jobs[0].description


def test_bonjour_bio_is_registered_as_global_adapter():
    from app.crawlers.registry import ADAPTERS

    assert ADAPTERS["bonjour_bio"] is BonjourBioAdapter
