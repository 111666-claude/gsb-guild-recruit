# guild-recruit

公会招募：等级条件筛选、名额上限、申请幂等、过期申请清理，只用 Python 标准库。

```
python3 -m recruit.cli --sample level
python3 -m recruit.cli --sample quota
python3 -m recruit.cli --sample dup
python3 -m unittest discover -s tests -v
```

## 口径（README 为准）

- **等级条件**：等级低于 `min_level` 的申请直接拒绝（返回 `False`），不占名额也不入队。
- **名额上限**：成员数达到 `quota` 后 `accept` 失败；成功接受的申请要从队列移出，不许重复接受。
- **申请幂等**：同一 `apply_id` 重复提交只留一条（第二次返回 `False`）。
- **过期清理**：超过 `expire_ms` 未处理的申请必须从队列清掉，`pending` 只数还在等的。
- **查询代价**：`pending` 不许每次全扫申请队列，`scanned_count` 不随申请数线性增长。
- **规模**：单公会 50 万条申请、每秒 10 万次提交与查询，单次摊还 O(1)。

## 输出契约（不改格式）

```
ok=false
second=false
second=false pending=1
pending=0
```

## 目录

```
recruit/core.py   条件、名额与幂等
recruit/cli.py    命令行入口
tests/            unittest 用例
```
