# 策略数据库逻辑

本文描述当前 Quant Lab 实际实现的策略数据模型，并标明回测相关表目前只是结构预留，尚未有 RQAlpha 执行器。

## 核心关系

```text
users
  ├─< strategies
  │    ├─< strategy_versions
  │    ├─< strategy_instruments >─ instruments
  │    └─< backtest_runs >─< backtest_jobs
  │                         └─< backtest_artifacts
  └─< strategy_versions.created_by
```

## 策略本体：`strategies`

一条策略记录描述“这是什么策略”，不保存具体某次运行的代码快照。

| 字段 | 含义 | 当前规则 |
| --- | --- | --- |
| `id` | 策略主键 | 自增，内部引用使用 |
| `name` | 策略名称 | 必填 |
| `strategy_type` | 策略类型 | 趋势、均值回归、突破、动量、择时、自定义 |
| `market` | 适用市场 | 如 A 股、ETF |
| `freq` | 默认频率 | 日线或周线 |
| `status` | 研究状态 | 草稿、待回测、回测中、已验证、废弃 |
| `strategy_idea` | 策略思想 | 解释想捕捉的市场现象和设计动机 |
| `description` | 策略说明 | 来源、核心逻辑、适用环境 |
| `uploader_notes` | 上传者备注 | 风险、改动、待验证事项 |
| `author_id` | 创建者 | 作者或管理员可编辑 |
| `created_at` / `updated_at` | 时间信息 | 修改策略属性、版本或关联标的时更新 |

`strategy_idea` 是新加字段。启动时会检查旧 SQLite 数据库；缺列时用迁移补齐，已有数据不会丢失。

## 代码版本：`strategy_versions`

每次“保存版本”都会新增一条记录，不更新已有版本。它是未来回测复现的唯一代码来源。

| 字段 | 含义 |
| --- | --- |
| `strategy_id` | 所属策略 |
| `version_name` | 用户命名或自动生成的 `v1`、`v2` |
| `code` | RQAlpha 风格 Python 代码快照 |
| `code_hash` | SHA-256 内容哈希，识别代码是否一致 |
| `notes` | 本次版本说明 |
| `validation_status` / `validation_message` | 基础 AST 校验结果 |
| `created_by` / `created_at` | 保存人和保存时间 |

基础校验只检查 Python 语法、`init` 和 `handle_bar` 是否存在，不执行代码。

版本删除规则：

1. 只有策略作者或管理员可以删除。
2. 版本必须属于当前策略。
3. 已被 `backtest_runs.strategy_version_id` 引用的版本不能删除。
4. 未被引用的版本可以删除，删除不可恢复。

这保证回测接入后，历史结果不会失去对应代码。

## 策略与标的：`strategy_instruments`

这是 `strategies` 和 `instruments` 的多对多关系表。

| 字段 | 含义 |
| --- | --- |
| `strategy_id` | 策略 |
| `instrument_id` | 数据中心中已经录入的标的 |
| `created_at` | 关联时间 |

同一个策略和标的只能关联一次。删除标的或策略时，关联记录通过外键级联删除。这里表示“适用/研究标的集合”，不是一次回测唯一确定的标的。

## 回测预留：`backtest_runs`、`backtest_jobs`、`backtest_artifacts`

这些表已经在数据库中建立，但当前没有创建任务的 API、没有 worker、没有 RQAlpha runner。

| 表 | 未来职责 |
| --- | --- |
| `backtest_runs` | 一次回测的配置、状态、指标摘要；必须绑定 `strategy_id` 和 `strategy_version_id` |
| `backtest_jobs` | 异步队列领取、锁定、重试和错误信息 |
| `backtest_artifacts` | 收益曲线、回撤曲线、成交、持仓和原始输出 |

未来创建回测时，应该从策略页带入策略 ID 和版本 ID，再由用户确认时间区间、初始资金、手续费、滑点、基准和标的集合。Worker 只读取不可变版本代码，不读取编辑器中的未保存内容。

## 当前权限与删除边界

| 对象 | 作者 | 管理员 | 普通其他用户 |
| --- | --- | --- |
| 查看策略 | 已登录用户 | 已登录用户 | 已登录用户 |
| 编辑策略属性 | 可以 | 可以 | 不可以 |
| 保存/载入/删除代码版本 | 可以 | 可以 | 不可以 |
| 关联/移除标的 | 可以 | 可以 | 不可以 |
| 删除策略 | 可以 | 可以 | 不可以 |

删除策略会级联删除未被外部表限制的版本和标的关联。等回测启用后，若策略下有历史回测，建议改成“归档策略”而不是直接物理删除；这一点需要在回测模块正式开始前确认。
