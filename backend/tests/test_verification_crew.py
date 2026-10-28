from crews import verification_crew


def test_manager_report_cannot_change_official_score(monkeypatch):
    official_scoring = {
        "score": 25,
        "risk_level": "medium",
        "findings": [],
    }

    evidence = {
        "company_name": "Example Technologies",
        "cin": "",
        "website": "",
        "offer_text": "Example offer",
        "checks": {},
    }

    result = {
        "status": "completed",
        "company_name": "Example Technologies",
        "checks": {},
        "scoring": official_scoring.copy(),
        "limitations": [],
    }

    class FakeCrew:
        def kickoff(self, inputs):
            # Simulate an LLM report that tries to invent a new score.
            return (
                "This company is fraudulent. "
                "The new risk score is 100/100."
            )

    monkeypatch.setattr(
        verification_crew,
        "collect_verification_evidence",
        lambda **kwargs: evidence,
    )
    monkeypatch.setattr(
        verification_crew,
        "build_verification_result",
        lambda evidence: result,
    )
    monkeypatch.setattr(
        verification_crew,
        "create_hierarchical_crew",
        lambda: FakeCrew(),
    )
    monkeypatch.setattr(
        verification_crew,
        "persist_verification_result",
        lambda result: result,
    )

    response = verification_crew.verify_company(
        company_name="Example Technologies",
        offer_text="Example offer",
    )

    assert response["scoring"] == official_scoring
    assert response["scoring"]["score"] == 25
    assert response["scoring"]["risk_level"] == "medium"
    assert "100/100" in response["investigation"]["report"]