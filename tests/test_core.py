import unittest

from recruit.core import Recruit


class ApplyTest(unittest.TestCase):
    def test_apply_returns_true(self):
        self.assertTrue(Recruit().apply("a-1", "p", 50, 0))

    def test_pending_counts_application(self):
        book = Recruit()
        book.apply("a-1", "p", 50, 0)
        self.assertEqual(book.pending(0), 1)


class AcceptTest(unittest.TestCase):
    def test_accept_hits_application(self):
        book = Recruit()
        book.apply("a-1", "p", 50, 0)
        self.assertTrue(book.accept("a-1"))

    def test_accept_missing_returns_false(self):
        self.assertFalse(Recruit().accept("missing"))


if __name__ == "__main__":
    unittest.main()


class LevelTest(unittest.TestCase):
    def test_below_min_level_rejected(self):
        self.assertFalse(Recruit(min_level=10).apply("a-1", "p", 9, 0))

    def test_rejected_apply_not_queued(self):
        book = Recruit(min_level=10)
        book.apply("a-1", "p", 5, 0)
        self.assertEqual(book.pending(0), 0)
        self.assertFalse(book.accept("a-1"))

    def test_min_level_boundary_accepted(self):
        book = Recruit(min_level=10)
        self.assertTrue(book.apply("a-1", "p", 10, 0))
        self.assertEqual(book.pending(0), 1)


class QuotaTest(unittest.TestCase):
    def test_accept_fails_when_quota_full(self):
        book = Recruit(quota=1)
        book.apply("a-1", "p", 50, 0)
        book.apply("a-2", "q", 50, 0)
        self.assertTrue(book.accept("a-1"))
        self.assertFalse(book.accept("a-2"))

    def test_accepted_application_leaves_queue(self):
        book = Recruit()
        book.apply("a-1", "p", 50, 0)
        book.accept("a-1")
        self.assertEqual(book.pending(0), 0)

    def test_accept_not_idempotent_twice(self):
        book = Recruit()
        book.apply("a-1", "p", 50, 0)
        self.assertTrue(book.accept("a-1"))
        self.assertFalse(book.accept("a-1"))
        self.assertEqual(book.members, 1)


class DupTest(unittest.TestCase):
    def test_duplicate_apply_id_keeps_one(self):
        book = Recruit()
        self.assertTrue(book.apply("a-1", "p", 50, 0))
        self.assertFalse(book.apply("a-1", "p", 50, 10))
        self.assertEqual(book.pending(10), 1)

    def test_reapply_after_expiry_allowed(self):
        book = Recruit(expire_ms=100)
        book.apply("a-1", "p", 50, 0)
        self.assertTrue(book.apply("a-1", "p", 50, 200))
        self.assertEqual(book.pending(200), 1)


class ExpireTest(unittest.TestCase):
    def test_expired_not_counted(self):
        book = Recruit(expire_ms=100)
        book.apply("a-1", "p", 50, 0)
        self.assertEqual(book.pending(100), 0)

    def test_fresh_before_deadline(self):
        book = Recruit(expire_ms=100)
        book.apply("a-1", "p", 50, 0)
        self.assertEqual(book.pending(99), 1)

    def test_expired_cannot_be_accepted(self):
        book = Recruit(expire_ms=100)
        book.apply("a-1", "p", 50, 0)
        self.assertFalse(book.accept("a-1", now_ms=150))
        self.assertEqual(book.members, 0)

    def test_pending_only_counts_waiting(self):
        book = Recruit(expire_ms=100)
        book.apply("a-1", "p", 50, 0)
        book.apply("a-2", "q", 50, 90)
        self.assertEqual(book.pending(150), 1)


class ScannedTest(unittest.TestCase):
    def test_pending_queries_do_not_rescan(self):
        book = Recruit(expire_ms=10**9)
        for i in range(10000):
            book.apply("a-%d" % i, "p", 50, 0)
        for t in range(1000):
            self.assertEqual(book.pending(t), 10000)
        self.assertEqual(book.scanned_count(), 0)

    def test_expiry_purge_is_amortized(self):
        book = Recruit(expire_ms=100)
        for i in range(10000):
            book.apply("a-%d" % i, "p", 50, i % 50)
        book.pending(1000)
        self.assertEqual(book.scanned_count(), 10000)
        book.pending(2000)
        self.assertEqual(book.scanned_count(), 10000)


class ScaleTest(unittest.TestCase):
    def test_half_million_applies_throughput(self):
        import time

        book = Recruit(quota=10**9, min_level=1, expire_ms=10**18)
        count = 500000
        start = time.perf_counter()
        for i in range(count):
            book.apply(i, i, 10, i)
            book.pending(i)
        elapsed = time.perf_counter() - start
        self.assertEqual(book.pending(count), count)
        self.assertGreater(2 * count / elapsed, 100000)


class RefRecruit:
    """参考实现：条件筛选 + 名额 + 幂等 + 过期，朴素全扫。"""

    def __init__(self, quota, min_level, expire_ms):
        self.quota = quota
        self.min_level = min_level
        self.expire_ms = expire_ms
        self.members = 0
        self.apps = []

    def _purge(self, now_ms):
        self.apps = [a for a in self.apps if now_ms - a[3] < self.expire_ms]

    def apply(self, apply_id, player, level, now_ms):
        self._purge(now_ms)
        if level < self.min_level:
            return False
        if any(a[0] == apply_id for a in self.apps):
            return False
        self.apps.append((apply_id, player, level, now_ms))
        return True

    def accept(self, apply_id, now_ms):
        self._purge(now_ms)
        if self.members >= self.quota:
            return False
        for i, a in enumerate(self.apps):
            if a[0] == apply_id:
                del self.apps[i]
                self.members += 1
                return True
        return False

    def pending(self, now_ms):
        self._purge(now_ms)
        return len(self.apps)


class DifferentialTest(unittest.TestCase):
    def test_matches_reference_on_random_sequences(self):
        import random

        rng = random.Random(20261001)
        for case in range(200):
            quota = rng.randint(1, 5)
            min_level = rng.randint(1, 50)
            expire_ms = rng.randint(10, 100)
            real = Recruit(quota=quota, min_level=min_level, expire_ms=expire_ms)
            ref = RefRecruit(quota, min_level, expire_ms)
            now = 0
            for step in range(200):
                now += rng.randint(0, 150)
                op = rng.random()
                if op < 0.55:
                    apply_id = "a-%d" % rng.randint(0, 15)
                    level = rng.randint(0, 60)
                    got = real.apply(apply_id, "p", level, now)
                    want = ref.apply(apply_id, "p", level, now)
                elif op < 0.85:
                    apply_id = "a-%d" % rng.randint(0, 15)
                    got = real.accept(apply_id, now_ms=now)
                    want = ref.accept(apply_id, now)
                else:
                    got = real.pending(now)
                    want = ref.pending(now)
                self.assertEqual(got, want, "case %d step %d" % (case, step))
                self.assertEqual(real.members, ref.members, "case %d step %d" % (case, step))
                self.assertEqual(real.pending(now), ref.pending(now), "case %d step %d" % (case, step))


if __name__ == "__main__":
    unittest.main()
