############################ Copyrights and license ############################
#                                                                              #
# Copyright 2024 Pasha Fateev <pasha@autokitteh.com>                           #
# Copyright 2025 Enrico Minack <github@enrico.minack.dev>                      #
#                                                                              #
# This file is part of PyGithub.                                               #
# http://pygithub.readthedocs.io/                                              #
#                                                                              #
# PyGithub is free software: you can redistribute it and/or modify it under    #
# the terms of the GNU Lesser General Public License as published by the Free  #
# Software Foundation, either version 3 of the License, or (at your option)    #
# any later version.                                                           #
#                                                                              #
# PyGithub is distributed in the hope that it will be useful, but WITHOUT ANY  #
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS    #
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more #
# details.                                                                     #
#                                                                              #
# You should have received a copy of the GNU Lesser General Public License     #
# along with PyGithub. If not, see <http://www.gnu.org/licenses/>.             #
#                                                                              #
################################################################################

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Any

import github.CopilotSeat
from github.GithubObject import Attribute, NonCompletableGithubObject, NotSet
from github.PaginatedList import PaginatedList

if TYPE_CHECKING:
    from github.CopilotSeat import CopilotSeat
    from github.Requester import Requester


class Copilot(NonCompletableGithubObject, ABC):
    """
    This class represents Copilot.

    Such objects do not exist in the Github API, so this class merely collects all endpoints the start with
    /{copilot_base_url}/copilot. There are specific implementations for Organization, Team and Enterprise
    for the different {copilot_base_url} urls.

    See methods below for specific endpoints and docs.
    https://docs.github.com/en/rest/copilot/copilot-metrics?apiVersion=2022-11-28
    https://docs.github.com/en/rest/copilot/copilot-usage?apiVersion=2022-11-28
    https://docs.github.com/en/rest/copilot/copilot-user-management?apiVersion=2022-11-28
    https://docs.github.com/en/enterprise-cloud@latest/rest/enterprise-admin?apiVersion=2022-11-28
    """

    def __init__(self, requester: Requester, parent_url: str) -> None:
        super().__init__(requester, {}, {"copilot_base_url": f"{parent_url}/copilot"})

    def _initAttributes(self) -> None:
        self._copilot_base_url: Attribute[str] = NotSet

    def __repr__(self) -> str:
        return self.get__repr__({"copilot_base_url": self._copilot_base_url.value})

    @property
    def copilot_base_url(self) -> str:
        return self._copilot_base_url.value

    def get_seats(self) -> PaginatedList[CopilotSeat]:
        """
        :calls: `GET {copilot_base_url}/billing/seats <https://docs.github.com/en/rest/copilot/copilot-business>`_
        """
        url = f"{self.copilot_base_url}/billing/seats"
        return PaginatedList(
            github.CopilotSeat.CopilotSeat,
            self._requester,
            url,
            None,
            list_item="seats",
            total_count_item="total_seats"
        )

    def add_seats(self, selected_usernames: list[str]) -> int:
        """
        :calls: `POST {copilot_base_url}/billing/selected_users <https://docs.github.com/en/rest/copilot/copilot-business>`_
        :param selected_usernames: List of usernames to add Copilot seats for
        :rtype: int
        :return: Number of seats created
        """
        url = f"{self.copilot_base_url}/billing/selected_users"
        _, data = self._requester.requestJsonAndCheck(
            "POST",
            url,
            input={"selected_usernames": selected_usernames},
        )
        return data["seats_created"]

    def remove_seats(self, selected_usernames: list[str]) -> int:
        """
        :calls: `DELETE {copilot_base_url}/billing/selected_users <https://docs.github.com/en/rest/copilot/copilot-business>`_
        :param selected_usernames: List of usernames to remove Copilot seats for
        :rtype: int
        :return: Number of seats cancelled
        """
        url = f"{self.copilot_base_url}/billing/selected_users"
        _, data = self._requester.requestJsonAndCheck(
            "DELETE",
            url,
            input={"selected_usernames": selected_usernames},
        )
        return data["seats_cancelled"]

    def _useAttributes(self, attributes: dict[str, Any]) -> None:
        if "copilot_base_url" in attributes:  # pragma no branch
            self._copilot_base_url = self._makeStringAttribute(attributes["copilot_base_url"])
