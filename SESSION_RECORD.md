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
