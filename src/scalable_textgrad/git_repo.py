"""Utilities on top of GitPython."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterable, Optional

from git import Repo


class GitRepository:
    """High-level wrapper around a git repository."""

    def __init__(self, repo: Repo) -> None:
        self.repo = repo

    @property
    def worktree(self) -> Path:
        assert self.repo.working_tree_dir is not None
        return Path(self.repo.working_tree_dir)

    @classmethod
    def open(cls, path: Path) -> "GitRepository":
        if not (path / ".git").exists():
            repo = Repo.init(path)
        else:
            repo = Repo(path)
        return cls(repo)

    def is_clean(self) -> bool:
        return not self.repo.is_dirty(untracked_files=True)

    def commit_all(self, message: str, paths: Optional[Iterable[str]] = None) -> str:
        if paths:
            self.repo.index.add(list(paths))
        else:
            self.repo.git.add(A=True)
        if self.repo.is_dirty(index=True, working_tree=True, untracked_files=True):
            commit = self.repo.index.commit(message)
            return commit.hexsha
        return self.head

    def tag(self, version: str) -> None:
        if version in {tag.name for tag in self.repo.tags}:
            self.repo.delete_tag(version)
        self.repo.create_tag(version)

    def checkout_detached(self, commit_hash: str) -> None:
        self.repo.git.checkout(commit_hash)

    def clone_to(self, destination: Path) -> "GitRepository":
        if destination.exists():
            shutil.rmtree(destination)
        repo = self.repo.clone(destination)
        return GitRepository(repo)

    @property
    def head(self) -> str:
        return self.repo.head.commit.hexsha

    def list_commits(self, limit: int = 50) -> list[dict[str, str]]:
        commits = []
        for commit in self.repo.iter_commits(max_count=limit):
            commits.append({"hash": commit.hexsha, "message": commit.message.strip()})
        return commits
