# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- 管理员：录入标的、同步数据、维护研究数据源、管理内部平台数据入口。
- 普通用户：登录后搜索并查看已录入标的，浏览行情图表和明细，后续沉淀研究过程。

## Product Purpose

Quant Lab is a multi-user internal quantitative research platform. Its first module is an authenticated data center for managing instruments and viewing synced market data.

## Positioning

An internal research platform that starts with a local-first data center, then expands into research-process capture, strategy exploration, task tracking, and reports after the workflows are defined.

## Operating Context

- Desktop browser usage is the primary path.
- Users log in, search the instrument list, open one instrument, and inspect daily or weekly bars.
- Administrators can create a new instrument and trigger sync from the same screen.

## Capabilities and Constraints

- Frontend: Vue 3, Element Plus, ECharts.
- Backend: Flask, SQLite.
- Data source: Tushare first; backend provider interface should leave room for other sources.
- Chinese UI vocabulary is part of the product.
- The interface must keep the existing authenticated workflow and avoid inventing unsupported market claims.

## Brand Commitments

- Product name: Quant Lab.
- Existing dashboard vocabulary is research-oriented and pragmatic.
- The product should feel like a serious workbench, not a consumer app.

## Evidence on Hand

- [README.md](README.md)
- [frontend/src/App.vue](frontend/src/App.vue)
- [frontend/src/styles.css](frontend/src/styles.css)
- `Quant Lab 量化研究实验工作台项目书.docx`

## Product Principles

- Make the primary task visible immediately after login.
- Keep admin actions distinct from read-only research browsing.
- Prioritize scanability, density, and fast state changes.
- Let charts, tables, and metadata read as one coherent research surface.
- Discuss strategy/research-process modules before implementing them; do not infer the workflow too early.

## Accessibility & Inclusion

- Preserve keyboard access, visible focus, and readable contrast.
- Keep the layout responsive enough to remain usable on narrower browser widths.
