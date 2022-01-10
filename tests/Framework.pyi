# this file is needed so that tox -e lint does not complain about:
# tests/Requester.py:63: error: Incompatible types in assignment (expression has type "float", base class "BasicTestCase" defined the type as "None")
# tests/Requester.py:64: error: Incompatible types in assignment (expression has type "float", base class "BasicTestCase" defined the type as "None")

from typing import Optional

class RecordingConnection:
    ...

class RecordingHttpConnection:
    ...

class RecordingHttpsConnection:
    ...

class ReplayingConnection:
    ...

class ReplayingHttpConnection:
    ...

class ReplayingHttpsConnection:
    ...

class BasicTestCase:
    seconds_between_requests: Optional[float] = ...
    seconds_between_writes: Optional[float] = ...

class TestCase:
    ...
