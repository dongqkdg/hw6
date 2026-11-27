"""Temporary failure for the HW6 CI gate submission screenshot."""


def test_failed_test_prevents_build_and_deploy():
    assert False, "Intentional CI failure: build and deploy must be skipped"
