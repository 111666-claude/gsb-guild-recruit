"""公会招募：等级条件筛选、名额上限、申请幂等、过期申请清理。

缺陷：不校验等级条件、名额满了也收、重复申请重复占位、过期申请不清理、查询全扫申请表。
"""

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
        self.applications = []
        self.scanned = 0

    def apply(self, apply_id, player, level, now_ms):
        """提交申请。缺陷：不看等级条件、不看名额、同一 apply_id 重复占位。"""
        self.applications.append([apply_id, player, level, now_ms])
        return True

    def accept(self, apply_id):
        """接受申请。缺陷：名额满了照样收、接受后也不把申请移出。"""
        for item in self.applications:
            self.scanned += 1
            if item[0] == apply_id:
                self.members += 1
                return True
        return False

    def pending(self, now_ms):
        """待处理申请数。缺陷：过期的也算，而且每次全扫。"""
        self.scanned += len(self.applications)
        return len(self.applications)

    def scanned_count(self):
        return self.scanned
