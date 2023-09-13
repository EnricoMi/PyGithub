from typing import Callable

import github
from github.GithubObject import CompletableGithubObject, NotSet, Opt, is_defined, is_undefined

from . import Framework


class Lazy(Framework.TestCase):
    def assertLaziness(self, obj: CompletableGithubObject, tests, transitive_lazy: Opt[bool], lazy: Opt[bool]):
        self.assertIsInstance(obj, CompletableGithubObject)

        is_lazy = lazy is True or is_undefined(lazy) and transitive_lazy is True
        self.assertEqual(not is_lazy, obj._CompletableGithubObject__completed)

        if is_defined(transitive_lazy):
            self.assertTrue(is_defined(obj._CompletableGithubObject__transitiveLazy))
            self.assertEqual(transitive_lazy, obj._CompletableGithubObject__transitiveLazy)
        else:
            self.assertTrue(is_undefined(obj._CompletableGithubObject__transitiveLazy))

        for func in tests:
            with self.subTest(lazy_child=True):
                instance = func(obj, True)
                with self.subTest(object_type=instance.__class__.__name__):
                    self.assertLaziness(instance, [], transitive_lazy, True)

            # do not test any cases that actually access the API
            if transitive_lazy is True:
                with self.subTest(lazy_child=NotSet):
                    instance = func(obj, NotSet)
                    with self.subTest(object_type=instance.__class__.__name__):
                        self.assertLaziness(instance, [], transitive_lazy, NotSet)

    def doTestLazyObject(
        self,
        func: Callable[[github.Github, bool], CompletableGithubObject],
        tests: list[Callable[[CompletableGithubObject, bool], CompletableGithubObject]],
    ):
        for transitive_lazy in [NotSet, False, True]:
            for lazy in [NotSet, False, True]:
                # do not test any cases that actually access the API
                if lazy is True or is_undefined(lazy) and transitive_lazy is True:
                    with self.subTest(transitive_lazy=transitive_lazy, lazy=lazy):
                        g = github.Github(retry=None, lazy=transitive_lazy)
                        obj = func(g, lazy)
                        self.assertLaziness(obj, tests, transitive_lazy, lazy)

    def testLazyRepo(self):
        # fetches comment only
        self.assertEqual(
            "stale[bot]",
            github.Github(retry=None, lazy=True)
            .get_repo("PyGithub/PyGithub")
            .get_issue(1234)
            .get_comment(560146023)
            .user.login,
        )
        self.assertEqual(
            "stale[bot]",
            github.Github(retry=None)
            .get_repo("PyGithub/PyGithub", lazy=True)
            .get_issue(1234, lazy=True)
            .get_comment(560146023, lazy=True)
            .user.login,
        )

        # test laziness of these repo getters
        tests = [
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
        self.doTestLazyObject(lambda g, lazy: g.get_repo("PyGithub/PyGithub", lazy=lazy), tests)

    def testLazyUser(self):
        # fetches comment only
        self.assertEqual(
            "stale[bot]",
            github.Github(retry=None, lazy=True)
            .get_user("PyGithub")
            .get_repo("PyGithub")
            .get_issue(1234)
            .get_comment(560146023)
            .user.login,
        )
        self.assertEqual(
            "stale[bot]",
            github.Github(retry=None)
            .get_user("PyGithub", lazy=True)
            .get_repo("PyGithub", lazy=True)
            .get_issue(1234, lazy=True)
            .get_comment(560146023, lazy=True)
            .user.login,
        )

        # test laziness of these repo getters
        tests = [
            lambda user, lazy: user.get_repo("repo", lazy=lazy),
            lambda user, lazy: user.get_organization_membership("org", lazy=lazy),
        ]
        self.doTestLazyObject(lambda g, lazy: g.get_user("PyGithub", lazy=lazy), tests)
