# 搭建问题记录

记录时间：2026-08-05

## 已确认问题

### 1. PowerShell 默认输出编码造成中文显示乱码

- 现象：直接 `Get-Content` 查看 `README.md`、`PRODUCT.md`、`frontend/src/App.vue` 时，中文显示为乱码。
- 核实：用 UTF-8 输出读取后，文件内容本身正常。
- 处理：后续在 Windows/PowerShell 中检查中文文件时，优先使用：

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Get-Content -Raw -Encoding UTF8 <file>
```

### 2. 首版前端集中在单个 `App.vue`

- 现象：登录、应用壳层、标的列表、管理员录入、数据源配置、行情图表、因子面板、表格、格式化、ECharts option 都集中在一个文件。
- 风险：后续网站扩展为多模块平台时，数据中心会和研究模块、策略模块、系统管理模块互相缠绕。
- 处理：已将数据中心拆为 `frontend/src/modules/data-center/`，并新增 `frontend/src/app/` 承载应用壳层、登录和 API 客户端。

### 3. 数据源能力原本直接写在 Tushare 服务和后台路由里

- 现象：管理员创建标的和同步标的直接调用 Tushare 函数。
- 风险：未来接入 AkShare、本地 CSV、券商数据或其他数据源时，需要反复改路由。
- 处理：已新增 `backend/app/services/data_providers/`，当前只注册 `tushare` provider，后续新增数据源应走 provider 注册表。

### 4. Vite 构建在当前受限环境里触发 `esbuild spawn EPERM`

- 现象：运行 `npm run build` 时，Vite 加载配置阶段启动 esbuild 子进程失败。
- 判断：这是当前执行环境对子进程的权限限制，不是业务代码报错。
- 处理：在允许启动子进程的环境里重新运行 `npm run build`，生产构建已通过。

### 5. 前端生产包出现大 chunk 警告

- 现象：`npm run build` 成功，但 Vite 提示 JS chunk 超过 500 kB。
- 判断：当前同时使用 Element Plus 和 ECharts，首版单入口打包出现大 chunk 可以接受，但后续网站多模块化后应做路由级或模块级懒加载。
- 后续：引入真实路由后，优先把数据中心、研究模块、后台管理拆成动态导入。

### 6. 研究模块范围尚未定义

- 现状：平台定位已经明确为“多用户内部研究平台”，研究模块要沉淀研究过程。
- 风险：如果过早按默认想法实现策略、回测、笔记、报告，容易做出不符合个人研究流程的结构。
- 决策：进入策略、研究笔记、回测、报告等模块前，必须先讨论流程、对象、权限和数据模型，再实现。

## 当前工程结构决策

- 数据中心是第一个业务模块，不再等同于整个网站。
- 先接入 Tushare，但后端要保留数据源 provider 扩展口。
- 多用户内部平台优先保证认证、权限、模块边界和可维护性。
- 研究过程沉淀模块先预留信息架构，不抢先实现业务细节。
