import pytest
from .common import make_git_repo
from kotkotool.git import GitRepository


@pytest.fixture(scope="module")
def git_repo_dir(tmp_path_factory) -> str:
    tmpdir = tmp_path_factory.mktemp("git-repo")
    return make_git_repo(tmpdir, "pyproj-in-git").resolve()


async def test_get_commit_hash(git_repo_dir: str):
    """Test building a package from a git repository source.
    """

    repo = GitRepository(git_repo_dir)

    commit_hash = await repo.get_commit_hash()
    assert len(commit_hash) == 40  # commit hash should be 40 characters long


async def test_has_commit(git_repo_dir: str):
    repo = GitRepository(git_repo_dir)
    commit_hash = await repo.get_commit_hash()

    assert (await repo.has_commit(commit_hash)) is True
    assert (await repo.has_commit("master")) is True

    assert (await repo.has_commit(f"{commit_hash}1")) is False
    assert (await repo.has_commit("not-existing-refspec")) is False


async def test_git_remotes(tmp_path):
    """
    Test getting and setting git remotes.
    """

    URL1 = "https://example.com/repo-1.git"
    URL2 = "https://example.com/repo-2.git"

    repo = await GitRepository.init(tmp_path)

    # no remotes by default
    assert (await repo.remotes.get_remotes()) == {}

    # add remote and check
    await repo.remotes.set_remote(URL1)

    remotes = await repo.remotes.get_remotes()
    assert len(remotes) == 1
    assert URL1 in remotes["origin"]

    # change remote URL and check
    await repo.remotes.set_remote(URL2)

    remotes = await repo.remotes.get_remotes()
    assert len(remotes) == 1
    assert URL2 in remotes["origin"]


async def test_clone_git_repository(git_repo_dir: str, tmp_path):
    """Test cloning a git repository from a URL with a commit hash.
    """

    url = f"file://{git_repo_dir}"
    dest_dir = tmp_path / "git-repo-clone"

    repo = await GitRepository.clone(url, dest_dir)

    assert repo.repo_dir.exists()
    await repo.get_commit_hash()  # no exception means the repository is valid


async def test_ensure_repo__already_exists(git_repo_dir: str):
    head_commit = await GitRepository(git_repo_dir).get_commit_hash()

    repo = await GitRepository.ensure_repo(git_repo_dir)
    assert (await repo.get_commit_hash()) == head_commit


async def test_ensure_repo__init_new(tmp_path):
    repo_dir = tmp_path / "new-repo"
    repo = await GitRepository.ensure_repo(repo_dir, initial_branch="master")

    assert repo.repo_dir.exists()



async def test_ensure_git_repository(git_repo_dir: str, tmp_path):
    url = f"file://{git_repo_dir}"
    dest_dir = tmp_path / "a-repo"

    remote_head_commit = await GitRepository(git_repo_dir).get_commit_hash()

    repo = await GitRepository.ensure_repo(dest_dir, origin=url)
    repo = await GitRepository.ensure_repo(dest_dir, origin=url)

    assert repo.repo_dir.exists()
    assert url in (await repo.remotes.get_remotes())["origin"]

    await repo.pull("origin", "master")
    assert (await repo.get_commit_hash()) == remote_head_commit
