from typing import Callable

import github
from github.GithubObject import CompletableGithubObject, NotSet, Opt, is_defined, is_undefined

from . import Framework


class Lazy(Framework.TestCase):
    def assertLaziness(self, obj: CompletableGithubObject, tests, sticky_lazy: Opt[bool], lazy: Opt[bool]):
        self.assertIsInstance(obj, CompletableGithubObject)

        is_lazy = lazy is True or is_undefined(lazy) and sticky_lazy is True
        self.assertEqual(not is_lazy, obj.completed)

        if is_defined(sticky_lazy):
            self.assertTrue(is_defined(obj.sticky_lazy))
            self.assertEqual(sticky_lazy, obj.sticky_lazy)
        else:
            self.assertTrue(is_undefined(obj.sticky_lazy))

        for func in tests:
            with self.subTest(sticky_lazy=True):
                instance = func(obj, True)
                with self.subTest(object_type=instance.__class__.__name__):
                    self.assertLaziness(instance, [], sticky_lazy, True)

            # do not test any cases that actually access the API
            if sticky_lazy is True:
                with self.subTest(sticky_lazy=NotSet):
                    instance = func(obj, NotSet)
                    with self.subTest(object_type=instance.__class__.__name__):
                        self.assertLaziness(instance, [], sticky_lazy, NotSet)

    def doTestLazyObject(
        self,
        func: Callable[[github.Github, bool], CompletableGithubObject],
        tests: list[Callable[[CompletableGithubObject, bool], CompletableGithubObject]],
    ):
        for sticky_lazy in [NotSet, False, True]:
            for lazy in [NotSet, False, True]:
                # do not test any cases that actually access the API
                if lazy is True or is_undefined(lazy) and sticky_lazy is True:
                    with self.subTest(sticky_lazy=sticky_lazy, lazy=lazy):
                        g = github.Github(retry=None, lazy=sticky_lazy)
                        obj = func(g, lazy)
                        self.assertLaziness(obj, tests, sticky_lazy, lazy)

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
            .get_comment(560146023)
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
