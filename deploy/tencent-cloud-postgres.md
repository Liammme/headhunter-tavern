# 腾讯云后端部署指南

本文是 `赏金猎人` 后端的默认上线方案，目标读者是第一次自己部署服务器的人。

默认方案：

1. 腾讯云 CVM
2. Ubuntu Linux
3. Python 虚拟环境运行 FastAPI
4. PostgreSQL 作为正式数据库
5. `systemd` 守护 API
6. `nginx` 做反向代理
7. `cron` 跑每日 `daily_bounty`

这份指南只覆盖仓库当前已有能力，不引入 Docker、任务平台、托管数据库迁移工具或新的外部依赖。

## 1. 服务器目标结构

默认约定以下路径：

- 项目目录：`/opt/bounty-pool/app`
- 后端目录：`/opt/bounty-pool/app/backend`
- 虚拟环境：`/opt/bounty-pool/venv`
- 日志目录：`/var/log/bounty-pool`
- 后端运行用户：`bounty`

如果你改了这些路径，记得同时修改：

- `deploy/systemd/bounty-pool.service`
- `deploy/cron/daily-bounty.cron`
- `deploy/nginx/bounty-pool.conf`

## 2. 服务器初始化

以 Ubuntu 为例，先登录服务器，然后执行：

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip postgresql nginx git
sudo adduser --system --group --home /opt/bounty-pool bounty
sudo mkdir -p /opt/bounty-pool/app /var/log/bounty-pool
sudo chown -R bounty:bounty /opt/bounty-pool /var/log/bounty-pool
```

## 3. 拉代码并创建虚拟环境

切到 `bounty` 用户后执行：

```bash
sudo -u bounty -H bash
cd /opt/bounty-pool/app
git clone <你的仓库地址> .
python3 -m venv /opt/bounty-pool/venv
/opt/bounty-pool/venv/bin/pip install --upgrade pip
/opt/bounty-pool/venv/bin/pip install -e ./backend
```

如果仓库不是公开的，这一步需要你自己准备 Git 凭据；不要把凭据写进仓库文件。

## 4. 准备 PostgreSQL

进入 PostgreSQL：

```bash
sudo -u postgres psql
```

执行以下 SQL，把 `change_me_now` 换成你自己的强密码：

```sql
CREATE USER bounty_pool_user WITH PASSWORD 'change_me_now';
CREATE DATABASE bounty_pool OWNER bounty_pool_user;
\q
```

默认连接串格式：

```text
postgresql+psycopg://bounty_pool_user:change_me_now@127.0.0.1:5432/bounty_pool
```

仓库当前已经兼容以下几种写法：

- `postgresql+psycopg://...`
- `postgresql://...`
- `postgres://...`

正式环境仍建议统一写成 `postgresql+psycopg://...`，这样最直观。

## 5. 配置后端环境变量

先复制模板：

```bash
cd /opt/bounty-pool/app/backend
cp .env.example .env
```

然后编辑 `/opt/bounty-pool/app/backend/.env`，至少确认这些字段：

```dotenv
DATABASE_URL=postgresql+psycopg://bounty_pool_user:change_me_now@127.0.0.1:5432/bounty_pool
CORS_ORIGINS=https://your-frontend-domain.com,http://localhost:3000
BOUNTY_POOL_INTELLIGENCE_LLM_ENABLED=true
BOUNTY_POOL_ZHIPU_API_KEY=your_real_key
BOUNTY_POOL_ZHIPU_MODEL=glm-4-flash-250414
BOUNTY_POOL_ZHIPU_BASE_URL=https://open.bigmodel.cn/api/paas/v4
BOUNTY_POOL_ZHIPU_FALLBACK_MODELS=glm-4-flash-250414,glm-4.7-flash
```

注意：

1. 线上不要再使用 SQLite 作为正式库。
2. `.env` 不要提交到 Git。
3. 如果暂时没有智谱 key，可以先把 `BOUNTY_POOL_INTELLIGENCE_LLM_ENABLED=false`，等密钥准备好再打开。

## 6. 手动初始化并验证后端

先在服务器手动跑一次，确认代码、依赖、数据库、环境变量都通：

```bash
cd /opt/bounty-pool/app/backend
source /opt/bounty-pool/venv/bin/activate
python -m app.cli.daily_bounty
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

另开一个终端检查：

```bash
curl http://127.0.0.1:8000/health
```

期望结果：

1. `daily_bounty` 输出 JSON summary
2. `/health` 返回 `{"status":"ok"}` 或等价 JSON
3. 进程启动时没有数据库连接异常

如果这一步没过，不要先配 `systemd` 或 `nginx`，先把根因查清。

## 7. 安装 systemd 服务

把仓库模板复制到系统目录：

```bash
sudo cp /opt/bounty-pool/app/deploy/systemd/bounty-pool.service /etc/systemd/system/bounty-pool.service
```

如果你的部署路径不是默认值，先修改以下字段再启用：

- `WorkingDirectory`
- `EnvironmentFile`
- `ExecStart`
- `User`
- `Group`

然后启用服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable bounty-pool
sudo systemctl start bounty-pool
sudo systemctl status bounty-pool --no-pager
```

查看日志：

```bash
journalctl -u bounty-pool -n 100 --no-pager
```

## 8. 安装 nginx 反向代理

复制模板：

```bash
sudo cp /opt/bounty-pool/app/deploy/nginx/bounty-pool.conf /etc/nginx/sites-available/bounty-pool.conf
```

把 `server_name api.your-domain.com;` 改成你的真实域名，然后启用：

```bash
sudo ln -sf /etc/nginx/sites-available/bounty-pool.conf /etc/nginx/sites-enabled/bounty-pool.conf
sudo nginx -t
sudo systemctl reload nginx
```

如果你要上 HTTPS，再继续接证书；这一步不在当前仓库模板范围内。

## 9. 安装每日定时任务

先确认手动跑 `python -m app.cli.daily_bounty` 没问题，再安装 cron：

```bash
sudo cp /opt/bounty-pool/app/deploy/cron/daily-bounty.cron /etc/cron.d/bounty-pool-daily
sudo chmod 644 /etc/cron.d/bounty-pool-daily
sudo systemctl restart cron
```

模板默认每天 `08:00` 执行，并把日志写到：

```text
/var/log/bounty-pool/daily-bounty.log
```

检查最近日志：

```bash
tail -n 50 /var/log/bounty-pool/daily-bounty.log
```

## 10. 最小验收清单

部署完成后，至少逐项确认：

1. `systemctl status bounty-pool --no-pager` 显示 `active (running)`
2. `curl http://127.0.0.1:8000/health` 返回正常
3. `journalctl -u bounty-pool -n 100 --no-pager` 没有数据库连接错误
4. `sudo -u postgres psql -lqt | grep bounty_pool` 能看到数据库
5. `/var/log/bounty-pool/daily-bounty.log` 有最新执行记录
6. 前端域名访问 API 时，CORS 没有报错

## 11. 常见故障先查什么

### 11.1 服务起不来

先查：

```bash
systemctl status bounty-pool --no-pager
journalctl -u bounty-pool -n 100 --no-pager
```

重点看：

1. `.env` 路径是否正确
2. `DATABASE_URL` 是否写错
3. 虚拟环境依赖是否安装完整
4. `WorkingDirectory` 是否真的是 `/opt/bounty-pool/app/backend`

### 11.2 API 能跑但页面跨域失败

先查 `.env` 里的 `CORS_ORIGINS`，确保前端真实域名已经加进去，多个域名用英文逗号分隔。

### 11.3 daily_bounty 没跑

先查：

```bash
cat /etc/cron.d/bounty-pool-daily
tail -n 100 /var/log/bounty-pool/daily-bounty.log
```

常见原因：

1. cron 文件权限不对
2. 虚拟环境路径写错
3. 工作目录不是 `/opt/bounty-pool/app/backend`

## 12. 当前明确不做

这份方案当前不覆盖：

1. Docker 化
2. 多实例扩容
3. 托管 PostgreSQL
4. 自动 schema migration
5. 监控平台接入
6. HTTPS 证书自动签发

这些都可以后续再加，但不应该阻塞当前版本正式上线。
