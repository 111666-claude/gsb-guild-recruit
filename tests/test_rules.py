"""等级条件、名额上限、申请幂等、过期清理与查询代价的用例。"""
import unittest

from recruit.core import EXPIRE_MS, Recruit


class LevelRuleTest(unittest.TestCase):
    def test_low_level_rejected(self):
        book = Recruit(min_level=10)
        self.assertFalse(book.apply("a-1", "p", 9, 0))

    def test_low_level_does_not_enter_queue_or_use_quota(self):
        book = Recruit(quota=1, min_level=10)
        book.apply("low", "p", 5, 0)
        self.assertEqual(book.pending(0), 0)
        self.assertTrue(book.apply("a-1", "q", 10, 0))
        self.assertTrue(book.accept("a-1"))

    def test_boundary_level_accepted(self):
        self.assertTrue(Recruit(min_level=10).apply("a-1", "p", 10, 0))


class QuotaRuleTest(unittest.TestCase):
    def test_accept_fails_when_quota_full(self):
        book = Recruit(quota=1)
        book.apply("a-1", "p", 50, 0)
        self.assertTrue(book.accept("a-1"))
        book.apply("a-2", "q", 50, 10)
        self.assertFalse(book.accept("a-2"))

    def test_accept_removes_application(self):
        book = Recruit(quota=2)
        book.apply("a-1", "p", 50, 0)
        self.assertTrue(book.accept("a-1"))
        self.assertEqual(book.pending(0), 0)

    def test_accept_is_not_repeatable(self):
        book = Recruit(quota=2)
        book.apply("a-1", "p", 50, 0)
        self.assertTrue(book.accept("a-1"))
        self.assertFalse(book.accept("a-1"))
        self.assertEqual(book.members, 1)

    def test_accept_missing_returns_false(self):
        self.assertFalse(Recruit().accept("missing"))

    def test_members_never_exceed_quota(self):
        book = Recruit(quota=3)
        for i in range(10):
            book.apply("a-%d" % i, "p", 50, i)
        accepted = sum(1 for i in range(10) if book.accept("a-%d" % i))
        self.assertEqual(accepted, 3)
        self.assertEqual(book.members, 3)


class IdempotencyRuleTest(unittest.TestCase):
    def test_duplicate_apply_keeps_one(self):
        book = Recruit()
        self.assertTrue(book.apply("a-1", "p", 50, 0))
        self.assertFalse(book.apply("a-1", "p", 50, 10))
        self.assertEqual(book.pending(10), 1)

    def test_duplicate_rejected_even_with_different_payload(self):
        book = Recruit()
        book.apply("a-1", "p", 50, 0)
        self.assertFalse(book.apply("a-1", "r", 99, 10))
        self.assertEqual(book.pending(10), 1)

    def test_reapply_after_accept_is_new_application(self):
        book = Recruit(quota=2)
        book.apply("a-1", "p", 50, 0)
        self.assertTrue(book.accept("a-1"))
        self.assertTrue(book.apply("a-1", "p", 50, 10))
        self.assertEqual(book.pending(10), 1)


class ExpiryRuleTest(unittest.TestCase):
    def test_expired_application_is_not_pending(self):
        book = Recruit()
        book.apply("a-1", "p", 50, 0)
        self.assertEqual(book.pending(EXPIRE_MS + 1), 0)

    def test_boundary_age_still_pending(self):
        book = Recruit()
        book.apply("a-1", "p", 50, 0)
        self.assertEqual(book.pending(EXPIRE_MS), 1)

    def test_only_expired_removed(self):
        book = Recruit(expire_ms=100)
        book.apply("a-1", "p", 50, 0)
        book.apply("a-2", "p", 50, 50)
        self.assertEqual(book.pending(101), 1)
        self.assertFalse(book.accept("a-1"))
        self.assertTrue(book.accept("a-2"))

    def test_reapply_after_expiry_allowed(self):
        book = Recruit(expire_ms=100)
        book.apply("a-1", "p", 50, 0)
        self.assertEqual(book.pending(101), 0)
        self.assertTrue(book.apply("a-1", "p", 50, 101))
        self.assertEqual(book.pending(101), 1)


class ScanCostTest(unittest.TestCase):
    def test_pending_does_not_full_scan_without_expiry(self):
        book = Recruit()
        for i in range(10000):
            book.apply("a-%d" % i, "p", 50, i)
        before = book.scanned_count()
        for _ in range(100):
            self.assertEqual(book.pending(10000), 10000)
        self.assertEqual(book.scanned_count() - before, 0)

    def test_sweep_is_amortized_constant(self):
        book = Recruit(expire_ms=100)
        for i in range(10000):
            book.apply("a-%d" % i, "p", 50, 0)
        before = book.scanned_count()
        self.assertEqual(book.pending(50), 10000)
        self.assertEqual(book.scanned_count() - before, 0)
        self.assertEqual(book.pending(101), 0)
        scanned_for_expiry = book.scanned_count() - before
        self.assertEqual(scanned_for_expiry, 10000)
        before = book.scanned_count()
        for t in (200, 300, 400):
            self.assertEqual(book.pending(t), 0)
        self.assertEqual(book.scanned_count() - before, 0)


if __name__ == "__main__":
    unittest.main()
