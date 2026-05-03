from spring_spring_hackathon import __version__


def test_version_is_nonempty() -> None:
    assert isinstance(__version__, str) and __version__
