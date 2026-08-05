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
```

## 4. 启动服务

```bash
docker compose up -d --build
docker compose exec backend flask init-db
docker compose exec backend flask create-admin
docker compose ps
```

## 5. 验证

```bash
curl http://127.0.0.1/api/health
```

浏览器访问：

```text
http://服务器IP
```

## 6. 配置 HTTPS

域名解析到服务器后：

```bash
sudo apt install -y certbot
sudo certbot certonly --standalone -d your-domain.com
```

把 `deploy/nginx-https.template.conf` 复制到 `nginx/quant-lab.conf`，将 `example.com` 替换成你的域名，然后重启：

```bash
docker compose restart nginx
```

## 7. 备份

```bash
APP_DIR=/opt/quant-lab/app sh scripts/backup.sh
```

可用 `crontab -e` 加每天凌晨备份：

```text
0 2 * * * APP_DIR=/opt/quant-lab/app sh /opt/quant-lab/app/scripts/backup.sh
```

