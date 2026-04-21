import subprocess
from pathlib import Path
from .proc import run_async
from .log import dbg, inf
from dataclasses import dataclass, field


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

        return ret
    
    async def set_remote(self, url, name="origin"):
        """
        Ensure the named remote is configured with the given URL.
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

    def __init__(self, repo_dir: Path, *, git_bin=None):
        self.repo_dir = repo_dir
        self.git_bin = git_bin or "git"

    async def run(self, args, **kwargs):
        return await run_async(
            [self.git_bin, *(str(it) for it in args)],
            cwd=self.repo_dir,
            **kwargs
        )

    @property
    def remotes(self) -> Remotes:
        return Remotes(self)

    async def init(self):
        await self.run(["init", "."])
    
    async def checkout(self, branch):
        await self.run(["checkout", branch])

    async def fetch_light(self, refspec, remote="origin"):
        """
        Fetch given <refspec> from a remote repository without blobs.
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
