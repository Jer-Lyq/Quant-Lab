# Quant Lab 服务器 Codex 交互式部署任务书

## 给服务器 Codex 的首条指令

请完整读取本文件，然后在当前服务器上部署 Quant Lab。先执行只读检查并汇报结论，再按阶段继续；除非遇到本文件定义的暂停条件，不要只给出命令建议，要实际执行、验证并修复可安全修复的问题。

部署目标：

- GitHub 仓库：`https://github.com/Jer-Lyq/Quant-Lab.git`
- 分支：`main`
- 回测模块最低提交：`0691cd9692d9ec82b1b52adde2f6a19884b36997`
- 应用目录：`/opt/quant-lab/app`
- 持久化数据：`/opt/quant-lab/app/data`
- 日志目录：`/opt/quant-lab/app/logs`
- 第一阶段访问方式：`http://服务器IP`
- 目标系统：Ubuntu 22.04/24.04，Docker Compose 部署

## 强制安全边界

1. 不要回显、记录或提交 `TUSHARE_TOKEN`、管理员密码、`SECRET_KEY`、SSH 凭据。
2. 不要把密钥放入命令行参数、Git、聊天回复或日志；需要密钥时暂停，让用户直接编辑 `.env`。
3. 如果 `/opt/quant-lab/app` 已存在，先识别它是否为本项目。不要覆盖未知目录。
4. 不要执行 `git reset --hard`、`git clean -fd`、`docker compose down -v`，不要删除 `data/`、`logs/`、`.env` 或备份。
5. 发现工作区有未提交改动时暂停并汇报，不要自动还原或覆盖。
6. 已存在 `.env` 时先备份并保留现有值，只补充缺失配置；不要用 `.env.example` 覆盖它。
7. 已存在数据库或 RQAlpha bundle 时保留，不要重新初始化或下载覆盖，除非验证表明缺失或损坏。
8. 防火墙操作前先确保 SSH 端口允许。不要在未确认 SSH 规则时启用 UFW。
9. 本次只有服务器 IP，不配置 HTTPS。原项目 HTTPS 模板尚未在 Compose 中完整挂载 `443` 和证书目录，禁止直接替换 Nginx 配置。
10. `backtest-worker` 可以挂载 Docker socket；Web 后端和一次性策略 Runner 不得挂载 Docker socket。

## 暂停并询问用户的条件

仅在以下情况暂停：

- 缺少 sudo 权限，且 Docker/Git 尚未安装。
- 应用目录存在但不是目标仓库。
- Git 工作区有未提交改动或分支状态无法安全快进。
- 需要用户填写 `TUSHARE_TOKEN`、管理员密码或确认公网 IP。
- 端口 `80` 已被非本项目服务占用。
- Docker、磁盘、网络或系统架构不满足要求，无法安全继续。
- 需要修改云厂商安全组；服务器内无法代替用户完成该操作。

## 阶段 0：只读环境检查

先执行并汇报，不做安装或修改：

```bash
whoami
hostname
pwd
uname -a
cat /etc/os-release
uname -m
df -h /
free -h
nproc
command -v git || true
command -v docker || true
docker --version 2>/dev/null || true
docker compose version 2>/dev/null || true
sudo -n true >/dev/null 2>&1 && echo SUDO_NONINTERACTIVE_OK || echo SUDO_MAY_PROMPT
ss -lntp 2>/dev/null | grep -E ':(22|80|443)\b' || true
test -e /opt/quant-lab/app && ls -la /opt/quant-lab/app || true
```

最低建议：2 核 CPU、4 GB 内存、20 GB 可用空间。资源略低时可以继续，但必须在最终报告中提示风险。

## 阶段 1：安装基础依赖

只安装缺失项。Ubuntu 环境推荐：

```bash
sudo apt update
sudo apt install -y ca-certificates curl git openssl
```

如果 Docker 或 Compose 缺失：

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
```

如果当前会话尚未获得 docker 组权限，可以在本次部署中使用 `sudo docker`，并提示用户部署后重新登录 SSH。不要因为组权限尚未刷新而重复安装 Docker。

验证：

```bash
git --version
docker --version || sudo docker --version
docker compose version || sudo docker compose version
```

## 阶段 2：获取或更新代码

### 全新部署

当 `/opt/quant-lab/app` 不存在时：

```bash
sudo mkdir -p /opt/quant-lab
sudo chown -R "$USER":"$USER" /opt/quant-lab
cd /opt/quant-lab
git clone https://github.com/Jer-Lyq/Quant-Lab.git app
cd app
git switch main
git pull --ff-only origin main
```

### 已有部署

当应用目录已经是目标仓库时：

```bash
cd /opt/quant-lab/app
git remote -v
git status --short
git branch --show-current
git rev-parse HEAD
git fetch origin main
```

如果 `git status --short` 非空，暂停并汇报。工作区干净时记录旧提交，再快进更新：

```bash
git rev-parse HEAD | tee /opt/quant-lab/previous_commit.txt
git switch main
git pull --ff-only origin main
```

### 代码验证

```bash
cd /opt/quant-lab/app
git status -sb
git log -1 --oneline
git merge-base --is-ancestor 0691cd9692d9ec82b1b52adde2f6a19884b36997 HEAD
test -f docker-compose.yml
test -f backend/Dockerfile.worker
test -f backend/backtest_runtime/Dockerfile
test -f frontend/package.json
```

`git merge-base --is-ancestor` 必须成功，说明当前版本包含回测模块。允许部署比 `0691cd9` 更新的 `main`。

## 阶段 3：保护数据并配置 `.env`

```bash
cd /opt/quant-lab/app
mkdir -p data/instruments data/backtests data/rqalpha-bundle logs
chmod 700 data logs
```

如果已有 `.env`：

```bash
cp -a .env ".env.backup.$(date +%Y%m%d_%H%M%S)"
chmod 600 .env
```

如果没有 `.env`：

```bash
cp .env.example .env
chmod 600 .env
```

然后暂停，让用户直接执行：

```bash
cd /opt/quant-lab/app
nano .env
```

用户需要填写或确认以下配置，服务器 Codex 不得要求用户在聊天中发送具体密钥：

```dotenv
FLASK_ENV=production
SECRET_KEY=<使用 openssl rand -hex 32 生成>
TUSHARE_TOKEN=<用户直接写入文件>
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<用户直接写入文件>
CORS_ORIGINS=http://服务器公网IP
SESSION_DAYS=7
MAX_CONTENT_LENGTH=1048576
BACKTEST_RUNNER=docker
BACKTEST_DOCKER_IMAGE=quant-lab-backtest-runner:latest
BACKTEST_TIMEOUT_SECONDS=300
BACKTEST_JOB_LEASE_SECONDS=600
BACKTEST_JOB_MAX_ATTEMPTS=2
BACKTEST_HOST_DATA_DIR=/opt/quant-lab/app/data
RQALPHA_HOST_BUNDLE_DIR=/opt/quant-lab/app/data/rqalpha-bundle
```

用户保存后，只验证键名和占位符，不打印值：

```bash
python3 - <<'PY'
from pathlib import Path

required = {
    "SECRET_KEY",
    "TUSHARE_TOKEN",
    "ADMIN_USERNAME",
    "ADMIN_PASSWORD",
    "CORS_ORIGINS",
    "BACKTEST_RUNNER",
    "BACKTEST_HOST_DATA_DIR",
    "RQALPHA_HOST_BUNDLE_DIR",
}

values = {}
for raw in Path(".env").read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    values[key.strip()] = value.strip()

missing = sorted(key for key in required if not values.get(key))
placeholders = sorted(
    key for key in required
    if any(word in values.get(key, "").lower() for word in ("replace-with", "your-tushare", "strong-initial"))
)
if missing or placeholders:
    raise SystemExit(f"env invalid; missing={missing}; placeholders={placeholders}")
print("env keys validated without printing secrets")
PY
```

## 阶段 4：构建 RQAlpha Runner 和数据 bundle

先选择 Docker 命令：如果普通用户运行 `docker info` 失败而 `sudo docker info` 成功，则本次所有 Docker 命令统一加 `sudo`。

构建隔离执行镜像：

```bash
cd /opt/quant-lab/app
docker build -t quant-lab-backtest-runner:latest backend/backtest_runtime
```

检查 bundle 是否已有内容：

```bash
find data/rqalpha-bundle -mindepth 1 -print -quit
```

仅当 bundle 为空时下载：

```bash
docker run --rm --user 0:0 \
  --entrypoint rqalpha \
  -v "$PWD/data/rqalpha-bundle:/root/.rqalpha/bundle" \
  quant-lab-backtest-runner:latest update-bundle
```

下载结束后确认目录非空。RQAlpha 6.3.0 含额外商业使用限制；最终报告必须注明当前部署按个人学习和研究用途配置。

## 阶段 5：启动应用

启动前验证 Compose：

```bash
cd /opt/quant-lab/app
docker compose config >/dev/null
```

启动并构建：

```bash
docker compose up -d --build
docker compose ps
```

首次部署或代码包含数据库迁移时执行：

```bash
docker compose exec -T backend flask init-db
docker compose exec -T backend flask create-admin
```

如果管理员已经存在，应检查命令输出并将“已存在”视为非致命情况；不要删除或覆盖现有管理员数据。

## 阶段 6：服务器内验证

等待最多 90 秒，不要用一次失败立即判定部署失败：

```bash
for i in $(seq 1 30); do
  if curl -fsS http://127.0.0.1/api/health >/dev/null; then
    echo HEALTH_OK
    break
  fi
  sleep 3
done
```

然后执行：

```bash
curl -i http://127.0.0.1/api/health
docker compose ps
docker compose logs --tail=100 backend
docker compose logs --tail=100 frontend
docker compose logs --tail=100 nginx
docker compose logs --tail=150 backtest-worker
ss -lntp 2>/dev/null | grep -E ':80\b' || true
```

验收标准：

- `/api/health` 返回 HTTP 200。
- `backend`、`frontend`、`nginx`、`backtest-worker` 均处于运行状态。
- Nginx 在宿主机监听 `80`。
- Worker 日志无循环崩溃、数据库权限错误或 Docker socket 权限错误。
- `data/` 和 `logs/` 保持为宿主持久化目录。

## 阶段 7：公网访问与防火墙

先检查 UFW：

```bash
sudo ufw status
```

如果 UFW 已启用，先确认 SSH 再开放 HTTP：

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw status
```

如果 UFW 未启用，不要擅自启用，只需提醒用户在云厂商安全组中开放：

- TCP `22`：SSH
- TCP `80`：Quant Lab HTTP
- TCP `443`：未来配置 HTTPS 时再开放

让用户在本地浏览器访问：

```text
http://服务器公网IP
```

如果服务器内部健康检查成功、端口 80 正常监听，但公网无法访问，应判断为云安全组、公网 IP、运营商防火墙或端口映射问题，不要反复重建容器。

## 阶段 8：备份

首次成功部署后执行一次备份验证：

```bash
cd /opt/quant-lab/app
APP_DIR=/opt/quant-lab/app sh scripts/backup.sh
ls -lh backups 2>/dev/null || true
```

可以建议用户配置每日备份，但不要未经确认修改 crontab：

```text
0 2 * * * APP_DIR=/opt/quant-lab/app sh /opt/quant-lab/app/scripts/backup.sh
```

## 故障处理原则

1. 先读取失败容器日志和 `docker compose ps`，再决定是否重建。
2. 构建失败时保留当前运行容器，不执行带 `-v` 的 down。
3. 数据库错误时先备份 `data/`，不要删除 SQLite 文件。
4. Docker socket 权限错误时检查 `backtest-worker`，不要把 socket 添加到 `backend`。
5. RQAlpha bundle 缺失时只重跑 bundle 下载，不重置数据库。
6. 更新部署失败时报告 `/opt/quant-lab/previous_commit.txt` 中的旧提交；未经用户确认不要自动切回或改写 Git 历史。

## 最终汇报格式

部署结束后必须向用户提供：

```text
部署状态：成功 / 部分成功 / 失败
服务器与系统：<hostname, Ubuntu version, architecture>
部署目录：/opt/quant-lab/app
Git 提交：<git rev-parse HEAD>
访问地址：http://<服务器IP>
容器状态：<backend/frontend/nginx/backtest-worker>
健康检查：<HTTP status and response summary>
数据目录：/opt/quant-lab/app/data
备份结果：<path or not configured>
尚未完成：<cloud security group / domain / HTTPS / real Tushare sync / production backtest smoke test>
重要警告：不要在回复中显示任何密钥或密码
```

只有在服务器内部健康检查、容器状态和公网访问路径均已明确后，才可以宣布部署完成。
