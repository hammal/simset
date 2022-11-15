import pytest


@pytest.fixture()
def dummy_fixture():
    return 1


def test_dummy(dummy_fixture):
    assert dummy_fixture == 1
