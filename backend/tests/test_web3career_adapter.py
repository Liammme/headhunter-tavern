from app.crawlers.adapters.web3career import Web3CareerAdapter


def test_web3career_uses_listing_links_when_json_ld_has_no_url(monkeypatch):
    html = """
    <html>
      <body>
        <a href="/front-end-engineer-blackwing/103745">Front End Engineer Blackwing 6h</a>
        <a href="/backend-engineer-blackwing/103747">Backend Engineer Blackwing 6h</a>
        <script type="application/ld+json">
          {
            "@context": "https://schema.org",
            "@type": "JobPosting",
            "datePosted": "2026-04-26 01:01:06 +0100",
            "title": "Front End Engineer",
            "description": "Build crypto-native front end products.",
            "hiringOrganization": {"@type": "Organization", "name": "Blackwing"},
            "applicantLocationRequirements": {"name": "Remote"},
            "employmentType": "Full-time"
          }
        </script>
        <script type="application/ld+json">
          {
            "@context": "https://schema.org",
            "@type": "JobPosting",
            "datePosted": "2026-04-26 01:00:59 +0100",
            "title": "Backend Engineer",
            "description": "Build crypto-native backend systems.",
            "hiringOrganization": {"@type": "Organization", "name": "Blackwing"},
            "applicantLocationRequirements": {"name": "Remote"},
            "employmentType": "Full-time"
          }
        </script>
      </body>
    </html>
    """
    monkeypatch.setattr("app.crawlers.adapters.web3career.fetch_html", lambda _url: html)

    jobs = Web3CareerAdapter().fetch()

    assert [job.canonical_url for job in jobs] == [
        "https://web3.career/front-end-engineer-blackwing/103745",
        "https://web3.career/backend-engineer-blackwing/103747",
    ]
