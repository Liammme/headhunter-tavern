from app.crawlers.adapters.japan_dev import JapanDevAdapter


def test_japan_dev_adapter_parses_listing_cards(monkeypatch):
    html = """
    <article class="job-item">
      <div class="job-item__main-data">
        <h2>
          <a href="/jobs/mode/software-engineer-1" class="job-item__title">
            Software Engineer
          </a>
        </h2>
        <div class="extras-box">
          <div class="job-item__contract-type">MODE・Sensor data platform</div>
        </div>
      </div>
      <ul class="job-top-tag-list">
        <li class="job-top-tag-list__job-top-tag"><span>Residents Only</span></li>
        <li class="job-top-tag-list__job-top-tag"><span>¥8.5M ~ ¥10M</span></li>
      </ul>
      <div class="job__tag"><div class="job__tag-desc">Tokyo</div></div>
    </article>
    """
    monkeypatch.setattr("app.crawlers.adapters.japan_dev.fetch_html", lambda url: html)

    jobs = JapanDevAdapter().fetch()

    assert len(jobs) == 1
    assert jobs[0].canonical_url == "https://japan-dev.com/jobs/mode/software-engineer-1"
    assert jobs[0].title == "Software Engineer"
    assert jobs[0].company == "MODE"
    assert jobs[0].location == "Tokyo"
    assert jobs[0].source_job_id == "jobs/mode/software-engineer-1"
    assert jobs[0].raw_payload["site"] == "japan_dev"
