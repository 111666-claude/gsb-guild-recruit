"""公会招募：等级条件筛选、名额上限、申请幂等、过期申请清理。

实现要点：
- 等级低于 min_level 的申请直接拒绝，不占名额也不入队。
- 成员数达到 quota 后 accept 失败；成功接受的申请立即移出队列，不可重复接受。
- 同一 apply_id 重复提交只留一条（第二次返回 False）；过期清理后可重新提交。
- 过期申请按提交顺序惰性清理（deque 队首），单次摊还 O(1)；
  pending 只数还在等的，不全扫申请表，scanned 只计惰性清理实际摘除的条目。
- 约定 now_ms 单调不减（与真实时间一致），过期清理因此可以遇未过期即停。
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
        self._live = {}
        self._order = deque()
        self.scanned = 0

    def _sweep(self, now_ms):
        """惰性清理队首已过期或已失效的条目，单次摊还 O(1)。"""
        order = self._order
        while order:
            apply_id, ts = order[0]
            item = self._live.get(apply_id)
            if item is None or item[1] != ts:
                order.popleft()
                self.scanned += 1
                continue
            if now_ms - ts > self.expire_ms:
                order.popleft()
                del self._live[apply_id]
                self.scanned += 1
                continue
            break

    def apply(self, apply_id, player, level, now_ms):
        """提交申请：等级不足直接拒绝；同一 apply_id 幂等去重。"""
        self._sweep(now_ms)
        if level < self.min_level:
            return False
        if apply_id in self._live:
            return False
        self._live[apply_id] = (player, now_ms)
        self._order.append((apply_id, now_ms))
        return True

    def accept(self, apply_id):
        """接受申请：名额满即失败；成功后从队列移出，不可重复接受。"""
        item = self._live.get(apply_id)
        if item is None:
            return False
        if self.members >= self.quota:
            return False
        del self._live[apply_id]
        self.members += 1
        return True

    def pending(self, now_ms):
        """待处理申请数：只数还在等的，过期的不计。"""
        self._sweep(now_ms)
        return len(self._live)

    def scanned_count(self):
        return self.scanned
