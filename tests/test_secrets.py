"""Secret fixtures are synthetic and contain no usable credential."""

from scripts.check_secrets import scan_text


def test_safe_text_passes() -> None:
    assert scan_text('password = os.environ["POSTGRES_PASSWORD"]') == []


def test_synthetic_secret_shapes_are_detected() -> None:
    fake_github_token = "ghp_" + "abcdefghij" * 4
    fake_aws_key = "AKIA" + "A1B2C3D4E5F6G7H8"
    fake_generic = 'AWS_SECRET_ACCESS_KEY = "' + "abcdef0123456789" + '"'
    fake_private_key_header = "-----BEGIN " + "PRIVATE KEY-----"

    labels = {
        label
        for _, label in scan_text(
            "\n".join(
                (
                    fake_github_token,
                    fake_aws_key,
                    fake_generic,
                    fake_private_key_header,
                )
            )
        )
    }
    assert labels == {
        "GitHub token",
        "AWS access key",
        "credential literal",
        "private key",
    }
