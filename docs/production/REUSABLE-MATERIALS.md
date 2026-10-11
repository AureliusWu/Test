# 可复用素材与制作工具 v1.1.0

三个仓库使用同一份素材校验和导出接口；各自的 `REUSABLE-ASSETS.json` 记录当前文件、来源、SHA-256、许可证和复用范围。`REUSE-MANIFEST.json` 锁定共用工具与模板的 LF 文本哈希，换行风格不会导致 Windows 与 CI 的假漂移。

## 使用

在仓库根目录执行：

```sh
node --test scripts/vn-materials.test.mjs
node scripts/vn-materials.mjs verify
node scripts/vn-materials.mjs export .reuse-kit/v1.1.0
```

导出目录必须是新的 `.reuse-kit/<名称>`；再次导出请使用新名称，工具不会覆盖已有文件。所有校验通过才开始导出。目录包含 MANIFEST.json、文件原有相对路径及逐项许可证；原图和运行文件保留二进制字节，文本规范为 LF。导出目录被 Git 忽略，可打包为团队交接素材。

`licensed` 表示文件按记录的许可证复用；`recipe` 表示工具或制作流程，需要目标引擎、依赖和参数适配；`project-only` 只用于原作品的来源核验，不进入通用导出包。不得把项目代码的 MIT 许可自动套到人物、CG、声音或 AI 图像上。

## 已沉淀的素材

- 三仓一致的剧情结构检查、素材校验/导出、来源记录模板、提示词模板和双端验收清单。
- 各引擎的真实 PWA 交付适配器：Vite 的完整缓存/安装更新状态，Ren'Py 的官方 Web 构建后处理。更换应用名、部署 scope 与原生内容后再运行目标作品的验收。
- Rain 的 Adobe 字体、Ren'Py 基础 GUI、原创程序生成占位声音，以及图像/声音加工流程；按各文件的 MIT/OFL 许可附带原文。工程候选素材仍需作品负责人确认审美与内容适用性。
- NetLove、Healing 的 OFL 字体子集和字体/图像加工工具；Healing 另有原创 Web Audio 配乐与雨声制作流程。
- 三个作品的人物与场景素材均保留独立目录和身份。NetLove 和 Rain 的已入库源文件可追溯；Healing 部分素材仅有运行 WebP、生成请求和哈希，索引明确记为 `not-in-repository`，后续补齐原图时更新索引并重新校验。

字体子集只覆盖原作品的剧情和界面，移植时须重新采集目标 JSON 正文与界面字形。OFL 名称限制和许可文本随字体携带。Ren'Py 工具不能直接替代 Vite 图集流水线；导出包保留原路径、来源和引擎边界。

## 更新规则

新素材按 templates/ASSET-RECORD.json 填写记录。`files` 使用仓库相对路径，禁止绝对路径、上级目录和外部链接。二进制用原字节 SHA-256，文本先 CRLF→LF 再计算。许可范围不明确的文件使用 project-only。保留实际提示词、源图和许可；缺少来源须明确写明，不能用成品反向冒充原图。

共用工具变更时同步三个仓库，升级制作契约、更新 REUSE-MANIFEST，并运行三仓校验和原生路线测试。素材索引的 sourceCommit 是本轮整理基线，具体导出文件由 SHA-256 精确标识；发布证明仍以对应版本的实际安装包和线上 PWA 验收为准。
