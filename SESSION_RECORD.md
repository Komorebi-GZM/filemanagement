# SESSION_RECORD.md

## [2026-07-29] 项目接管 + 代码审查修复

**背景：** 首次接管项目，先进行任务交接了解项目全貌，然后发起代码审查，最后修复全部审查发现的问题。

**完成工作：**
- 全面探索项目结构、架构、代码库状态
- 发起代码审查（review commits: 4386650..061d090）
- 修复 11 个审查问题 + 1 个额外 bug：
  - Critical: 侧边栏计数在 inspector 标签增删后不同步 → `_update_tag_tree()` 调用
  - Important: `hasattr` 死代码路径移除 → 直接调用 ViewModel 方法
  - Important: CommandPalette 与父组件解耦 → 显式传入 vm 参数
  - Important: `count_files` DB 异常保护 → try/except + 默认返回 0
  - Important: 预览面板重复"简介"section 删除
  - Minor: 冗余局部 import 删除
  - Minor: TagChipWidget 改用主题色（palette）
  - Minor: 测试改用 itemActivated.emit 而非私有方法
  - Minor: MockVM 清理死方法
  - Minor: QSpacerItem 冗余调用清理
  - Bonus: 图片预览 `QTextEdit.setPixmap()` 崩溃 → 改用 base64 HTML 内嵌
- 建立会话记录规范（AGENTS.md + SESSION_RECORD.md）

**当前状态：**
- 14 个测试全部通过（0.83s）
- 应用可正常运行、打包
- `search_history` 表仍未写入（占位）
- `watchdog` 依赖未引入（占位）

**待办事项：**
- 考虑实现 `search_history` 写入逻辑
- 如需文件监控功能，引入 `watchdog`

**决策记录：**
- 会话记录文件命名为 `SESSION_RECORD.md`，置于项目根目录
- 记录格式采用 Markdown 二级标题 + 关键字段（背景/完成工作/当前状态/待办事项/决策记录）

## [2026-07-29] V1.2 设计 + 实现

**背景：** 完成 V1.2 版本的设计、实现、测试和发布

**完成工作：**
- 编写 V1.2 PRD：watchdog 文件监控（P0）+ search_history 写入（P1）
- 编写实现计划（6 个 Task）
- 实现并审查 6 个 Task：
  - Task 1: FileMonitor 服务层（QTimer debounce + watchdog Observer）
  - Task 2: Database 方法（find_by_hash, update_file_path, record_search 等 8 方法）
  - Task 3: ViewModel 事件处理 + search_history 写入
  - Task 4: Command palette ↑/↓ 历史导航
  - Task 5: main.py 集成 FileMonitor 生命周期
  - Task 6: 集成测试
- 最终 review 修复：_db None guard、command palette 搜索执行、delete_old_searches 排序、消除 dead code
- Push 到 origin/master (9f2144a..cabb400)

**当前状态：**
- 37 passed, 4 skipped（全部通过）
- 新增文件：`src/app/services/`、`src/app/services/file_monitor.py`、`tests/services/test_file_monitor.py`、`tests/services/test_file_monitor_integration.py`
- 修改文件：`database.py`、`main_viewmodel.py`、`command_palette.py`、`main_window.py`、`main.py`
- 测试文件：`test_file_sync.py`、`test_search_history.py`、`test_command_palette.py`
- V1.2 已推送到 origin/master

**待办事项：**
- V1.3：全文搜索（FTS）推迟至 V1.3
- V1.2 遗留：SHA256 计算在主线程阻塞 UI（已知问题，后续优化）

**决策记录：**
- 数据库 Schema 不变，不增加 inode 字段（跨平台不可靠，file_hash 已足够）
- `delete_old_searches` 采用 `ORDER BY created_at DESC, id DESC` + `DELETE WHERE id <= ?` 而非纯 `created_at` 比较（处理同时间戳边缘情况）
- 删除事件 path-only 匹配是正确方案（文件已消失，无法获取 size）

## [2026-07-29] 实现 Task 3: IndexWorker — Background FTS Indexing

**背景：** V1.3 Task 3 — 创建 IndexWorker 后台队列工作线程处理 FTS 索引

**完成工作：**
- 创建 `src/app/services/index_worker.py` — IndexWorker(QObject)，包含 enqueue / enqueue_batch / start / stop 接口
- 3 个信号：indexing_progress, indexing_finished, index_updated
- 创建 `tests/services/test_index_worker.py` — 2 个测试（单文件 + 批量）
- 测试全部通过（2/2），完整套件 56 passed, 4 skipped

**当前状态：**
- IndexWorker 已实现并提交 (01405e1)
- TDD 中发现并修复了 spec 中的 2 个 bug：内层循环空队列无限循环、_total=0 时过早触发 indexing_finished
- 测试 fixture 改用 file-based SQLite 以支持跨线程连接

**待办事项：**
- 后续 Task：FTS 搜索 UI、结果展示、增量索引

**决策记录：**
- 测试 fixture 使用 tmp_path 文件数据库而非 :memory:（因为 IndexWorker 在后台线程创建独立 DB 连接，:memory: 数据库连接间不共享）

## [2026-07-29] Fix 2 Critical + 4 Important issues from V1.3 whole-branch review

**背景：** V1.3 全分支最终审查发现 6 个问题需修复

**完成工作：**
- **Issue 1 (CRITICAL):** `import_files()` 连接 `worker.file_imported` → `self._index_worker.enqueue`，确保导入的文件被索引
- **Issue 2 (CRITICAL):** `search_fts()` 查询补充 `file_hash`, `create_time`, `created_at`, `updated_at`, `is_deleted`, `deleted_at` 列；`search_files()` FTS FileRecord 构造使用完整字段
- **Issue 3 (IMPORTANT):** `enqueue_batch()` 在 `_total == 0` 时发射 `indexing_finished`；`_process_queue()` 退出条件移除 `_total > 0` 守卫
- **Issue 4 (IMPORTANT):** 并发导入添加 `logger.warning` 提示
- **Issue 5 (IMPORTANT):** 修正 `_total` 跟踪（与 Issue 3 同修复）
- **测试修复：** `tests/db/test_fts.py` CREATE TABLE 补充缺失列（file_hash, create_time, created_at, updated_at, deleted_at）

**当前状态：**
- 63 passed, 4 skipped（全部通过）
- 修改文件：`main_viewmodel.py`, `database.py`, `index_worker.py`, `test_fts.py`
- HEAD SHA: `becc4a6`（amend 后）

**待办事项：**
- 无

**决策记录：**
- 测试中 CREATE TABLE 必须与实际 schema 的 files 表列匹配，否则 `search_fts` 查询会因引用不存在列而失败

## [2026-07-30] V1.3 最终交付 + UI 美化

**背景：** V1.3 修复审查完毕后，用户要求完成正式交付，并对前端界面进行美化

**完成工作：**
- 全部 6 个修复问题已确认通过代码审查（2 Critical + 4 Important）
- 交付 V1.3 到 origin/master + 打 tag `v1.3-fts-async`
- UI 美化：
  - 创建 `src/app/ui/theme.py` — 中心化 QSS 样式表（专业蓝 #2563EB + 琥珀 #D97706 配色）
  - 重写 `TagChipWidget` → 彩色药丸设计（基于 tag_name hash 的 12 色调色板）
  - `FileListWidget` → OS 原生文件图标（`QFileIconProvider`）
  - 搜索栏 → 右侧添加放大镜图标（QPainter 绘制）+ 快捷键提示
  - `CommandPalette` → 阴影效果 + 圆角边框 + 居中浮动定位
  - 自定义 QSS：QPushButton、QLineEdit、QComboBox、QTreeWidget、QListWidget、QTabWidget、QSplitter、QScrollBar、QProgressBar、QStatusBar、QMenu/QMenuBar、对话框等
  - 索引进度标签 → 使用图标前缀，完成后 2s 自动消失
- 测试：63 passed, 4 skipped，0 回归

**当前状态：**
- V1.3 已发布（tag: `v1.3-fts-async`）
- UI 视觉全面更新，保留全部原有功能
- 无新增外部依赖，PyInstaller 兼容

**待办事项：**
- 无

**决策记录：**
- QSS 样式使用 f-string 注入 Color 常量，方便后续主题切换
- 不使用外部图标库（Phosphor/Heroicons），改用 `QFileIconProvider` + `QPainter` 绘制
- 不使用 Google Fonts（PyInstaller 打包复杂），退化为 Segoe UI 系统字体

## [2026-11-15] 审查问题修复 + 仓库清理 + PR #3 / PR #1 处理

**背景：** 完成全仓库分支与文件全面审查后，按计划创建修复分支与 PR #3，逐项修复审计发现的 UI/ViewModel bug、清理仓库历史遗留文件，并处理已过时冲突的 PR #1。

**完成工作：**
- **分支与 PR：** 基于 `master` 创建 `fix/audit-bugs-and-cleanup` 并开启 PR #3；关闭过时冲突的 PR #1（`optimize-architecture-5931458531709047786`），同时提取其中的 `get_all_drive_letters` SQL 优化
- **文档与打包对齐：**
  - 更新 `README.md` 从 `v1.0.0` 到 `V1.3`（补充 Services 层、FTS5 全文检索、异步导入、`Ctrl+K` 命令面板、`py311-pack` 环境及表结构说明）
  - 修正 `package.bat` 输出提示目录为 `dist_new`，与 `filemanagement.spec` 保持一致
- **仓库清理：** `git rm -r --cached .superpowers/` 取消追踪已在 `.gitignore` 中的 `.superpowers/` 目录
- **Bug 修复与功能补全：**
  - `MainSignals.files_updated` 改为 `pyqtSignal(object)`，ViewModel 发出 `None` 触发重载，`MainWindow._on_files_updated` 同步刷新文件列表与侧边栏计数，保留空搜索/筛选结果 `[]` 清空列表行为
  - `ImportWorker` 新增 `import_finished(int)` 信号并在完成后发射实际导入/恢复数量（同时持有 `_thread` 引用避免提前回收）；`MainViewModel` 转发至 `MainSignals.import_finished`，`MainWindow._on_import_finished` 刷新筛选器与列表后弹窗汇报真实数量
  - `MainWindow._load_filter_options` 使用 `blockSignals` 避免重建下拉框时重复触发筛选查询
  - 接通 `FileListWidget`（添加标签、添加注释 `NoteDialog`、添加印记 `ImprintDialog`、软删除）与 `TagTreeWidget`（添加子/根标签、删除标签且保护虚拟根节点）右键菜单信号，并改用 `main_window` 引用替代脆弱父链查找
  - `MainViewModel.get_all_drive_letters` 改用 SQLite `SUBSTR` 直接查询盘符（复用自 PR #1）
- **新增测试：** 补充 `tests/ui/test_main_window_fixes.py`，并在 `test_async_import.py` 与 `test_main_viewmodel_counts.py` 增加回归测试

**当前状态：**
- 测试套件（`/tmp/fm-venv`，`watchdog==4.0.2`，`QT_QPA_PLATFORM=offscreen`）：`69 passed, 4 skipped`（4 个 skipped 为默认跳过的 watchdog 真实文件系统集成测试）
- 注意：`watchdog >= 7.x` 对 `PatternMatchingEventHandler(patterns=["*"])` 改用了 `PurePath.full_match`，本次测试使用 `watchdog==4.0.2` 验证通过（`requirements.txt` 当前仅约束 `watchdog>=4.0.1`）
- `dist_new/文件管理系统.exe` 仍为 V1.2 构建产物，需在 Windows `py311-pack` 环境执行 `package.bat` 重新打包

**待办事项：**
- 审查并合并 PR #3 到 `master`
- 在 Windows 环境运行 `package.bat` 更新 `dist_new/文件管理系统.exe`
- 可选：在 `requirements.txt` 中限制 `watchdog>=4.0.1,<5` 或将 `FileMonitor` 的 `patterns` 调整为 `None` 以兼容 watchdog 7.x；接入 `CommandPalette` 实时标签过滤（`fuzzy_search_tags`）

**决策记录：**
- `files_updated` 使用 `pyqtSignal(object)` 并以 `None` 表示“全量重查刷新”，以 `[]` 表示“筛选/搜索结果为空”，避免两者语义冲突
- `ImportWorker` 新增独立 `import_finished(int)` 信号而非改动 `finished()` 签名，确保既有 0 参数槽函数（如 `deleteLater` 和状态重置）兼容

## [2026-11-15] 续：watchdog 7.x 兼容修复与 CommandPalette 实时标签过滤

**背景：** 根据用户确认，在 PR #3（`fix/audit-bugs-and-cleanup`）中继续完成待办项：解决 `FileMonitor` 在 `watchdog >= 7.x` 下事件失效的问题，并将 `CommandPalette` 的实时标签过滤接入 `MainViewModel.fuzzy_search_tags`。

**完成工作：**
- **FileMonitor 跨版本兼容（`src/app/services/file_monitor.py`）：**
  - `_FileChangeHandler` 将 `patterns=["*"]` 调整为 `patterns=None`（在 watchdog 4.x 回退为 `["*"]`，在 7.x+ 回退为 `["**"]`）
  - 展开 `IGNORE_PATTERNS` 与 `IGNORE_DIRS` 为 `pat` / `**/{pat}` 与 `{dir}/**` / `**/{dir}/**` 形式，确保临时文件与 `.git` / `__pycache__` / `.svn` 在 watchdog 4.x 与 7.x+ 下均能正确忽略
- **CommandPalette 实时标签过滤（`src/app/ui/command_palette.py`）：**
  - `set_context_file()` 清理旧输入时不触发多余搜索事件
  - `_on_text_changed()` 与 `_load_tags()` 在标签模式下实时调用 `vm.fuzzy_search_tags()`（对仅实现 `get_all_tags()` 的测试 mock 提供降级过滤），并自动高亮第一条匹配项
  - `_on_return_pressed()` 在标签模式下激活当前/首条匹配标签而非触发文件搜索
- **新增测试：** 在 `tests/services/test_file_monitor.py` 新增忽略规则回归测试；在 `tests/ui/test_command_palette.py` 新增实时标签过滤、回车选中与状态清理测试

**当前状态：**
- 全量测试在 **watchdog 4.0.2**（`/tmp/fm-venv`）下：`71 passed, 4 skipped`
- 全量测试在 **watchdog 7.1.0**（`/tmp/fm-venv-wd7`）下：`71 passed, 4 skipped`
- 4 个 skipped 为默认跳过的 `test_file_monitor_integration.py` 集成测试

**待办事项：**
- 审查并合并 PR #3 到 `master`
- 在 Windows 环境运行 `package.bat` 更新 `dist_new/文件管理系统.exe`

**决策记录：**
- 不在 `requirements.txt` 锁死 `watchdog<5`，而是在 `_FileChangeHandler` 使用 `patterns=None` 与 `**/` 前缀通配规则以同时兼容 watchdog 4.x 与 7.x+
- `CommandPalette._load_tags()` 对空查询保留调用 `get_all_tags()`，仅在非空查询时调用 `fuzzy_search_tags()`，兼顾既有测试 mock 兼容性

## [2026-11-15] Win + macOS 双平台开发兼容线调整（新 PR，基于 PR #3 分支）

**背景：** 用户确认项目后续将在 Windows 与 macOS 上共同开发，需调整依赖/脚本/打包的兼容基线，并以独立 PR 提交。

**完成工作：**
- `requirements.txt`：转为 LF；`PyQt5>=5.15.10,<5.16`（macOS arm64/universal2 wheel）、`watchdog>=4.0.1,<8`（4.0.2 与 7.1.0 均已验证）
- 新增 `.gitattributes`（源码 LF、`.bat` CRLF、二进制不转换）
- 新增 `start.sh` / `package.sh`（macOS/Linux，优先 `py311-pack`，可用 `FM_PYTHON` 覆盖）
- `filemanagement.spec` 按 `sys.platform` 分支：Windows 保持 onefile；macOS 使用 onedir + `.app`（BUNDLE）
- `tests/test_env.py`：Python 版本断言由 `== 3.11` 放宽为 `>= 3.11`
- `README.md`：补充双平台环境、脚本、打包与平台差异说明

**当前状态：**
- Linux 上 watchdog 4.0.2 / 7.1.0 全量测试：`71 passed, 4 skipped`
- macOS `.app` 打包与 Windows 打包未在本环境实测（PyInstaller 不支持交叉编译），需在对应系统上跑一次 `package.sh` / `package.bat` 验证

**待办事项：**
- 在 Mac 上实机验证启动、`package.sh` 与 `.app`；视需要配置签名/公证与 `universal2`
- 「位置」筛选目前基于盘符，macOS 下仅显示「所有位置」，可后续改为按卷（`/Volumes/*`）
- PR #3 合并后，将本 PR 基底改为 `master`

**决策记录：**
- 不锁定 `watchdog<5`，上限设 `<8` 以覆盖已验证版本
- macOS 采用 onedir + `.app`，因 onefile 窗口应用在 macOS 上被 PyInstaller 弃用
- 新 PR 基于 `fix/audit-bugs-and-cleanup`（堆叠 PR），避免与 PR #3 中的 README/file_monitor 改动冲突

