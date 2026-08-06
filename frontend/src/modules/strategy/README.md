# Strategy Module

策略库负责保存 RQAlpha 风格的 Python 策略代码、上传者说明、代码版本和关联标的。

## 边界

- 属于本模块：策略 CRUD、代码编辑、代码版本快照、版本二级浏览界面、基础 RQAlpha 结构校验、关联数据中心标的、快速回测与历史回测入口。
- 不属于本模块：执行 RQAlpha、回测任务队列、收益曲线和交易明细。这些属于后续 backtest 模块。

## 结构

```text
modules/strategy/
  StrategyPage.vue
  components/
    StrategyList.vue
    StrategyEditor.vue
    StrategyVersionStudio.vue
    StrategyVersionPanel.vue
    StrategyInstrumentPanel.vue
  composables/useStrategies.js
  utils/labels.js
```

后端策略规则与安全边界见 `docs/STRATEGY_SECURITY.md`。策略版本列表只加载元数据，打开或载入某个版本时再读取完整代码。

## 策略代码约定

第一版统一使用 RQAlpha 风格 Python 代码，基础校验要求至少包含：

```python
def init(context):
    pass


def handle_bar(context, bar_dict):
    pass
```
