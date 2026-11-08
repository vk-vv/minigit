"""Tests for what ``minigit status`` prints."""

import io

from minigit.cli import main
from minigit.refs import head_commit, set_head


class _FakeTTY(io.StringIO):
    """Minimal stdout stand-in that pretends to be a terminal."""

    def isatty(self) -> bool:
        return True


def test_clean_repository(repo, run, write):
    write("a.txt", "a\n")
    run("add", "a.txt")
    run("commit", "-m", "first")
    result = run("status")
    assert result.code == 0
    assert result.out == "On branch main\nnothing to commit, working tree clean\n"


def test_empty_repository_says_no_commits_yet(repo, run):
    out = run("status").out
    assert out.startswith("On branch main\n\nNo commits yet\n")
    assert "nothing to commit, working tree clean" in out


def test_staged_section(repo, run, write):
    write("notes.txt", "n\n")
    run("add", "notes.txt")
    out = run("status").out
    assert "Changes to be committed:" in out
    assert "\tnew file:   notes.txt" in out


def test_all_three_sections(repo, run, write):
    write("hello.txt", "hello\n")
    write("old.txt", "old\n")
    run("add", "hello.txt", "old.txt")
    run("commit", "-m", "first")

    write("hello.txt", "staged edit\n")
    run("add", "hello.txt")
    write("hello.txt", "unstaged edit\n")
    (repo.worktree / "old.txt").unlink()
    write("scratch.py", "print(1)\n")

    out = run("status").out
    assert "\tmodified:   hello.txt" in out
    assert "\tdeleted:    old.txt" in out
    assert "\tscratch.py" in out
    assert out.index("Changes to be committed:") < out.index("Changes not staged for commit:")
    assert out.index("Changes not staged for commit:") < out.index("Untracked files:")


def test_detached_head(repo, run, write):
    write("a.txt", "a\n")
    run("add", "a.txt")
    run("commit", "-m", "first")
    commit = head_commit(repo)
    set_head(repo, commit, symbolic=False)
    assert run("status").out.startswith(f"HEAD detached at {commit[:7]}")


def test_status_colors_when_tty(repo, write, monkeypatch):
    write("hello.txt", "hello\n")
    write("old.txt", "old\n")
    main(["add", "hello.txt", "old.txt"])
    main(["commit", "-m", "first"])

    write("hello.txt", "staged edit\n")
    main(["add", "hello.txt"])
    write("hello.txt", "unstaged edit\n")
    (repo.worktree / "old.txt").unlink()
    write("scratch.py", "print(1)\n")

    monkeypatch.delenv("NO_COLOR", raising=False)
    fake = _FakeTTY()
    monkeypatch.setattr("sys.stdout", fake)
    main(["status"])
    out = fake.getvalue()

    assert "\t\033[32mmodified:   hello.txt\033[0m" in out
    assert "\t\033[31mdeleted:    old.txt\033[0m" in out
    assert "\t\033[31mmodified:   hello.txt\033[0m" in out
    assert "\t\033[31mscratch.py\033[0m" in out


def test_status_detached_head_color_when_tty(repo, write, monkeypatch):
    write("a.txt", "a\n")
    main(["add", "a.txt"])
    main(["commit", "-m", "first"])
    commit = head_commit(repo)
    set_head(repo, commit, symbolic=False)

    monkeypatch.delenv("NO_COLOR", raising=False)
    fake = _FakeTTY()
    monkeypatch.setattr("sys.stdout", fake)
    main(["status"])
    out = fake.getvalue()

    assert out.startswith(f"\033[31mHEAD detached at \033[0m{commit[:7]}")


def test_status_no_color_flag_suppresses_color(repo, write, monkeypatch):
    write("hello.txt", "hello\n")
    main(["add", "hello.txt"])

    monkeypatch.delenv("NO_COLOR", raising=False)
    fake = _FakeTTY()
    monkeypatch.setattr("sys.stdout", fake)
    main(["--no-color", "status"])
    out = fake.getvalue()

    assert "\033[" not in out
    assert "\tnew file:   hello.txt" in out


def test_status_no_color_env_suppresses_color(repo, write, monkeypatch):
    write("hello.txt", "hello\n")
    main(["add", "hello.txt"])

    monkeypatch.setenv("NO_COLOR", "1")
    fake = _FakeTTY()
    monkeypatch.setattr("sys.stdout", fake)
    main(["status"])
    out = fake.getvalue()

    assert "\033[" not in out
    assert "\tnew file:   hello.txt" in out
