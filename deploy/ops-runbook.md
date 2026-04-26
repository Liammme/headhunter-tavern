# 猎头酒馆后端运维与发版手册

本文面向已经完成正式上线后的日常运维，不再讨论“怎么第一次把服务跑起来”，而是回答：

1. 线上服务怎么查看状态
2. 每日任务怎么确认是否正常
3. 后端怎么发新版
4. 出问题后先看什么
5. 需要回滚时怎么做

当前线上形态默认是：

1. 前端：Vercel
2. 后端：腾讯云轻量服务器
3. API 域名：`https://api.talentsignal.cloud`
4. 前端域名：`https://talentsignal.cloud`
5. 进程托管：`systemd`
6. 反向代理：`nginx`
7. 数据库：PostgreSQL
8. 定时任务：`cron` 每天 08:00 跑 `daily_bounty`

## 1. 线上关键路径

后端关键路径按顺序是：

1. `nginx`
2. `systemd` 托管的 `uvicorn`
3. FastAPI 应用
4. PostgreSQL
5. `cron` 触发 `python -m app.cli.daily_bounty`

排查问题时，不要一上来猜代码。先判断断在哪一层。

## 2. 常用命令

### 2.1 看 API 进程状态

```bash
sudo systemctl status bounty-pool --no-pager
```

### 2.2 重启 API

```bash
sudo systemctl restart bounty-pool
sudo systemctl status bounty-pool --no-pager
```

### 2.3 看 API 日志

```bash
journalctl -u bounty-pool -n 100 --no-pager
```

持续跟日志：

```bash
journalctl -u bounty-pool -f
```

### 2.4 看 nginx 状态

```bash
sudo systemctl status nginx --no-pager
sudo nginx -t
```

### 2.5 看定时任务日志

```bash
tail -n 100 /var/log/bounty-pool/daily-bounty.log
```

### 2.6 手动跑一次每日任务

```bash
cd /opt/bounty-pool/app/backend
source /opt/bounty-pool/venv/bin/activate
python -m app.cli.daily_bounty
```

### 2.7 本机探活

```bash
curl http://127.0.0.1:8000/health
curl https://api.talentsignal.cloud/health
```

## 3. 每日巡检最小清单

每天不需要做复杂巡检，先看这四项：

1. `systemctl status bounty-pool --no-pager` 是否为 `active (running)`
2. `curl https://api.talentsignal.cloud/health` 是否返回正常
3. `/var/log/bounty-pool/daily-bounty.log` 今天 08:00 后是否有新记录
4. 产品首页数据是否正常更新，没有空白或明显过旧

如果这四项都正常，说明主链基本健康。

## 4. 发版标准流程

下面这套流程默认用于“后端代码有更新，需要发到线上”。

### 4.1 发版前

本地先做最小相关验证，不要把明显没过的版本直接推上服务器。

至少确认：

1. 改动相关 `pytest` 已通过
2. 没有把 `.env`、密钥、数据库密码提交到 Git
3. 没有改坏 `deploy/` 模板和路径假设

### 4.2 推荐方式：执行后端部署脚本

代码已经合并并 push 到 `master` 后，优先用脚本发后端：

```bash
ssh deploy@43.163.127.112
bash /opt/bounty-pool/app/deploy/backend-deploy.sh
```

脚本会执行：

1. 确认 `/opt/bounty-pool/app` 是 Git safe directory
2. 检查 tracked 文件是否有本地改动
3. 拉取 `origin/master`
4. 重启 `bounty-pool`
5. 验证本机和公网 `/health`

脚本不会执行：

1. 安装 Python 依赖
2. 数据库迁移
3. 修改 `.env`
4. 修改 nginx、cron 或 systemd 配置

如果本次后端依赖、数据库、nginx、cron 或 systemd 有变化，不要只跑脚本，先按对应变更类型做额外检查。

### 4.3 手动方式：拉新代码

```bash
cd /opt/bounty-pool/app
git config --global --add safe.directory /opt/bounty-pool/app
git status --short --branch
git fetch origin
git checkout master
git pull --ff-only origin master
git rev-parse HEAD
```

如果线上不是直接跟主分支，要按实际分支替换。

### 4.4 更新依赖

如果本次有 Python 依赖变化，执行：

```bash
/opt/bounty-pool/venv/bin/pip install -e ./backend
```

如果没有依赖变化，也可以跳过。

### 4.5 重启服务

```bash
cd /opt/bounty-pool/app/backend
sudo systemctl restart bounty-pool
sudo systemctl status bounty-pool --no-pager
journalctl -u bounty-pool -n 100 --no-pager
```

### 4.6 发版后验收

至少做这三步：

```bash
curl http://127.0.0.1:8000/health
curl https://api.talentsignal.cloud/health
curl https://api.talentsignal.cloud/api/v1/home
```

再打开前端确认首页接口可用。

## 5. 哪些变更要额外小心

以下类型不是“拉代码重启”就算完：

1. 数据库 schema 变更
2. `DATABASE_URL` 或其他环境变量变更
3. cron 路径、执行命令、日志路径变更
4. nginx 配置变更
5. systemd 服务文件变更

这几类改动发布后，都要额外执行对应命令：

- nginx 改动：`sudo nginx -t && sudo systemctl reload nginx`
- systemd 改动：`sudo systemctl daemon-reload && sudo systemctl restart bounty-pool`
- `.env` 改动：`sudo systemctl restart bounty-pool`
- cron 改动：重新复制 cron 文件并确认权限

## 6. 回滚原则

如果新版本上线后出现明显异常，先做最小回滚，不要在线上临时 patch。

默认顺序：

1. 先确认异常是否只是 nginx / systemd / `.env` 配置问题
2. 如果是代码版本问题，回到上一个可用 commit
3. 重新安装依赖并重启服务
4. 再做健康检查

最小回滚示例：

```bash
sudo -u bounty -H bash
cd /opt/bounty-pool/app
git log --oneline -n 5
git checkout <上一个可用提交>
/opt/bounty-pool/venv/bin/pip install -e ./backend
exit
sudo systemctl restart bounty-pool
curl https://api.talentsignal.cloud/health
```

注意：不要在线上做 `git reset --hard` 这类破坏性操作，除非你明确知道当前工作树状态。

## 7. 常见故障先看哪里

### 7.1 前端打不开数据，但服务器进程是活的

先分层检查：

1. `curl https://api.talentsignal.cloud/health`
2. `curl http://127.0.0.1:8000/health`
3. `sudo systemctl status nginx --no-pager`
4. `journalctl -u bounty-pool -n 100 --no-pager`

这能快速判断是域名代理问题，还是 FastAPI 本身有问题。

### 7.2 API 进程反复重启

先看：

```bash
journalctl -u bounty-pool -n 200 --no-pager
```

重点排查：

1. `.env` 缺字段
2. `DATABASE_URL` 写错
3. PostgreSQL 没启动
4. 新依赖没安装

### 7.3 每日数据没更新

先看：

```bash
tail -n 200 /var/log/bounty-pool/daily-bounty.log
cat /etc/cron.d/bounty-pool-daily
```

再手动执行一次：

```bash
cd /opt/bounty-pool/app/backend
source /opt/bounty-pool/venv/bin/activate
python -m app.cli.daily_bounty
```

如果手动能跑，说明问题多半在 cron 配置或环境。

## 8. 当前建议补充但不阻塞上线的事项

这些项值得排期，但不需要现在打断产品迭代：

1. 整理前后端统一发版清单
2. 为 API 增加更细的线上监控信号
3. 建立数据库备份与恢复演练
4. 明确定义回滚版本记录方式

## 9. 一句话原则

线上问题先按链路定位：

`域名/HTTPS -> nginx -> systemd -> FastAPI -> Postgres -> cron`

不要跳过证据直接猜代码，也不要把临时操作沉淀成正式流程。
