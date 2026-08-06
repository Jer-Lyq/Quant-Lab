# 策略与回测模块规划

## 已确认方向

Quant Lab 下一阶段建设两个模块：

1. 策略模块：用户收集、录入、编辑和保存 RQAlpha 风格的 Python 策略代码。
2. 回测模块：基于 RQAlpha 异步执行回测，保存结果，并做收益率等指标可视化。

本阶段不做研究笔记系统、报告系统、实盘交易、复杂因子平台或组合优化。后续可以扩展多标的组合，但第一版先让“代码策略 -> 任务队列 -> RQAlpha 回测 -> 结果可视化”跑通。

## 核心设计原则

### 1. 策略和代码版本分开

策略本体回答“这是什么策略”，代码版本回答“这次回测使用的是哪份代码”。

用户可以持续编辑策略代码，但每一次回测必须绑定一个不可变的代码版本快照。这样以后才能复现结果。

### 2. 策略代码统一采用 RQAlpha 格式

第一版不自定义策略 DSL。策略代码要求用户写 Python，并遵循 RQAlpha 的基本结构，例如：

```python
def init(context):
    pass


def handle_bar(context, bar_dict):
    pass
```

平台可以做基础校验，例如是否存在 `init`、`handle_bar`，但不在第一版做复杂静态分析。

### 3. 回测通过任务队列异步执行

Flask API 只负责创建回测任务，不直接阻塞等待 RQAlpha 执行完成。

Worker 独立处理队列：

1. 取出待执行任务。
2. 读取策略版本代码。
3. 生成临时策略文件和 RQAlpha 配置。
4. 调用 RQAlpha 执行。
5. 解析结果。
6. 写回数据库和结果文件。

### 4. 数据接入优先采用本地行情适配层

RQAlpha 数据模块第一版采用第三种方案：写一个适配层，让 RQAlpha 回测读取 Quant Lab 数据中心已有的本地行情数据。

这意味着数据中心仍然负责 Tushare 同步、标的管理、日线/周线存储；回测模块不重复采集行情。

## 模块划分

### 策略模块 Strategy

负责：

- 策略列表。
- 策略详情。
- 策略说明。
- Python 代码编辑。
- 代码版本保存。
- 代码版本二级浏览界面。
- 策略适用标的关联。
- 快速回测和历史回测入口。

不负责：

- 执行回测。
- 生成交易信号。
- 调用 RQAlpha。
- 保存回测结果。

### 回测模块 Backtest

负责：

- 创建回测任务。
- 设置回测参数。
- 查看任务状态。
- 查看回测结果。
- 展示收益曲线、回撤曲线、指标卡片、交易明细。

不负责：

- 编辑策略代码。
- 管理原始行情数据。
- 实盘交易。

### 数据模块 Data Adapter

负责：

- 将 Quant Lab 本地行情提供给 RQAlpha。
- 处理标的代码、日期、频率、OHLCV 字段映射。
- 后续支持多标的组合时，提供 universe 数据。

不负责：

- 策略 CRUD。
- 回测任务管理。
- 前端结果展示。

## 后端结构

```text
backend/app/routes/
  strategies.py              # 策略 API
  backtests.py               # 回测 API

backend/app/services/
  strategy_service.py        # 策略、版本、标的关联
  backtest_service.py        # 回测任务创建、查询、结果读取
  backtest_queue.py          # 数据库任务队列
  rqalpha_runner.py          # RQAlpha 调用封装
  rqalpha_data_adapter.py    # 读取 Quant Lab 本地行情并适配 RQAlpha

backend/app/workers/
  backtest_worker.py         # 后台回测 worker
```

## 前端结构

```text
frontend/src/modules/strategy/
    StrategyPage.vue
    README.md
    composables/useStrategies.js
    components/
      StrategyList.vue
      StrategyEditor.vue       # 代码编辑器和说明编辑
      StrategyVersionStudio.vue
      StrategyVersionPanel.vue
      StrategyInstrumentPanel.vue

frontend/src/modules/backtest/
  BacktestPage.vue
  README.md
  composables/useBacktests.js
  components/
    BacktestForm.vue
    BacktestRunsTable.vue
    BacktestStatusPanel.vue
    BacktestResultCards.vue
    BacktestEquityChart.vue
    BacktestDrawdownChart.vue
    BacktestTradesTable.vue
```

AppShell 后续增加模块导航：

- 数据中心
- 策略库
- 回测

## 数据库设计草案

### strategies

保存策略的基本信息。

```sql
CREATE TABLE strategies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    strategy_type TEXT NOT NULL DEFAULT 'custom'
        CHECK (strategy_type IN ('trend', 'mean_reversion', 'breakout', 'momentum', 'timing', 'custom')),
    market TEXT,
    freq TEXT NOT NULL DEFAULT 'daily' CHECK (freq IN ('daily', 'weekly')),
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'ready', 'backtesting', 'validated', 'discarded')),
    author_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### strategy_versions

保存策略代码版本。回测必须绑定这里的某个版本。

```sql
CREATE TABLE strategy_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id INTEGER NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    version_name TEXT NOT NULL,
    code TEXT NOT NULL,
    code_hash TEXT NOT NULL,
    notes TEXT,
    validation_status TEXT NOT NULL DEFAULT 'unchecked'
        CHECK (validation_status IN ('unchecked', 'valid', 'invalid')),
    validation_message TEXT,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### strategy_instruments

保存策略适用或关注的标的。

```sql
CREATE TABLE strategy_instruments (
    strategy_id INTEGER NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    instrument_id INTEGER NOT NULL REFERENCES instruments(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (strategy_id, instrument_id)
);
```

### backtest_runs

保存一次回测的配置、状态和核心指标。

```sql
CREATE TABLE backtest_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id INTEGER NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    strategy_version_id INTEGER NOT NULL REFERENCES strategy_versions(id) ON DELETE RESTRICT,
    instrument_id INTEGER REFERENCES instruments(id) ON DELETE SET NULL,
    universe_config_json TEXT,
    freq TEXT NOT NULL DEFAULT 'daily' CHECK (freq IN ('daily', 'weekly')),
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    initial_cash REAL NOT NULL DEFAULT 1000000,
    benchmark TEXT,
    commission_rate REAL NOT NULL DEFAULT 0,
    slippage_rate REAL NOT NULL DEFAULT 0,
    parameters_json TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'queued', 'running', 'success', 'failed', 'cancelled')),
    error_message TEXT,
    total_return REAL,
    annual_return REAL,
    max_drawdown REAL,
    sharpe REAL,
    volatility REAL,
    win_rate REAL,
    trade_count INTEGER,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    queued_at TEXT,
    started_at TEXT,
    finished_at TEXT
);
```

### backtest_jobs

数据库任务队列表。第一版先用 SQLite 轮询，后续任务量变大再切换 Celery 或 Redis Queue。

```sql
CREATE TABLE backtest_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES backtest_runs(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'success', 'failed', 'cancelled')),
    priority INTEGER NOT NULL DEFAULT 100,
    attempts INTEGER NOT NULL DEFAULT 0,
    locked_by TEXT,
    locked_until TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### backtest_artifacts

保存 RQAlpha 输出、收益曲线、回撤曲线、交易明细等结果。第一版可以使用 JSON 或文件路径。

```sql
CREATE TABLE backtest_artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES backtest_runs(id) ON DELETE CASCADE,
    artifact_type TEXT NOT NULL
        CHECK (artifact_type IN ('summary', 'equity_curve', 'drawdown_curve', 'trades', 'positions', 'raw_output')),
    storage_kind TEXT NOT NULL DEFAULT 'json'
        CHECK (storage_kind IN ('json', 'file')),
    json_data TEXT,
    relative_path TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

## API 草案

### 策略 API

- `GET /api/strategies`
- `POST /api/strategies`
- `GET /api/strategies/<id>`
- `PATCH /api/strategies/<id>`
- `DELETE /api/strategies/<id>`
- `POST /api/strategies/<id>/versions`
- `GET /api/strategies/<id>/versions`
- `GET /api/strategy-versions/<id>`
- `POST /api/strategies/<id>/instruments`
- `DELETE /api/strategies/<id>/instruments/<instrument_id>`

### 回测 API

- `GET /api/backtests`
- `POST /api/backtests`
- `GET /api/backtests/<id>`
- `POST /api/backtests/<id>/cancel`
- `GET /api/backtests/<id>/artifacts`

`POST /api/backtests` 创建 `backtest_run` 和 `backtest_job`，返回任务 ID。前端轮询 `GET /api/backtests/<id>` 获取状态。

## RQAlpha 数据适配方案

第一版目标不是改造数据中心，而是让回测模块能复用数据中心已同步的日线/周线行情。

### 输入

- `instruments`
- `price_bars`
- `instrument_datasets`
- 后续可能接本地 parquet/csv 数据。

### 字段映射

```text
Quant Lab price_bars       RQAlpha 需要的数据含义
trade_date                 datetime/date
open                       open
high                       high
low                        low
close                      close
volume                     volume
amount                     total_turnover 或扩展字段
```

### 第一版处理策略

- 先只支持日线和周线。
- 先只支持已在数据中心同步过的标的。
- 回测前检查该标的在所选时间范围内是否有数据。
- 数据不足时任务失败，并写入清楚的错误信息。
- 多标的组合后续通过 `universe_config_json` 扩展。

## 实现顺序

### Phase 1：策略库和代码版本

先做策略模块，不接 RQAlpha。

验收标准：

- 能创建策略。
- 能编辑策略说明。
- 能编辑 Python 策略代码。
- 能保存代码版本。
- 能查看历史版本。
- 能关联数据中心已有标的。
- 能对代码做基础 RQAlpha 结构校验。

### Phase 2：回测任务队列

先把任务创建、状态流转和 worker 骨架跑通。

验收标准：

- 能创建回测任务。
- API 不阻塞等待回测完成。
- Worker 能领取任务并更新状态。
- 任务失败时能记录错误。
- 前端能看到 pending、running、success、failed。

### Phase 3：RQAlpha Runner

接入 RQAlpha 执行策略版本。

验收标准：

- Worker 能把策略版本写入临时文件。
- Worker 能生成 RQAlpha 配置。
- Worker 能调用 RQAlpha。
- Worker 能解析核心指标。
- 回测结果能保存到 `backtest_runs` 和 `backtest_artifacts`。

### Phase 4：本地行情数据适配

让 RQAlpha 使用 Quant Lab 数据中心已有数据。

验收标准：

- 能读取已同步标的的日线/周线。
- 能完成单标的回测。
- 数据不足时有清楚提示。
- 数据适配逻辑独立在 `rqalpha_data_adapter.py`，不写进路由。

### Phase 5：结果可视化

展示成熟回测结果。

验收标准：

- 指标卡：总收益、年化收益、最大回撤、夏普、波动率、胜率、交易次数。
- ECharts 收益曲线。
- ECharts 回撤曲线。
- 交易明细表。
- 策略页提供历史回测入口，结果详情集中在回测模块展示。

### Phase 6：多标的和参数调优

在单标的回测稳定后再做。

验收标准：

- 支持一个策略绑定多个标的。
- 支持 universe 配置。
- 支持参数 JSON。
- 支持参数扫描任务。
- 支持保存最优参数到策略版本说明。

## 暂不做

- 不做自研策略 DSL。
- 不做实盘交易。
- 不做券商接口。
- 不做复杂权限协作。
- 不做报告生成。
- 不做机器学习自动调参。
- 不做完整专业因子平台。

## 下一步建议

下一步先实现 Phase 1：策略库和代码版本。它是回测模块的前置基础，也最符合当前学习阶段。等策略代码和版本快照稳定后，再加任务队列和 RQAlpha runner。
