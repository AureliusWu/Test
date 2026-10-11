# 三项目视觉小说制作契约 v1.1.0

同步日期：2026-10-11。适用仓库：[Rain](https://github.com/AureliusWu/Rain)、[NetLove](https://github.com/AureliusWu/NetLove)、[Healing](https://github.com/AureliusWu/Healing)。旧文档的 Test 对应 Rain，Project1 对应 Healing；既有版本证明保留原仓库名和提交。

三个作品共用制作方法、检查接口和可复用素材包，各自保留故事、美术与原生引擎。共用文件及 LF 文本哈希由各仓库 docs/production/REUSE-MANIFEST.json 锁定；作品素材分别记录在 REUSABLE-ASSETS.json。共用更新必须在三仓验证，不能只复制文件而宣称平台已验收。

## 能力对照与复用边界

| 能力 | Rain | NetLove / Healing | 共用接口与验收 |
| --- | --- | --- | --- |
| 剧情事实来源 | Ren'Py 8.5.3 + game/data/story.json 编译 | React/Vite + JSON 原生执行器 | vn-contract 检查图结构；各自验证状态路线 |
| Windows | 原生 Ren'Py EXE | Electron EXE、ASAR | 发行包实际启动、阅读、保存恢复和退出 |
| Web/PWA | 官方 Ren'Py Web/WASM 产物，独立后处理 | Vite + PWA 产物 | 相对子路径、独立缓存/scope、完整缓存成功才承诺离线 |
| 阅读控制 | Ren'Py screen 与平台输入 | 底部透明阅读层、隐藏暂停、旋转保持位置 | 相同用户目标，各引擎保留具体 UI/存档实现 |
| 存档 | Ren'Py 原生槽位与迁移验证 | 各自稳定故事 ID、浏览器/JSON 存档 | 独立命名空间；导入不信任外部进度与分数 |
| 素材来源 | 原图/音频、提示词注册表与运行哈希 | 图像/字形加工与生成请求 | vn-materials 校验、许可和素材导出 |
| 素材可移植性 | OFL 字体、MIT GUI/程序音频、加工流程 | OFL 字体子集、加工流程；Healing Web Audio 配乐 | 许可随包；人物/CG/声音身份不跨作品混用 |

NetLove 的成年人物设定、Healing 的校园角色设定和 Rain 的 Ren'Py 规则只作用于各自作品。共用模板读取目标作品的角色设定，不把单个作品的年龄、剧情或美术当成全局约束。

## 共用检查与素材导出

在仓库根目录运行：

```sh
node scripts/vn-contract.mjs path/to/story.json
node --test scripts/vn-materials.test.mjs
node scripts/vn-materials.mjs verify
node scripts/vn-materials.mjs export .reuse-kit/v1.1.0
```

vn-contract 接受 scenes 或 nodes，检查入口、唯一 ID、台词非空、选项冲突、目标存在、可达性、意外环路和未完成终点。Rain 的 routes 作为结构分支读取；条件是否成立由 Ren'Py 原生验证器判断。Healing 通过 tests/shared-vn.test.ts 适配 resolve、bridge 和旧段落偏移。图路径数不能替代真实状态路线数。

vn-materials 检查真实字节、许可证引用、源文件状态和共用文件哈希；导出 licensed/recipe 条目，附带许可并排除 project-only 人物、CG 和声音。详见 [REUSABLE-MATERIALS.md](REUSABLE-MATERIALS.md) 与 templates。Healing 部分图像缺少入库原图，索引明示缺口，不能宣称完整生成复现。

## 新作品移植清单

1. 记录来源提交和逐项许可证，重新建立故事 ID、应用 ID、存储/缓存前缀及安装文件名前缀。
2. 替换剧本、人物图集、专用夹具、窗口标题与发行元数据；历史证明不改写成新作品证明。
3. 正文只有一个事实来源。稳定台词与存档位置；路线、回看和读档由原生执行器重建。
4. 保存生成原图、实际请求、参考来源、尺寸/alpha 和哈希。编码工具只加工格式，工程通过与作品负责人创意审批分别记录。
5. 字体子集覆盖全部 JSON 正文和界面文字，移植时重新生成；字体授权随播放器交付。
6. PWA 使用部署 scope 标识自己的缓存；只删除本应用旧缓存。等待当前注册成功，资源缺失时不冒报离线可用。
7. 验证 1440×900、412×915、568×320、844×390，覆盖选择/结局、读档、隐藏恢复、旋转、断网重开与缓存更新。
8. 源码运行、实际 Windows 包、公开 PWA 分别留证。至少三次同环境性能样本；首次新增平台明确记录首个基线。
9. 先构建与运行，再推送并检查精确提交的 CI/部署；公开版本不覆盖，未执行项写明限制。

## 本轮维护依据

v1.0 沉淀了 Healing 的全窗口阅读/PWA、Rain 的资产追溯/实际 Windows 验证和 NetLove 的 JSON 字形及引擎无关检查。本轮补齐 Rain Web 平台、核验两个 Electron 作品的缓存部署隔离，并把素材索引、校验、导出和模板变成可运行的工具。发布结果以各仓本轮测试与版本文档的实际证据为准。
