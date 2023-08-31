import github
from github.GithubObject import NotSet, is_defined, is_undefined

from . import Framework


class Lazy(Framework.TestCase):
    def testLazyMainClassRepo(self):
        test_instances = [
            lambda repo, lazy: repo.get_artifact(1234, lazy=lazy),
            lambda repo, lazy: repo.get_branch("main", lazy=lazy),
            lambda repo, lazy: repo.get_check_run(1234, lazy=lazy),
            lambda repo, lazy: repo.get_check_suite(1234, lazy=lazy),
            lambda repo, lazy: repo.get_comment(1234, lazy=lazy),
            lambda repo, lazy: repo.get_commit("SHA", lazy=lazy),
            lambda repo, lazy: repo.get_deployment(1234, lazy=lazy),
            lambda repo, lazy: repo.get_download(1234, lazy=lazy),
            lambda repo, lazy: repo.get_git_blob("SHA", lazy=lazy),
            lambda repo, lazy: repo.get_git_commit("SHA", lazy=lazy),
            lambda repo, lazy: repo.get_git_ref("SHA", lazy=lazy),
            lambda repo, lazy: repo.get_git_tag("tag", lazy=lazy),
            lambda repo, lazy: repo.get_hook(1234, lazy=lazy),
            lambda repo, lazy: repo.get_issue(1234, lazy=lazy),
            lambda repo, lazy: repo.get_issues_event(1234, lazy=lazy),
            lambda repo, lazy: repo.get_key(1234, lazy=lazy),
            lambda repo, lazy: repo.get_label("label", lazy=lazy),
            lambda repo, lazy: repo.get_milestone(1234, lazy=lazy),
            lambda repo, lazy: repo.get_pull(1234, lazy=lazy),
        ]

        # non-transitive lazy objects
        g = github.Github()
        repo = g.get_repo("PyGithub/PyGithub", lazy=True)
        self.assertFalse(repo._CompletableGithubObject__completed)
        self.assertTrue(is_undefined(repo._CompletableGithubObject__transitiveLazy))

        with self.subTest(transitive_lazy=False):
            for func in test_instances:
                instance = func(repo, lazy=True)
                with self.subTest(object_type=instance.__class__.__name__):
                    self.assertFalse(instance._CompletableGithubObject__completed)
                    self.assertTrue(is_undefined(instance._CompletableGithubObject__transitiveLazy))

        # transitive lazy objects
        g = github.Github(lazy=True)
        repo = g.get_repo("PyGithub/PyGithub")
        self.assertFalse(repo._CompletableGithubObject__completed)
        self.assertTrue(is_defined(repo._CompletableGithubObject__transitiveLazy))
        self.assertTrue(repo._CompletableGithubObject__transitiveLazy)

        with self.subTest(transitive_lazy=True):
            for func in test_instances:
                instance = func(repo, lazy=NotSet)
                with self.subTest(object_type=instance.__class__.__name__):
                    self.assertFalse(instance._CompletableGithubObject__completed)
                    self.assertTrue(is_defined(instance._CompletableGithubObject__transitiveLazy))
                    self.assertTrue(instance._CompletableGithubObject__transitiveLazy)
