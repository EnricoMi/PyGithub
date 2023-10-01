from __future__ import annotations

from typing import Callable

import github
from github.GithubObject import CompletableGithubObject, NotSet, Opt
from . import Framework


class Lazy(Framework.TestCase):
    def assertLaziness(self, obj: CompletableGithubObject, tests):
        self.assertIsInstance(obj, CompletableGithubObject)
        self.assertEqual(False, obj.completed)

        for func in tests:
            instance = func(obj)
            with self.subTest(object_type=instance.__class__.__name__):
                self.assertLaziness(instance, [])

    def doTestLazyObject(
        self,
        func: Callable[[github.Github], CompletableGithubObject],
        tests: list[Callable[[CompletableGithubObject], CompletableGithubObject]],
    ):
        g = github.Github(retry=None, lazy=True)
        obj = func(g)
        self.assertLaziness(obj, tests)

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

        # test laziness of these repo getters
        tests = [
            lambda repo: repo.get_artifact(1234),
            lambda repo: repo.get_branch("main"),
            lambda repo: repo.get_check_run(1234),
            lambda repo: repo.get_check_suite(1234),
            lambda repo: repo.get_comment(1234),
            lambda repo: repo.get_commit("SHA"),
            lambda repo: repo.get_deployment(1234),
            lambda repo: repo.get_download(1234),
            lambda repo: repo.get_git_blob("SHA"),
            lambda repo: repo.get_git_commit("SHA"),
            lambda repo: repo.get_git_ref("SHA"),
            lambda repo: repo.get_git_tag("tag"),
            lambda repo: repo.get_hook(1234),
            lambda repo: repo.get_issue(1234),
            lambda repo: repo.get_issues_event(1234),
            lambda repo: repo.get_key(1234),
            lambda repo: repo.get_label("label"),
            lambda repo: repo.get_milestone(1234),
            lambda repo: repo.get_pull(1234),
        ]
        self.doTestLazyObject(lambda g: g.get_repo("PyGithub/PyGithub"), tests)
