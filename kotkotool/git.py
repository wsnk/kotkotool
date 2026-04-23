import subprocess
from pathlib import Path
from .proc import run_async, run_many_tasks
from .log import dbg, inf
from dataclasses import dataclass, field
from typing import Literal


def parse_remotes(output: str):
    # origin  https://github.com/FFmpeg/FFmpeg.git (fetch) [blob:none]
    # origin  https://github.com/FFmpeg/FFmpeg.git (push)
    for ln in output.splitlines():
        if not ln:
            continue
        name, url, mode = ln.split(maxsplit=2)
        yield (name, url, mode)


RemoteUrlT = tuple[str, str]  # URL, mode


@dataclass(kw_only=True)
class RemoteRepository:
    name: str
    urls: list[RemoteUrlT] = field(default_factory=list)

    def __contains__(self, url: str) -> bool:
        """Return if the remote has the given URL configured.
        """
        for it in self.urls:
            if it[0] == url:
                return True
        return False

    def has_url(self, url: str) -> bool:
        # FIXME
        for it in self.urls:
            if it[0] == url:
                return True
        return False


class Remotes:
    def __init__(self, git_repo: 'GitRepository'):
        self.git_repo = git_repo

    async def get_remotes(self) -> dict[str, RemoteRepository]:
        proc = await self.git_repo.run(["remote", "-v"], stdout=subprocess.PIPE, text=True)
        
        ret: dict[str, RemoteRepository] = {}
        for (name, url, mode) in parse_remotes(proc.stdout):
            rr = ret.setdefault(name, RemoteRepository(name=name))
            rr.urls.append((url, mode))
            dbg("Remote found: name='%s', URL='%s', mode='%s'", name, url, mode)

        return ret
    
    async def set_remote(self, url, name="origin"):
        """
        Ensure the named remote is configured with the given URL.

        If a remote with the given name already exists but has a different URL, it will be removed
        and re-added with the new URL.
        """

        remotes = await self.get_remotes()
        r = remotes.get(name)
        if r is not None:
            if r.has_url(url):
                dbg("Remote already has the given URL: name='%s', URL='%s'", name, url)
                return

            dbg("Removing existing remote: name='%s', %s", name, r)
            await self.git_repo.run(["remote", "remove", name])

        dbg("Adding new remote: name='%s', URL='%s'...", name, url)
        await self.git_repo.run(["remote", "add", name, url])
        inf("New '%s' remote added", name)


class GitRepository:
    @classmethod
    async def clone(cls, url: str, dest_dir: Path, *, git_bin=None):
        if git_bin is None:
            git_bin = "git"

        dbg(f"Cloning repository: {url} into '{dest_dir}'")
        await run_async([git_bin, "clone", url, str(dest_dir)])
        return cls(dest_dir)

    @classmethod
    async def init(cls, dest_dir: Path, *, git_bin=None):
        """
        Initialize a new git repository in the given directory. If the directory does not exist, it
        will be created.
        """

        repo = cls(dest_dir, git_bin=git_bin)
        await repo.run(["init", "."])
        return repo

    @classmethod
    async def ensure_repo(cls, dest_dir: Path, *, initial_branch="master", origin=None):
        dest_dir.mkdir(parents=True, exist_ok=True)

        repo = cls(dest_dir)

        if not repo.is_repository():
            await repo.run(["init", "."])

        if origin is not None:
            await repo.remotes.set_remote(origin)

        return repo

    def __init__(self, repo_dir: str | Path, *, git_bin=None):
        self.repo_dir = Path(repo_dir)
        self.git_bin = git_bin or "git"

    async def run(self, args, **kwargs):
        args = tuple(str(it) for it in args if it is not None)
        return await run_async(
            [self.git_bin, *args],
            cwd=self.repo_dir,
            **kwargs
        )

    def is_repository(self) -> bool:
        return (self.repo_dir/".git").is_dir()

    @property
    def remotes(self) -> Remotes:
        return Remotes(self)

    async def has_commit(self, refspec) -> bool:
        """Return if the repository has/know the given refspec.
        """
        try:
            res = await self.run(
                ["cat-file", "-t", refspec],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True
            )
            return res.stdout.strip() == "commit"
        except subprocess.CalledProcessError:
            return False

    async def pull(self, remote=None, refspec=None):
        await self.run(["pull", remote, refspec])

    async def checkout(self, branch):
        await self.run(["checkout", branch])
    
    async def fetch(self, repository=None, refspec=None, *, all=False):
        """git-fetch - fetch refs from one or more remote repositories.
        """
        if all:
            await self.run(["fetch", "--all"])
        else:
            await self.run(["fetch", repository, refspec])

    async def fetch_light(self, refspec, remote="origin"):
        """Fetch given <refspec> from a remote repository without blobs.
        """
        await self.run([
            "fetch",
            "--depth", "1",
            "--filter=blob:none",
            remote,
            refspec
        ])

    async def get_commit_hash(self) -> str:
        result = await run_async(
            ["git", "rev-parse", "HEAD"],
            cwd=self.repo_dir,
            stdout=subprocess.PIPE,
            text=True
        )
        return result.stdout.strip()
