from app.crawlers.adapters.withb import WithBAdapter


def test_withb_adapter_parses_category_pages_and_pagination(monkeypatch):
    pages = {
        "https://withb.co.jp/category/engineer/": """
        <html><body>
          <article>
            <a href="https://withb.co.jp/79872/">
              エンジニア バックエンドエンジニア（TypeScript）
              給与：402万円 〜 600万円
              2026.02.17 株式会社マーキュリー
            </a>
          </article>
          <a href="https://withb.co.jp/category/engineer/page/2/">2</a>
        </body></html>
        """,
        "https://withb.co.jp/category/engineer/page/2/": """
        <html><body>
          <article>
            <a href="https://withb.co.jp/79852/">
              エンジニア 【システムリスク管理部】サイバーセキュリティ担当
              給与：700万円 〜 1100万円
              2026.02.14 ビットバンク株式会社
            </a>
          </article>
        </body></html>
        """,
    }

    monkeypatch.setattr(
        "app.crawlers.adapters.withb.fetch_html",
        lambda url: pages.get(url, "<html><body></body></html>"),
    )
    monkeypatch.setattr(
        "app.crawlers.adapters.withb.CATEGORY_URLS",
        ("https://withb.co.jp/category/engineer/",),
    )

    jobs = WithBAdapter().fetch()

    assert [job.canonical_url for job in jobs] == [
        "https://withb.co.jp/79872/",
        "https://withb.co.jp/79852/",
    ]
    assert jobs[0].title == "バックエンドエンジニア（TypeScript）"
    assert jobs[0].company == "株式会社マーキュリー"
    assert jobs[0].location == "Japan"
    assert jobs[0].source_job_id == "79872"
    assert jobs[0].raw_payload["site"] == "withb"
    assert jobs[0].raw_payload["salary"] == "402万円 〜 600万円"
    assert jobs[0].posted_at is not None
