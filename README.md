# 雨停之前 / Before the Rain Stops

离线中文 Ren’Py 视觉小说。雨夜旧车站，两位久未联系的旧友，和一封没有寄出的信。

**v1.2.0 双平台开发候选：Ren'Py 原生 Windows EXE + 同引擎 WebAssembly PWA。** 浏览器入口为 [Rain PWA](https://aureliuswu.github.io/Rain/)；当前提交需完成 CI / Pages 部署后更新公开验收状态，详见 [双平台说明](docs/DUAL_PLATFORM_V12.md)。

PWA 首次联网保存完整内容后可安装、离线重开和导入 / 导出 Ren'Py 原生存档。浏览器与 Windows 的本机保存位置独立；请使用浏览器左上角导出备份。新版本下载完成后等待旧窗口关闭再激活，正在阅读的窗口继续使用原版本。

三作品共用制作检查和可导出的许可素材包：`node scripts/vn-materials.mjs verify`、`node scripts/vn-materials.mjs export .reuse-kit/v1.1.0`。保留角色、剧情、引擎和存档身份，移植入口见 [可复用素材](docs/production/REUSABLE-MATERIALS.md)。

以下保留已公开的 v1.1.1 Windows 正式版身份证据；它不替代新 PWA 或 v1.2.0 的验收。

**v1.1.1 鉴赏室体验补丁已正式发布。** 六章、24个叙事场景、四次选择、16条路线、Normal / True两个结局，七表情、四背景、旧信CG、17句配音及原创音乐 / 环境音效。

主菜单进入“鉴赏室”：五张已有背景 / CG、三首音乐随真实剧情解锁，退出后保留进度，未解锁内容隐藏图片和标题。音乐鉴赏显示已解锁数量、当前曲名及播放 / 暂停 / 停止状态；暂停后显示“继续”，停止后提示选择已解锁音乐。状态分隔符改用现有字体支持的中文冒号，修复方框缺字。

关键配音使用免费开源 **Qwen3-TTS 1.7B CustomVoice / Serena**，预生成OGG随包提供；当前台词可重听，已读历史可重播，自动模式等待重播结束。

2026-10-09 已完成验收证据导出维护：Windows / Linux 各130项检查通过，原始Windows审计及全部12个截图副本完整取回。正式下载继续为v1.1.1；详见 [维护记录](docs/REVIEW_TRANSPORT.md)。

## 下载与运行

[v1.1.1 Release](https://github.com/AureliusWu/Test/releases/tag/v1.1.1) · [Windows ZIP](https://github.com/AureliusWu/Test/releases/download/v1.1.1/BeforeTheRainStops-1.1.1-win.zip) · [本次验收](docs/RELEASE_ACCEPTANCE_V111.md) · [统一真人后续](docs/HUMAN_HANDOFF.md)

1. 完整解压 `BeforeTheRainStops-1.1.1-win.zip` 到可写目录。
2. 双击 `BeforeTheRainStops.exe`，无需Python、引擎、模型、账号或语音API，可离线游玩。
3. 左键 / 空格 / Enter推进，右键 / Esc开菜单，F切换全屏；下方有回退、历史、快进、自动、存读档与设置。
4. 主菜单进入鉴赏室，看过的图片与听过的音乐自动解锁。

原生1920×1080、默认1280×720；沿用 `AureliusWu-BeforeTheRainStops-v1` 存档目录，已用公开v1.1.0实际写入并验证两个代表存档和原生已读解锁。

游戏验收提交 `491e9859368a402960afcdf856be4f456b885ec5` / [Windows CI 37711912728](https://github.com/AureliusWu/Test/actions/runs/37711912728)；原始 ZIP **56,382,628 字节**，SHA-256 `7f57b4f4d3f2cc4071d7e4d59ff6a2e3c7db0531b78477abae18804c47d6d35b`。

Windows **118 项 Python**、全部作者校验及 Ren’Py 8.5.3.26051504 lint 通过；源码和独立 EXE 各 **36 用例 / 448 断言 / 82 截图**。新进程读档 / 鉴赏持久进度 **1/16/3**，公开 v1.1.0 写档 **1/14/3**、新 EXE 读取旧档 / 已读解锁 **2/26/4**（用例 / 断言 / 截图）。五个完整进程退出 0、未超时，异常计数全为 0；两遍真实前缀另各 **6/103/29** 通过。

Windows 审计完整解码并核对 **174 张原始 PNG** 的尺寸 / SHA-256；复核 **58 个关键视图**，其中 12 个直接查看当前全分辨率 JPEG 副本、46 个原始 PNG 与已有审阅哈希完全相同。副本绑定原图哈希，保留 JPEG 检查限制。85 包内资产、ZIP CRC、版本、署名及许可核验通过，原始玩家包无测试注入或模型。

全分支15,065字符，单路线11,303–11,666。真人试听、Normal / True 阅读计时、普通电脑 / 中文路径 / DPI、最终创作定案与冻结继续由用户统一操作，五组保持 pending。Windows 使用 dummy 音频，自动执行耗时不等于阅读时长；真实旧档覆盖两个代表位置，未宣称验证全部玩家旧档或 Linux 原生 UI。

## 开发与验证

当前游戏验收提交 `491e9859368a402960afcdf856be4f456b885ec5`。完整机器与图像证据见 [本次验收](docs/RELEASE_ACCEPTANCE_V111.md)，发布进度见 [当前断点](docs/WORK_CHECKPOINT.md)。

Python 3.12、Pillow、SoundFile / NumPy 只用于开发。模型与推理依赖不进入玩家包。

```bash
python -m pip install -r requirements-dev.txt
python -m tools.preflight
python -m tools.validate
python -m tools.build.sdk
```

Windows 使用固定并校验 SHA-256 的 Ren’Py 8.5.3 SDK：

本机验收可通过 `RENPY_ACCEPTANCE_WINDOWED=1`、`RENPY_HIGHDPI=1` 使用真正 1920×1080 窗口，无需改系统分辨率或 DPI；仍实际切换全屏并校验硬件尺寸，所有原生 / 缩放 PNG 门槛保持。源码验收与发行构建分别复制到临时工程，排除 `game/saves`，保护作者 / 玩家持久数据。

Web 构建与浏览器检查：

```powershell
python -m tools.build.sdk
python -m tools.build.web
npm ci
npx playwright install chromium
npm run test:pwa
```

生成 `dist/web/` 与版本化 `*-web.zip`，CI 使用相同官方 WASM、完整原子缓存和 `/Rain/` 子路径检查后部署 Pages。Windows 继续使用 Ren'Py 原生 ZIP，无新播放器框架。

升级构建先从已发布的 v1.1.0 ZIP 校验并保留原语句名；CI 自动完成。手工构建也应在 lint 前运行 `python -m tools.build.seed_release_names --previous-zip <已下载的完整v1.1.0-ZIP>`。标准 [old-game 机制](https://www.renpy.org/doc/html/build.html#old-game) 不进入玩家包；真实旧档加载另行测试。

```powershell
$sdk = ".runtime/renpy-8.5.3-sdk"
& "$sdk/lib/py3-windows-x86_64/python.exe" "$sdk/renpy.py" . lint --error-code --all-problems
python -m tools.build.display
python -m tools.build.verify_package --source-sdk $sdk --timeout 2400
python -m tools.build.package --sdk $sdk
$version = (Get-Content VERSION -Raw).Trim()
python -m tools.build.verify_package --zip "dist/BeforeTheRainStops-$version-win.zip" --timeout 2400
python -m tools.build.verify_upgrade --previous-zip .runtime/compat/BeforeTheRainStops-1.1.0-win.zip --current-zip "dist/BeforeTheRainStops-$version-win.zip"
```

可选共享结构检查：`node scripts/vn-contract.mjs game/data/story.json`。制作契约见 [SHARED-VN.md](docs/production/SHARED-VN.md)，不替代16条原生状态路线及Windows实际包验收。

## 数据与来源

`game/data/story.json` 是剧情唯一事实来源，编译成原生 label / menu / if。仅 affection、trust、truth_known 三个状态，遍历全部 16 条可达路径。源码资产、Scene Prompt、录音文字、来源、许可证和 SHA-256 均保留；运行时没有 LLM、TTS 服务或服务器。

| 位置 | 内容 |
|---|---|
| `game/data/` | 剧情、资产及语音绑定 |
| `game/script/*_generated.rpy` | 自动生成的运行脚本 |
| `assets_source/`、`prompts/` | 原始资产、版本化请求与 Registry |
| `tools/`、`tests/` | 编译、完整性和回归工具 |
| `CREDITS.md`、`licenses/` | 署名、第三方许可与 AI 输出说明 |

[正文精修记录](docs/review/V10_PROSE_REVIEW.json) · [字数统计](docs/STORY_STATS_V10.md) · [项目约束](docs/PROJECT.md) · [测试计划](docs/TEST_PLAN.md)。最终主题、角色、美术与结局由用户决定。

## 正式发布记录

[正式 v1.1.1](https://github.com/AureliusWu/Test/releases/tag/v1.1.1) 已于 **2026-10-08T14:26:27Z** 发布，非草稿、非预发行，并验证为最新正式版。tag 指向 `75f757b9ce78779a7036a948375f55579990b8e5`，游戏源码与验收候选完全相同；[发布 CI 37792383846](https://github.com/AureliusWu/Test/actions/runs/37792383846) 成功，公开 ZIP 下载回读 SHA-256 / CRC 与验收包一致。v1.1.0、v1.0.1、v1.0.0 标签和全部下载资产保持原样。实际身份见 [发布记录](docs/evidence/v111-publication.json)。

[发布授权](docs/review/V111_PUBLICATION_AUTHORIZATION.json) · [语音方案与来源](docs/VOICE_UPGRADE_V10.md)。

保留 [v1.1.0](https://github.com/AureliusWu/Test/releases/tag/v1.1.0)、[v1.0.1](https://github.com/AureliusWu/Test/releases/tag/v1.0.1) 和 [v1.0.0](https://github.com/AureliusWu/Test/releases/tag/v1.0.0) 的原有下载。
