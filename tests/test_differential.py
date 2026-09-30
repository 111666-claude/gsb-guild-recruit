"""随机序列对照：实现 vs 朴素参考模型，结果必须零差异。

参考模型按 README 口径用 O(n) 直白写法实现：
条件筛选（等级）+ 名额上限 + 申请幂等 + 过期清理。
"""
import random
import unittest

from recruit.core import Recruit


class RefRecruit:
    """朴素参考实现：每次全扫，语义以 README 口径为准。"""

    def __init__(self, quota, min_level, expire_ms):
        self.quota = quota
        self.min_level = min_level
        self.expire_ms = expire_ms
        self.members = 0
        self.apps = []

    def _sweep(self, now_ms):
        self.apps = [a for a in self.apps if now_ms - a[3] <= self.expire_ms]

    def apply(self, apply_id, player, level, now_ms):
        self._sweep(now_ms)
        if level < self.min_level:
            return False
        if any(a[0] == apply_id for a in self.apps):
            return False
        self.apps.append((apply_id, player, level, now_ms))
        return True

    def accept(self, apply_id):
        for i, a in enumerate(self.apps):
            if a[0] == apply_id:
                if self.members >= self.quota:
                    return False
                del self.apps[i]
                self.members += 1
                return True
        return False

    def pending(self, now_ms):
        self._sweep(now_ms)
        return len(self.apps)


def random_sequence(rng):
    """生成一条「申请 + 重复申请 + 接受 + 过期」混合序列。"""
    quota = rng.choice([1, 2, 3, 5])
    min_level = rng.choice([1, 10, 20])
    expire_ms = rng.choice([10, 100, 1000])
    ops = []
    now = 0
    ids = []
    fresh = 0
    for _ in range(rng.randint(20, 200)):
        now += rng.choice([0, 1, 5, expire_ms, expire_ms + 1, expire_ms * 3])
        kind = rng.random()
        if kind < 0.45:
            if ids and rng.random() < 0.4:
                apply_id = rng.choice(ids)
            else:
                apply_id = "a-%d" % fresh
                fresh += 1
                ids.append(apply_id)
            level = rng.randint(0, min_level + 5)
            ops.append(("apply", apply_id, "p%d" % fresh, level, now))
        elif kind < 0.75:
            if ids and rng.random() < 0.8:
                apply_id = rng.choice(ids)
            else:
                apply_id = "ghost-%d" % rng.randint(0, 5)
            ops.append(("accept", apply_id))
        else:
            ops.append(("pending", now))
    return quota, min_level, expire_ms, ops


def run_sequence(model_cls, quota, min_level, expire_ms, ops):
    book = model_cls(quota=quota, min_level=min_level, expire_ms=expire_ms)
    results = []
    last_now = 0
    for op in ops:
        if op[0] == "apply":
            results.append(book.apply(op[1], op[2], op[3], op[4]))
            last_now = op[4]
        elif op[0] == "accept":
            results.append(book.accept(op[1]))
        else:
            results.append(book.pending(op[1]))
            last_now = op[1]
    return results, book.members, book.pending(last_now)


class DifferentialTest(unittest.TestCase):
    def test_matches_reference_on_random_sequences(self):
        rng = random.Random(20261001)
        for case in range(200):
            quota, min_level, expire_ms, ops = random_sequence(rng)
            got_results, got_members, got_pending = run_sequence(
                Recruit, quota, min_level, expire_ms, ops)
            ref_results, ref_members, ref_pending = run_sequence(
                RefRecruit, quota, min_level, expire_ms, ops)
            self.assertEqual(got_results, ref_results, "case %d 结果序列不一致" % case)
            self.assertEqual(got_members, ref_members, "case %d 成员数不一致" % case)
            self.assertEqual(got_pending, ref_pending, "case %d pending 不一致" % case)
            self.assertLessEqual(got_members, quota, "case %d 成员数超过名额" % case)

    def test_replay_is_deterministic(self):
        rng = random.Random(7)
        quota, min_level, expire_ms, ops = random_sequence(rng)
        first = run_sequence(Recruit, quota, min_level, expire_ms, ops)
        second = run_sequence(Recruit, quota, min_level, expire_ms, ops)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
