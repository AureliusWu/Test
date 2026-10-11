# v1.2.0 — 原生 Windows 与 PWA

2026-10-11。当前为双平台工程候选，公开 CI / Pages / 下载状态在推送后单独回读。旧 v1.1.1 发行、标签和封存证据保持原样。

## 交付能力

- Windows：Ren'Py 8.5.3 原生 EXE / ZIP，默认 1280×720、1920×1080 虚拟画布，仍可全屏。构建与源码验收复制输入到独立临时工程，排除 game/saves，并隔离开发进程的 APPDATA 保存路径。
- PWA：同一 Ren'Py 8.5.3 DSL 经官方 WebAssembly 组件构建。相对 manifest、应用 ID / scope、图标和缓存，可部署在 `/Rain/` 与更深子路径。首次完整 SHA-256 / 字节数验证后才能宣告可离线重开；下载失败删除未完成缓存。
- 更新：新 worker 完整下载后等待旧应用窗口关闭。旧窗口继续使用旧完整构建，避免新旧 WASM / game.zip 混读；缓存清理只覆盖本应用与同 scope。
- 存档：继续 `AureliusWu-BeforeTheRainStops-v1` 原生存档身份。浏览器持久数据和桌面本机位置独立，浏览器菜单提供原生导入 / 导出 ZIP。请定期备份，清理浏览器数据会影响存档。
- 内容：剧情 JSON 仅版本字段更新；六章正文、560 台词 ID、16 原生状态路线、17 配音和 85 游戏资源保留。
- 复用：三仓共用契约 / 校验接口与许可素材导出。Rain 的原始素材、Prompt、授权、版本与 SHA-256 绑定到 `REUSABLE-ASSETS.json`；人物、剧情与创作批准边界继续独立。

## 本轮检查

当前本地门槛与最终包哈希写入 `docs/evidence/v12-local-platforms.json`。Python / 作者校验、Ren'Py lint、源码和独立 EXE 交互、跨进程存档、旧档读取与实际浏览器检查分别记录，不用构建 ZIP 代替 Windows 执行，也不用缓存 ready 代替菜单可交互。

浏览器验收包含真实点击 Start / 保存 / 读取，原生 ZIP 跨新浏览器导入，完整断网重开、1440×900 / 412×915 / 568×320 / 844×390、嵌套子路径、父 scope worker 与旧窗口续读升级。新增平台报告首个基线；原始离线资源约 73.5 MB，第一次完整下载成本明显高于轻量网页，尤其慢网络和移动设备。预算为完整内容 <100 MB、菜单可交互 <120 秒；本机样本不代表实际手机性能。

本机显示器为 2560×1440 / Windows 125% DPI。可选验收参数仅使测试进程 DPI aware，在真正 1920×1080 窗口检查精确 PNG；全屏检查匹配当前硬件后返回 1920 窗口。CI 默认继续严格 1920 全屏。没有调整用户系统 DPI。

正式发布时集中下载同一成功提交的 Windows / Web CI 产物，不重复构建替换验收字节。公开 PWA smoke 再验证固定 worker revision、实际菜单 / 保存 / 读取与断网重开；详情及交付文件名见 [发行说明](RELEASE_V12.md)。新素材 catalog 含89项 / 212文件引用，可导出59项 / 140文件；PWA wrapper也已纳入带许可的可复用配方。

真人试听、普通硬件 / DPI、物理设备安装、Normal / True 阅读计时、最终创作定案与冻结继续单独验收；dummy 音频、自动耗时、结构检查不能证明这些项目。

## 开发命令

```powershell
$env:PYTHONUTF8="1"
python -m tools.validate
node scripts/vn-contract.mjs game/data/story.json
node --test scripts/vn-materials.test.mjs
node scripts/vn-materials.mjs verify
node scripts/vn-materials.mjs export .reuse-kit/v1.1.0
python -m tools.build.sdk
python -m tools.build.web
npm ci
npx playwright install chromium
npm run test:pwa
```

发行 ZIP 位于 `dist/BeforeTheRainStops-1.2.0-win.zip` 与 `dist/BeforeTheRainStops-1.2.0-web.zip`。不要直接双击 HTML；浏览器必须通过 HTTPS 或 localhost 服务访问。

技术参考：[Ren'Py 官方 Web / HTML5](https://www.renpy.org/doc/html/web.html)、[官方 8.5.3 SHA-256](https://www.renpy.org/dl/8.5.3/checksums.txt)、[SDL 进程 DPI awareness](https://wiki.libsdl.org/SDL2/SDL_HINT_WINDOWS_DPI_AWARENESS)。官网当前文档版本会前进，执行 SDK / web 字节固定在 8.5.3。
