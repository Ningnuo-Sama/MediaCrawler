# LOCAL_MAINTENANCE — MediaCrawler 维护说明

> 2026-09-16 建：用户已在 GitHub fork 本项目，远端按双远端约定配置完毕。

## 远端与分支

| 名称 | 指向 | 角色 |
|---|---|---|
| `origin` | Ningnuo-Sama/MediaCrawler | **用户 fork**（推送目标） |
| `upstream` | NanmiCoder/MediaCrawler | 官方上游（更新来源） |

> 2026-11-04 起用 `Ningnuo-Sama` 账号（原 `ningnuo-dot` 已封，其 fork 只读）。

| 分支 | 内容 |
|---|---|
| `main` | 跟随上游 + 极少量本机配置（当前仅 `CDP_CONNECT_EXISTING=False` 一处） |
| `local-custom` | 2026-08~09 实测修复与工具存档（douyin 评论洞察、知乎问题排序等 37 文件，**仅代码**） |

## 配置与密钥边界

- `config/base_config.py` 是本机运行配置（CDP 开关、保存选项等），改动**允许提交**（当前无凭证）。
- **登录 cookie、token 等凭证一律不提交 Git**——登录态存于浏览器 profile 与 `browser_data/`，天然不入库；若未来把 cookie 写进 config，须改用环境变量或本地未跟踪文件。

## 上游更新流程（每次更新照此执行）

```bash
cd /d/GitHub/MediaCrawler
git fetch upstream                                  # 1. 取官方更新
git log --oneline main..upstream/main               # 2. 看更新范围与发行说明
git checkout -b update-candidate upstream/main      # 3. 开候选分支，把上游合进来
git merge local-custom                              #    （如需带本地定制）逐个解决冲突，冲突停留在候选分支
# 4. 候选分支上：重装依赖变化部分、跑通一次采集、验证数据落库格式
# 5. 验证通过后才合入 main 并推送 fork：
git checkout main && git merge update-candidate
git push origin main
git branch -d update-candidate
```

- 不直接在 `main` 上 `git pull upstream`；不动正在运行的采集环境。
- 上游大版本重构（数据库格式、接口）先单独备份 `media_data/` 与数据库再动。

## 回退

- 回退代码：`git checkout <旧提交或分支>`；采集出的数据在 `media_data/` 与数据库，与代码版本无关，回退代码不影响已采数据。

## 更新记录

| 日期 | 上游 SHA | 结果 |
|---|---|---|
| 2026-11-04 | `d172fc8` | 合入上游 6 个提交（README 三种语言、赞助商图片、`.gitignore`），无代码改动；冲突为 0，本地定制（`CDP_CONNECT_EXISTING=False`、`*.bak*` 忽略规则）全部保留。回退点：标签 `backup-pre-upstream-20261104`（`b435723`） |
| 2026-11-15 | `4d629b5` | 上游自 `d172fc8` 起新增 18 个提交，**已合入 main**（合并提交 `0549371`），冲突 0，`CDP_CONNECT_EXISTING=False` 自动保留（上游默认 True 被本地值盖住，合并后已核对）。与下载管线直接相关：抖音图文 `/note/` 链接解析修复（`efcf8ab`）、抖音实况图随附视频抽取（`ade7a23`/`b059657`）、小红书实况图视频与 `image_list` 原始媒体（`dd4be82`）、新增 `DOWNLOAD_LIVE_PHOTO`（默认 True）、CDP 现有浏览器 attach 失败提示（`a5d4083`/`d17bd61`）、代理 IP 缓存单条坏数据不再全丢（`eeaa4fd`）。 |

### 2026-11-15 本地修复（未随上游）

采集在这台机器上完全跑不起来，两个根因都在 `[::1]` 与代理环境上：

1. 本机进程环境 `NO_PROXY` 含 `[::1]`，httpx 构造客户端时把它当 URL 解析 → `InvalidURL: Invalid port: ':1]'`。
   `tools/cdp_browser.py` 的 `/json/version` 探测改走 `make_async_client()`；
   `tools/httpx_util.py` 的直连判断从「`proxy` key 不存在」改为「`proxy` 值为空」——调用方常写
   `make_async_client(proxy=self.proxy)`，`proxy=None` 时旧判断失效，仍会读环境代理并被 `[::1]` 打挂。
2. CDP 回环统一用 `127.0.0.1`：`localhost` 可能解析到 `::1`，Chrome 会回 `ws://[::1]:9222/...`，
   Playwright 把它解析成端口 `":1]"`。新增 `_normalize_ws_url` 把回环 host 归一化为 `127.0.0.1`。
   `browser_launcher.py` 的端口 bind/connect 探测同样改成 `127.0.0.1`。

回归测试：`tests/test_loopback_proxy_safety.py`（新增 6 条）、`tests/test_cdp_browser.py` 断言改为 `127.0.0.1`。
合并上游后全量 `pytest tests`：**341 passed / 2 failed**，两个失败是 `tests/test_no_user_info.py` 依赖 Unix `grep`，与本次改动无关。

合并后的端到端实测（2026-11-15）：

| 场景 | 结果 |
|---|---|
| 抖音视频 detail + 媒体 | `video.mp4` 15.5 MB + `cover.jpeg` |
| 抖音 creator + 评论（登录态） | 3 条作品、`creator_comments` 34 KB（评论接口必须登录，说明登录态有效） |
| 抖音图文 `/note/` 链接 + 媒体 | 解析出 aweme_id，下到 6 张 jpeg（**合并前该链接直接报错**） |
| 小红书图文 detail + 媒体 | 4 张 webp |
| 小红书视频 detail + 媒体 | `video.mp4` 156 MB + `cover.webp`（走 CloakMulti `xhs-01` 登录态） |
| 实况照片抽取 | 抖音/小红书 `extract_live_photo_video_urls` 均可用（样例输出正确），缺真实实况笔记样本做端到端 |

**已知遗留**：`.venv` 里 playwright 1.61.0 需要 `chromium_headless_shell-1228`，本机 `ms-playwright` 只有 1243/1248，
所以「不用 CDP 的标准模式」起不来；CDP 模式不受影响。要用标准模式先跑
`uv run python -m playwright install chromium`。

- 2026-11-04 同时修正远端角色：`origin` 曾被误设为 NanmiCoder 官方源，已恢复为 `ningnuo-dot/MediaCrawler`（用户 fork），`upstream` 仍指官方源。
