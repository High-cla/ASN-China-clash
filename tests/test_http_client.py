import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from http_client import RETRYABLE_STATUS_CODES, build_session  # noqa: E402


def test_get_retry_policy():
    session = build_session()
    try:
        adapter = session.get_adapter("https://")
        retry = adapter.max_retries
        assert retry.total == 3
        assert retry.connect == 3
        assert retry.read == 3
        assert retry.status == 3
        assert retry.backoff_factor == 0.5
        assert "GET" in retry.allowed_methods
        assert set(RETRYABLE_STATUS_CODES).issubset(retry.status_forcelist)
        assert retry.respect_retry_after_header is True
    finally:
        session.close()


if __name__ == "__main__":
    test_get_retry_policy()
    print("http retry policy: ok")
