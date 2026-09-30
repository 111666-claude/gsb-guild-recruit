"""公会招募：等级条件筛选、名额上限、申请幂等、过期申请清理。

口径见 README：
- 等级低于 min_level 的申请直接拒绝，不占名额也不入队。
- 成员数达到 quota 后 accept 失败；接受成功的申请移出队列，不可重复接受。
- 同一 apply_id 重复提交只留一条，重复提交返回 False。
- 超过 expire_ms 未处理的申请惰性清理，pending 只统计还在等的。

台账：dict 存申请、deque 按提交时间排序供过期淘汰、计数器维护待处理数，
提交 / 接受 / 查询单次摊还 O(1)，scanned 只记过期淘汰实际弹出的条数，
不随申请总数线性增长。
"""

from collections import deque

QUOTA = 30
MIN_LEVEL = 10
EXPIRE_MS = 60000


class Recruit:
    """招募台账。"""

    def __init__(self, quota=QUOTA, min_level=MIN_LEVEL, expire_ms=EXPIRE_MS):
        self.quota = quota
        self.min_level = min_level
        self.expire_ms = expire_ms
        self.members = 0
        self._applications = {}
        self._order = deque()
        self._pending = 0
        self.scanned = 0

    def _purge_expired(self, now_ms):
        """弹出所有超过 expire_ms 未处理的申请（摊还 O(1)）。"""
        while self._order:
            expires_at, apply_id = self._order[0]
            if expires_at > now_ms:
                break
            self._order.popleft()
            item = self._applications.pop(apply_id, None)
            if item is not None:
                self._pending -= 1
                self.scanned += 1

    def apply(self, apply_id, player, level, now_ms):
        """提交申请；等级不足拒绝，重复申请只留一条。"""
        self._purge_expired(now_ms)
        if level < self.min_level:
            return False
        if apply_id in self._applications:
            return False
        self._applications[apply_id] = (apply_id, player, level, now_ms)
        self._order.append((now_ms + self.expire_ms, apply_id))
        self._pending += 1
        return True

    def accept(self, apply_id, now_ms=None):
        """接受申请；名额满、不存在或已过期的申请接受失败。"""
        if now_ms is not None:
            self._purge_expired(now_ms)
        if self.members >= self.quota:
            return False
        item = self._applications.pop(apply_id, None)
        if item is None:
            return False
        self._pending -= 1
        self.members += 1
        return True

    def pending(self, now_ms):
        """还在等且未过期的申请数（O(1) 摊还，不全扫）。"""
        self._purge_expired(now_ms)
        return self._pending

    def scanned_count(self):
        return self.scanned
