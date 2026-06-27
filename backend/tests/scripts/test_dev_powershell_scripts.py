from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_ROOT = PROJECT_ROOT / "scripts"


def test_dev_powershell_scripts_exist() -> None:
    expected = {
        "start-enterprisemind.ps1",
        "stop-enterprisemind.ps1",
        "check-enterprisemind.ps1",
        "test-enterprisemind.ps1",
    }

    actual = {
        path.name
        for path in SCRIPT_ROOT.glob("*.ps1")
    }

    assert expected <= actual


def test_dev_powershell_scripts_do_not_contain_destructive_reset_commands() -> None:
    forbidden = [
        "docker volume rm",
        "docker compose down -v",
        "Remove-Item -Recurse",
        "DROP DATABASE",
        "TRUNCATE",
        "FLUSHALL",
    ]

    for path in SCRIPT_ROOT.glob("*.ps1"):
        content = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in content


def test_dev_powershell_scripts_do_not_print_env_file_content() -> None:
    forbidden = [
        "Get-Content backend\\.env",
        "Get-Content .env",
        "type backend\\.env",
        "type .env",
    ]

    for path in SCRIPT_ROOT.glob("*.ps1"):
        content = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in content


def test_start_script_runs_windows_compatible_worker_by_default() -> None:
    content = (
        SCRIPT_ROOT / "start-enterprisemind.ps1"
    ).read_text(encoding="utf-8")

    assert "[switch]$SkipWorker" in content
    assert "rq worker document_ingestion" in content
    assert "rq.worker.SimpleWorker" in content
    assert "python -m rq worker" not in content
