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
