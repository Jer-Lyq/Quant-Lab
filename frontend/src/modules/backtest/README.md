# Backtest Module

The backtest module owns task creation, queue status, archived results, charts, and trades.

## Boundaries

- A run binds one immutable strategy version and one linked instrument.
- The first release supports daily stock and ETF research only.
- Strategy code is edited in the strategy module, never on the backtest page.
- Local development uses an explicitly labelled fixture runner.
- Production uses the isolated RQAlpha runner image and a read-only RQAlpha bundle.

## Frontend structure

- `BacktestPage.vue`: module composition and result states.
- `composables/useBacktests.js`: API calls, polling, selection, cancellation, and form defaults.
- `components/BacktestForm.vue`: run configuration.
- `components/BacktestRunsList.vue`: task history rail.
- `components/BacktestResultCards.vue`: metric summary.
- `components/BacktestCurveChart.vue`: equity and drawdown chart.
- `components/BacktestTradesTable.vue`: trade archive.
