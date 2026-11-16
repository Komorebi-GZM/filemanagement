# Windows + macOS 跨平台「位置筛选」与「路径规范化」设计方案与测试用例

> 状态：**Draft（设计方案与测试用例，暂不执行代码实现）**  
> 日期：2026-11-15  
> 前置依赖：PR #3（`fix/audit-bugs-and-cleanup`）、PR #4（`chore/cross-platform-win-mac`）

## 1. 背景与前提约束

经 `/grill-me` 逐项确认，本设计遵循以下核心约束：

1. **数据库不跨机共享**：`data/users/<user>/app.sqlite3` 仅在本机使用，`files.full_path` 只需在本机路径体系内自洽，无需引入跨平台可移植相对路径。
2. **无 Schema 变更**：不修改 `src/app/db/schema.sql`，位置筛选与路径规范化全部通过查询推导与统一工具函数完成。
3. **跨平台位置抽象**：
   - **Windows**：按盘符聚合（如 `C:`、`D:`，统一大写）。
   - **macOS**：`/Volumes/<name>/...` 聚合为外接/独立卷名 `<name>`（查询键 `/Volumes/<name>`）；其余 `/...` 路径归入 `Macintosh HD`（查询键 `/`）。
4. **向后兼容**：`MainViewModel` 保留 `get_all_drive_letters()` 与 `list_files(..., drive_letter=...)` 作为兼容别名，新增 `get_all_locations()` 与 `list_files(..., location=...)`。

---

## 2. 详细设计方案

### 2.1 统一路径工具模块：`src/app/core/path_utils.py`

1. **`normalize_path(path: str | Path) -> str`**
   - 执行 `Path(path).expanduser().resolve(strict=False)`，消除 macOS 上 `/tmp` → `/private/tmp`、`/var` → `/private/var` 软链接及相对路径差异。
   - 执行 `unicodedata.normalize("NFC", path_str)`，消除 macOS APFS/HFS+ 下 FSEvents 返回 NFD 分解字符与用户输入 NFC 组合字符的不一致。
   - 对 Windows 盘符路径（`^[A-Za-z]:`）将盘符首字母统一规范为大写（如 `c:\docs` → `C:\docs`）。

2. **`extract_location(full_path: str) -> Optional[tuple[str, str]]`**
   - 返回 `(display_label, location_key)`：
     - Windows 盘符路径 `^[A-Za-z]:` → `(f"{drive.upper()}:", f"{drive.upper()}:")`
     - macOS/POSIX `/Volumes/<name>` 或 `/Volumes/<name>/...` → `("<name>", "/Volumes/<name>")`
     - 其他 POSIX `/...` → `("Macintosh HD", "/")`
     - 空字符串或相对路径 → `None`

3. **`escape_like(value: str) -> str`**
   - 转义 SQLite `LIKE` 通配符 `\`、`%`、`_`，配合 `ESCAPE '\'` 使用，防止卷名/路径含特殊字符时误匹配。

---

### 2.2 数据库与 ViewModel 路径匹配策略

涉及文件：`src/app/db/database.py`、`src/app/services/import_worker.py`、`src/app/viewmodel/main_viewmodel.py`、`src/main.py`

- **写入侧规范化**：
  - `ImportWorker._do_import()` 与 `MainViewModel._handle_file_moved()` 写入 `files.full_path` 前统一调用 `normalize_path()`。
- **查询侧双阶段匹配**（用于 `Database.find_by_path_and_size`、`MainViewModel._on_file_system_changed` 的 `modified`/`deleted` 事件、`MainViewModel._handle_file_deleted_by_path`）：
  1. **快路径**：`normalize_path(event_path)` 后执行 `WHERE full_path = ? AND is_deleted = 0`（命中 `idx_files_full_path` 索引）。
  2. **大小写/Unicode 兜底（Windows / macOS 默认大小写不敏感文件系统）**：快路径未命中时，执行 `WHERE full_path = ? COLLATE NOCASE AND is_deleted = 0`，并在 Python 侧以 `normalize_path(row["full_path"]).casefold() == norm_target.casefold()` 校验非 ASCII 字符场景。
  3. **哈希兜底**：`modified` 事件保留原有的 `file_hash` 匹配路径。

---

### 2.3 ViewModel 与 UI「位置」筛选接口

- **ViewModel（`src/app/viewmodel/main_viewmodel.py`）**：
  - 新增 `get_all_locations() -> list[tuple[str, str]]`：查询活跃文件 `full_path`，调用 `extract_location()` 去重并排序输出 `(label, key)` 列表。
  - 保留 `get_all_drive_letters() -> list[str]` 作为向后兼容别名。
  - `list_files(..., location: Optional[str] = None, drive_letter: Optional[str] = None)`：
    - `effective_loc = location if location is not None else drive_letter`
    - Windows 盘符（如 `"C:"`）：`UPPER(SUBSTR(full_path, 1, 2)) = ?`
    - 独立卷（如 `"/Volumes/USB"`）：`(full_path = ? OR full_path LIKE ? ESCAPE '\')`，参数 `(loc, f"{escape_like(loc)}/%")`，避免 `/Volumes/USB` 误匹配 `/Volumes/USB2`。
    - 系统根目录（`"/"`）：`(full_path LIKE '/%' AND full_path NOT LIKE '/Volumes/%')`。
- **UI（`src/app/ui/main_window.py`）**：
  - `_load_filter_options()` 调用 `vm.get_all_locations()`（若 mock 未实现则降级调用 `get_all_drive_letters()`），使用 `filter_location_combo.addItem(label, key)` 绑定显示名称与查询键。
  - `_on_filter_change()` 读取 `filter_location_combo.currentData()`（若为 `None` 回退 `currentText()`）并传入 `vm.list_files(..., location=...)`。

---

## 3. 测试用例设计（Test Cases）

### 3.1 `tests/core/test_path_utils.py`（纯单元测试）

| 用例名 | 输入/场景 | 预期结果 |
|---|---|---|
| `test_normalize_path_unicode_nfc` | macOS NFD 字符串（`unicodedata.normalize("NFD", "设计稿.txt")`） | 输出等于 NFC 形式，`unicodedata.is_normalized("NFC", out)` 为 `True` |
| `test_normalize_path_symlink_resolution` | `tmp_path` 下真实目录与软链接指向同一文件 | 两者 `normalize_path()` 结果完全一致 |
| `test_normalize_path_windows_drive_upper` | Windows 路径 `"c:/Docs/a.txt"` / `"c:\\Docs\\a.txt"` | 盘符首字母规范为 `"C:"` |
| `test_extract_location_windows_drives` | `"C:\\a.txt"`, `"d:/work/b.md"` | 返回 `("C:", "C:")`、`("D:", "D:")` |
| `test_extract_location_macos_volumes` | `"/Volumes/Backup/2026/a.pdf"`, `"/Volumes/USB2/x.txt"` | 返回 `("Backup", "/Volumes/Backup")`、`("USB2", "/Volumes/USB2")` |
| `test_extract_location_macos_root` | `"/Users/alice/Desktop/note.md"`, `"/tmp/a.txt"` | 返回 `("Macintosh HD", "/")` |
| `test_extract_location_invalid_or_empty` | `""`, `"relative/path.txt"` | 返回 `None`，不抛异常 |

### 3.2 `tests/viewmodel/test_cross_platform_locations.py`（ViewModel + SQLite）

| 用例名 | 测试数据与操作 | 预期结果 |
|---|---|---|
| `test_get_all_locations_mixed_and_deleted` | 插入 `/Users/a/1.txt`、`/Volumes/USB/2.txt`、`/Volumes/USB2/3.txt`、`C:\a\4.txt`、`d:\b\5.txt` 及已删除记录 `/Volumes/Old/6.txt` | 不含 `Old`；合并 `/` 为 `("Macintosh HD", "/")`；包含 `USB`、`USB2`、`C:`、`D:` |
| `test_list_files_filter_macos_root_excludes_volumes` | 调用 `vm.list_files(location="/")` | 仅返回 `/Users/a/1.txt`，不包含 `/Volumes/USB/...` |
| `test_list_files_filter_volume_boundary` | 调用 `vm.list_files(location="/Volumes/USB")` | 仅返回 `/Volumes/USB/2.txt`，不误匹配 `/Volumes/USB2/3.txt` |
| `test_list_files_filter_like_special_chars` | 卷名为 `/Volumes/100%_Disk/a.txt` 与 `/Volumes/1000Disk/b.txt` | 筛选 `/Volumes/100%_Disk` 仅返回 `a.txt` |
| `test_list_files_windows_drive_case_insensitive` | 存入 `c:\work\a.txt` 与 `C:\work\b.txt`，分别调用 `location="C:"` 与 `drive_letter="C:"` | 两者均返回 `a.txt` 和 `b.txt` |

### 3.3 `tests/viewmodel/test_path_matching_cross_platform.py`（监控事件与路径匹配）

| 用例名 | 场景 | 预期结果 |
|---|---|---|
| `test_deleted_event_matches_nfd_unicode_path` | 库中存入 NFC 路径 `/dir/设计稿.txt`，模拟 FSEvents 发出 NFD 路径的 `deleted` 事件 | `_on_file_system_changed` 成功软删除该记录并清理 FTS |
| `test_deleted_event_matches_symlink_alias` | 文件通过 `/real/dir/a.txt` 导入，监控发出 `/symlink/dir/a.txt` 的 `deleted` 事件 | `normalize_path()` 解析软链接后命中并软删除 |
| `test_modified_event_case_insensitive_fallback` | 在 `win32`/`darwin` 模式下，库中为 `/Users/Alice/Doc.txt`，事件为 `/users/alice/doc.txt` | 成功定位 `file_id` 并更新 `file_size`/`modify_time` |
| `test_moved_event_stores_normalized_path` | 触发 `moved` 事件到包含 NFD 或符号链接的新路径 | `files.full_path` 更新为规范化后的 NFC 真实路径 |

### 3.4 `tests/ui/test_main_window_locations.py`（PyQt5 UI）

| 用例名 | 场景 | 预期结果 |
|---|---|---|
| `test_location_combo_displays_label_passes_key` | `vm.get_all_locations()` 返回 `[("Macintosh HD", "/"), ("Backup", "/Volumes/Backup")]` | 下拉框显示 `"所有位置"`、`"Macintosh HD"`、`"Backup"`；选中时分别传入 `location="/"` 与 `location="/Volumes/Backup"` |
| `test_location_combo_legacy_vm_fallback` | Mock VM 仅实现 `get_all_drive_letters()`（`["C:", "D:"]`） | 下拉框正常加载 `C:`、`D:`，无异常 |
