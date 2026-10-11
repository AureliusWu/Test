# 雨停之前 v1.2.0

同一 Ren'Py 8.5.3 视觉小说现在提供原生 Windows ZIP 与可安装、可完整离线阅读的 PWA。PWA 使用官方 WebAssembly 引擎，完整缓存按每个文件的 SHA-256 / 字节数核验；更新在关闭旧应用窗口后生效。

沿用六章剧情、560 台词 ID、16 条原生状态路线、17 句已有录音与85个游戏资源。Windows 延续原有 v1 存档身份；浏览器存档单独保存，并提供原生 ZIP 导入 / 导出。手机竖屏会提示横屏阅读，原始16:9画面保持一致。

PWA 首次完整下载约73.5 MB，慢网络需要等待“完整内容已保存，可离线重开”。本机浏览器与 Windows 自动测试分别见 [本地验收](evidence/v12-local-platforms.json)。实际物理设备安装、真人试听、阅读计时、普通电脑 / DPI 和创作最终定案仍待统一验收。

三仓共享制作契约、许可与素材导出规则；Rain 可复用 kit 提供59项 / 140个绑定来源、Prompt与 SHA-256 的文件，项目专属角色与剧情保持独立。

发行时须使用同一提交已成功的 `Game validation` 与 `Native RenPy PWA and shared materials` CI 产物。发布流程不重新构建，并保留旧版本标签与下载资产。

| 交付物 | 精确 CI artifact | 文件 |
|---|---|---|
| Windows 玩家包 | `windows-${candidateSHA}` | `BeforeTheRainStops-1.2.0-win.zip` |
| PWA 玩家包及证据 | `Rain-Web-${candidateSHA}` | `BeforeTheRainStops-1.2.0-web.zip`、`reports/web-build.json` |
| 可复用素材 | `Rain-Reusable-Materials-${candidateSHA}` | `v1.1.0` kit 与 catalog |
| 公开浏览器互动证据 | `Rain-Public-PWA-${candidateSHA}-${runAttempt}` | 实际菜单 / 保存 / 断网重开 / 读取 |

Windows ZIP CRC、version/build_info、85资源哈希与独立 EXE / 跨进程 / 真实v1.1.0旧档结果必须一致。PWA ZIP SHA-256 与公开站点 worker revision 必须匹配同一 CI metadata。发布前写入实际 tag / commit、两个 ZIP 字节数与 SHA-256；发布后回读公开下载验证相同字节，才可把本页状态更新为已发布。

当前状态：本轮平台工程候选，公开 CI、Pages 与 v1.2.0 Windows 下载由最终推送后的实际结果补充。没有把旧 v1.1.1 下载链接标为新版本。
