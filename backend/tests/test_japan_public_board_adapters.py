from app.crawlers.adapters.careercross import CareerCrossAdapter
from app.crawlers.adapters.daijob import DaijobAdapter
from app.crawlers.adapters.gaijinpot import GaijinPotAdapter
from app.crawlers.adapters.mynavi_tenshoku import MynaviTenshokuAdapter
from app.crawlers.adapters.type_jp import TypeJpAdapter
from app.crawlers.adapters.wantedly import WantedlyAdapter
from app.crawlers.japan_registry import JAPAN_ADAPTERS
from app.crawlers.registry import ADAPTERS


def test_careercross_adapter_parses_kaigai_job_links(monkeypatch):
    kaigai_html = """
    <a href="/job-search/specialty-10?utm_source=careercross">海外求人</a>
    <a href="https://www.careercross.com/job/detail-1593181"
       title="【英語を活かす】事業開発マネージャー/ Business Development Manager">
      【英語を活かす】事業開発マネージャー/ Business ...
    </a>
    """
    listing_html = """
    <div class="result-job-box">
      <a href="https://www.careercross.com/job/detail-1582269?sid=1&page=1"
         title="【インドネシア勤務】拠点立ち上げ・営業マネジャー候補">
        <span class="badge">リモートワーク</span>
        <span>【インドネシア勤務】拠点立ち上げ・営業マネジャー候補</span>
      </a>
      <table>
        <tr><td>採用企業</td><td>株式会社ウィル・シード</td></tr>
        <tr><td>勤務地</td><td>インドネシア</td></tr>
        <tr><td>雇用形態</td><td>正社員</td></tr>
      </table>
    </div>
    """

    def fake_fetch_html(url):
        if url == "https://www.careercross.com/kaigai":
            return kaigai_html
        assert url == "https://www.careercross.com/job-search/specialty-10"
        return listing_html

    monkeypatch.setattr("app.crawlers.adapters.careercross.fetch_html", fake_fetch_html)

    jobs = CareerCrossAdapter().fetch()

    assert len(jobs) == 2
    assert jobs[0].canonical_url == "https://www.careercross.com/job/detail-1593181"
    assert jobs[0].title == "【英語を活かす】事業開発マネージャー/ Business Development Manager"
    assert jobs[0].source_job_id == "1593181"
    assert jobs[0].raw_payload["site"] == "careercross"
    assert jobs[1].canonical_url == "https://www.careercross.com/job/detail-1582269"
    assert jobs[1].company == "株式会社ウィル・シード"
    assert jobs[1].location == "インドネシア"
    assert jobs[1].employment_type == "正社員"
    assert jobs[1].remote_type == "remote"


def test_careercross_adapter_is_japan_only_source():
    assert JAPAN_ADAPTERS["careercross"] is CareerCrossAdapter
    assert "careercross" not in ADAPTERS


def test_mynavi_tenshoku_adapter_parses_job_links(monkeypatch):
    html = """
    <a href="//tenshoku.mynavi.jp/jobinfo-383998-1-14-1/">
      【ゲームエンジニア】＃未経験歓迎＃リモート70%～＃年休125日
    </a>
    """
    monkeypatch.setattr("app.crawlers.adapters.mynavi_tenshoku.fetch_html", lambda url: html)

    jobs = MynaviTenshokuAdapter().fetch()

    assert len(jobs) == 1
    assert jobs[0].canonical_url == "https://tenshoku.mynavi.jp/jobinfo-383998-1-14-1/"
    assert jobs[0].title == "【ゲームエンジニア】＃未経験歓迎＃リモート70%～＃年休125日"
    assert jobs[0].source_job_id == "jobinfo-383998-1-14-1"
    assert jobs[0].raw_payload["site"] == "mynavi_tenshoku"


def test_type_jp_adapter_parses_job_links(monkeypatch):
    html = """
    <a href="https://type.jp/job-company/43073/message/?jobId=1347982">
      開発エンジニア｜面接1回｜還元率最大89%｜フルリモートも可
    </a>
    """
    monkeypatch.setattr("app.crawlers.adapters.type_jp.fetch_html", lambda url: html)

    jobs = TypeJpAdapter().fetch()

    assert len(jobs) == 1
    assert jobs[0].canonical_url == "https://type.jp/job-company/43073/message/?jobId=1347982"
    assert jobs[0].title == "開発エンジニア｜面接1回｜還元率最大89%｜フルリモートも可"
    assert jobs[0].source_job_id == "1347982"
    assert jobs[0].remote_type == "remote"
    assert jobs[0].raw_payload["site"] == "type_jp"


def test_wantedly_adapter_parses_project_links(monkeypatch):
    html = """
    <a href="/projects/2313760?featured=0">
      iOSアプリエンジニア 24 エントリー 熱量を形に。1億超の作品が動くpixivアプリを届けるiOSエンジニア募集
    </a>
    """
    monkeypatch.setattr("app.crawlers.adapters.wantedly.fetch_html", lambda url: html)

    jobs = WantedlyAdapter().fetch()

    assert len(jobs) == 1
    assert jobs[0].canonical_url == "https://www.wantedly.com/projects/2313760"
    assert jobs[0].title.startswith("iOSアプリエンジニア")
    assert jobs[0].source_job_id == "2313760"
    assert jobs[0].raw_payload["site"] == "wantedly"


def test_daijob_adapter_parses_job_links(monkeypatch):
    html = """
    <a href="/en/jobs/detail/1526823">TOKI Co., Ltd.</a>
    <a href="/en/jobs/detail/1526823">View Full Listing</a>
    <a href="/en/jobs/detail/1526823">
      ◆◇Join us August 1st! Luxury Travel Specialist Travel Agent◇◆
      Travel Coordinator / VIP Inbound Travel Specialist Company [TOKI Co., Ltd.]
    </a>
    """
    monkeypatch.setattr("app.crawlers.adapters.daijob.fetch_html", lambda url: html)

    jobs = DaijobAdapter().fetch()

    assert len(jobs) == 1
    assert jobs[0].canonical_url == "https://www.daijob.com/en/jobs/detail/1526823"
    assert jobs[0].company == "TOKI Co., Ltd."
    assert "Luxury Travel Specialist" in jobs[0].title
    assert jobs[0].source_job_id == "1526823"
    assert jobs[0].raw_payload["site"] == "daijob"


def test_gaijinpot_adapter_parses_job_links(monkeypatch):
    html = """
    <a href="/en/job/158692">Full Time Street Go-Kart Tour Guide</a>
    """
    monkeypatch.setattr("app.crawlers.adapters.gaijinpot.fetch_html", lambda url: html)

    jobs = GaijinPotAdapter().fetch()

    assert len(jobs) == 1
    assert jobs[0].canonical_url == "https://jobs.gaijinpot.com/en/job/158692"
    assert jobs[0].title == "Full Time Street Go-Kart Tour Guide"
    assert jobs[0].source_job_id == "158692"
    assert jobs[0].raw_payload["site"] == "gaijinpot"
