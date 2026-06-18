from app.crawlers.adapters.aijobsnet import AIJobsNetAdapter
from app.crawlers.adapters.cryptocurrencyjobs import CryptocurrencyJobsAdapter
from app.crawlers.adapters.cryptojobslist import CryptoJobsListAdapter
from app.crawlers.adapters.wantedly import WantedlyAdapter


def test_aijobsnet_uses_detail_description_when_available(monkeypatch):
    listing_html = """
    <ul id="job_list">
      <li>
        <a href="/job/123">AI Engineer</a>
        <div><div><span>Python</span></div></div>
      </li>
    </ul>
    """
    detail_html = "<main>Apply via TG: @HiringLead</main>"

    def fake_fetch_html(url: str, timeout: int = 30) -> str:
        return detail_html if "/job/123" in url else listing_html

    monkeypatch.setattr("app.crawlers.adapters.aijobsnet.fetch_html", fake_fetch_html)

    jobs = AIJobsNetAdapter().fetch()

    assert len(jobs) == 1
    assert "TG: @HiringLead" in jobs[0].description


def test_cryptocurrencyjobs_falls_back_to_listing_tags_when_detail_fails(monkeypatch):
    listing_html = """
    <section id="find-a-job">
      <ul class="mt-6">
        <li class="grid">
          <h2><a href="/companies/backend-engineer/">Backend Engineer</a></h2>
          <h3><a href="/companies/acme/">Acme</a></h3>
          <ul class="flex flex-wrap"><a href="/tags/rust">Rust</a></ul>
        </li>
      </ul>
    </section>
    """

    def fake_fetch_html(url: str, timeout: int = 30) -> str:
        if url != "https://www.cryptocurrencyjobs.co/":
            raise RuntimeError("detail unavailable")
        return listing_html

    monkeypatch.setattr("app.crawlers.adapters.cryptocurrencyjobs.fetch_html", fake_fetch_html)

    jobs = CryptocurrencyJobsAdapter().fetch()

    assert len(jobs) == 1
    assert jobs[0].description == "Rust"


def test_cryptojobslist_uses_detail_description(monkeypatch):
    listing_html = """
    <table class="job-preview-inline-table">
      <tbody>
        <tr>
          <td><a href="/jobs/bd-manager">BD Manager</a></td>
          <td><a href="/companies/acme">Acme</a></td>
          <td></td>
          <td>Remote</td>
        </tr>
      </tbody>
    </table>
    """
    detail_html = "<article>Contact WeChat: talent_bd_01</article>"

    def fake_fetch_html(url: str, timeout: int = 30) -> str:
        return detail_html if "/jobs/bd-manager" in url else listing_html

    monkeypatch.setattr("app.crawlers.adapters.cryptojobslist.fetch_html", fake_fetch_html)

    jobs = CryptoJobsListAdapter().fetch()

    assert len(jobs) == 1
    assert "WeChat: talent_bd_01" in jobs[0].description


def test_wantedly_uses_detail_description_and_company(monkeypatch):
    listing_html = '<a href="/projects/42">Product Manager</a>'
    detail_html = """
    <main>
      <a href="/companies/acme">Acme Japan</a>
      <section class="project-description">連絡先 WeChat: talent_jp_01</section>
    </main>
    """

    def fake_fetch_html(url: str, timeout: int = 30) -> str:
        return detail_html if "/projects/42" in url else listing_html

    monkeypatch.setattr("app.crawlers.adapters.wantedly.fetch_html", fake_fetch_html)

    jobs = WantedlyAdapter().fetch()

    assert len(jobs) == 1
    assert jobs[0].company == "Acme Japan"
    assert "WeChat: talent_jp_01" in jobs[0].description
