import unittest
from datetime import datetime, timedelta, timezone

from admissions import can_submit


class ExistingCoverage(unittest.TestCase):
    def test_before_deadline_allowed(self):
        deadline = datetime(2030, 1, 1, tzinfo=timezone.utc)
        self.assertTrue(can_submit(deadline - timedelta(seconds=1), deadline))
