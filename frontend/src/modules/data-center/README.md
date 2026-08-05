# Data Center Module

数据中心是 Quant Lab 的第一个业务模块，负责标的录入、Tushare 同步、行情展示、指标展示和因子检查。

## 边界

- 属于本模块：标的列表、行情 K 线、成交量、副图指标、策略因子、最近行情表、管理员数据源配置、管理员标的同步。
- 不属于本模块：策略编辑、研究笔记、回测任务、研究报告生成。这些属于后续“研究过程沉淀”模块，进入实现前需要先讨论流程和数据模型。

## 结构

```text
modules/data-center/
  DataCenterPage.vue          # 模块入口
  components/                 # UI 子组件
  composables/useDataCenter.js # 数据加载、同步、删除、数据源配置
  utils/chartOptions.js        # ECharts option 构造
  utils/formatters.js          # 数字、百分比、分位格式化
  utils/labels.js              # 选项、标签、默认状态
```

## 数据源扩展

当前前端仍以 Tushare 配置为主。后端已经开始通过 market data provider 访问数据源，后续接入 AkShare、本地 CSV 或券商数据时，应新增 provider，而不是把逻辑继续写进路由。
