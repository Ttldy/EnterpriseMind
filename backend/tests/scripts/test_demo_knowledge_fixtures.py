from scripts.http_demo import create_and_upload


def test_demo_knowledge_covers_hr_it_and_finance() -> None:
    assert hasattr(create_and_upload, "demo_fixture_contents")

    fixtures = create_and_upload.demo_fixture_contents()

    assert "annual-leave-policy.md" in fixtures
    assert "年假" in fixtures["annual-leave-policy.md"]
    assert "申请" in fixtures["annual-leave-policy.md"]
    assert "internal-vpn-guide.md" in fixtures
    assert "VPN" in fixtures["internal-vpn-guide.md"]
    assert "expense-policy.md" in fixtures
    assert "发票" in fixtures["expense-policy.md"]
    assert "报销" in fixtures["expense-policy.md"]
