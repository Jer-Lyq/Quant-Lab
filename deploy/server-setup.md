# 服务器部署操作清单

以下命令假设服务器是 Ubuntu，项目部署到 `/opt/quant-lab/app`。

## 1. 安装 Docker

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
```

重新登录 SSH 后确认：

```bash
docker --version
docker compose version
```

## 2. 拉取代码

```bash
sudo mkdir -p /opt/quant-lab
sudo chown -R $USER:$USER /opt/quant-lab
cd /opt/quant-lab
git clone <your-repo-url> app
cd app
```

## 3. 配置环境变量

```bash
cp .env.example .env
nano .env
```

必须修改：

```text
SECRET_KEY=
TUSHARE_TOKEN=
ADMIN_USERNAME=
ADMIN_PASSWORD=
BACKTEST_HOST_DATA_DIR=/opt/quant-lab/app/data
RQALPHA_HOST_BUNDLE_DIR=/opt/quant-lab/app/data/rqalpha-bundle
```

## 4. 准备 RQAlpha Runner

构建独立执行镜像：

```bash
docker build -t quant-lab-backtest-runner:latest backend/backtest_runtime
mkdir -p data/rqalpha-bundle data/backtests
```

下载 RQAlpha 基础数据 bundle：

```bash
docker run --rm --user 0:0 \
  --entrypoint rqalpha \
  -v "$PWD/data/rqalpha-bundle:/root/.rqalpha/bundle" \
  quant-lab-backtest-runner:latest update-bundle
```

RQAlpha 6.3.0 包含额外商业使用限制。本项目按个人学习和研究用途接入；商业使用前需要单独核对并取得相应授权。

## 5. 启动服务

```bash
docker compose up -d --build
docker compose exec backend flask init-db
docker compose exec backend flask create-admin
docker compose ps
```

`backtest-worker` 通过受控 Docker CLI 启动一次性 Runner。策略容器禁用网络、只读根文件系统、移除 Linux capabilities，并限制 CPU、内存和进程数。不要把 Docker socket 挂载给 Web 后端或策略 Runner。

## 6. 验证

```bash
curl http://127.0.0.1/api/health
docker compose logs --tail=100 backtest-worker
```

浏览器访问：

```text
http://服务器IP
```

## 7. 配置 HTTPS

域名解析到服务器后：

```bash
sudo apt install -y certbot
sudo certbot certonly --standalone -d your-domain.com
```

把 `deploy/nginx-https.template.conf` 复制到 `nginx/quant-lab.conf`，将 `example.com` 替换成你的域名，然后重启：

```bash
docker compose restart nginx
```

## 8. 备份

```bash
APP_DIR=/opt/quant-lab/app sh scripts/backup.sh
```

可用 `crontab -e` 加每天凌晨备份：

```text
0 2 * * * APP_DIR=/opt/quant-lab/app sh /opt/quant-lab/app/scripts/backup.sh
```
