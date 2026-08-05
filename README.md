# Quant Lab 量化研究实验工作台

首版实现数据中心模块：管理员录入股票、ETF 或基金代码，后端通过 Tushare 同步日线和周线数据，普通用户登录后查看标的档案、K线、成交量和技术指标。

## 技术栈

- Frontend: Vue3, Element Plus, ECharts
- Backend: Flask, Gunicorn, SQLite
- Data: Tushare
- Deploy: Docker Compose, Nginx

## 本地/服务器启动

1. 复制环境变量：

```bash
cp .env.example .env
```

2. 修改 `.env`：

```text
SECRET_KEY=随机长密钥
TUSHARE_TOKEN=你的 Tushare Token
ADMIN_USERNAME=admin
ADMIN_PASSWORD=初始化管理员密码
```

3. 启动服务：

```bash
docker compose up -d --build
```

4. 初始化数据库：

```bash
docker compose exec backend flask init-db
docker compose exec backend flask create-admin
```

5. 检查健康状态：

```bash
curl http://127.0.0.1/api/health
```

6. 浏览器访问服务器域名或 IP。

## 首次使用

1. 用 `.env` 中的管理员账号登录。
2. 在管理员录入区输入 Tushare 代码，例如 `000001.SZ`。
3. 选择类型：股票、ETF 或基金。
4. 点击“新增并同步”。
5. 同步成功后，普通用户可以在数据中心查看该标的。

## 部署到 `/opt/quant-lab`

```bash
sudo mkdir -p /opt/quant-lab
cd /opt/quant-lab
git clone <your-repo-url> app
cd app
cp .env.example .env
docker compose up -d --build
docker compose exec backend flask init-db
docker compose exec backend flask create-admin
```

## HTTPS

首版建议先用 Nginx 暴露 80 端口，确认域名解析后再在服务器安装 `certbot` 申请证书，并把 Nginx 配置升级为 443 HTTPS。

## 备份

服务器上可以每天执行：

```bash
APP_DIR=/opt/quant-lab/app sh scripts/backup.sh
```

脚本会备份 SQLite 数据库，并保留最近 7 天。

