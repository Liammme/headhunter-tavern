from app.crawlers.adapters.green_japan import GreenJapanAdapter


def test_green_japan_adapter_parses_listing_cards(monkeypatch):
    html = """
    <html>
      <body>
        <a href="/company/11130/job/315985">
          株式会社 ミラリンク 6 人 2022年 設立
          フルリモート可｜Claude Codeを利用した0→1開発で、製造業×AI の技術リードを募集
          リードエンジニア フルリモート 600万円〜650万円
          Python, Django, React, TypeScript, Docker, Azure
        </a>
      </body>
    </html>
    """
    monkeypatch.setattr("app.crawlers.adapters.green_japan.fetch_html", lambda url: html)

    jobs = GreenJapanAdapter().fetch()

    assert len(jobs) == 1
    assert jobs[0].canonical_url == "https://www.green-japan.com/company/11130/job/315985"
    assert "リードエンジニア" in jobs[0].title
    assert jobs[0].company == "株式会社 ミラリンク"
    assert jobs[0].location == "フルリモート"
    assert jobs[0].remote_type == "remote"
    assert jobs[0].source_job_id == "company/11130/job/315985"
    assert jobs[0].raw_payload["site"] == "green_japan"
