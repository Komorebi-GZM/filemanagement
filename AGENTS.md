# AGENTS.md

## 项目概览

本地文件多标记交叉管理系统（v1.0.0），基于 PyQt5 + SQLite 的桌面文件管理工具，采用 MVVM 架构。

## 开发命令

| 操作 | 命令 |
|------|------|
| 运行应用 | `conda run -n py311-pack python -m src.main` |
| 安装依赖 | `pip install -r requirements.txt` |
| 运行全部测试 | `pytest` |
| 运行单个测试 | `pytest tests/path/to/test.py -k test_name` |
| 打包 exe | `package.bat`（需 `py311-pack` conda 环境 + pyinstaller） |

## 关键约定

- **Python 版本**：开发环境使用 Python 3.11（conda 环境 `py311-pack`）
- **入口文件**：`src/main.py`，通过 `python -m src.main` 启动
- **测试框架**：pytest + pytest-qt，`pytest.ini` 设置 `pythonpath = .`
- **数据库**：SQLite，schema 定义在 `src/app/db/schema.sql`，测试使用 `:memory:` 数据库
- **打包工具**：PyInstaller，配置在 `filemanagement.spec`，产物输出到 `dist_new/`
- **会话记录**：每次对话结束后，在 `SESSION_RECORD.md` 追加当前会话记录，便于任务交接

## 架构要点

- **MVVM 分层**：`src/app/model/`（数据类）→ `src/app/viewmodel/`（业务逻辑+信号）→ `src/app/ui/`（PyQt5 界面）
- **数据库表**：`files`、`tags`、`file_tag_relation`、`search_history`、`file_notes`、`file_imprints`
- **路径解析**：`src/app/core/paths.py` 管理数据目录（`data/users/<user>/app.sqlite3`）
- **PyInstaller 兼容**：`src/main.py` 通过 `sys.frozen` 和 `sys._MEIPASS` 处理打包后路径

## 测试注意

- `tests/conftest.py` 提供 `db_session` fixture（内存数据库，自动加载 schema）
- UI 测试使用 pytest-qt，需要 Qt 环境
- 测试文件位于 `tests/ui/` 和 `tests/viewmodel/`

## 不要做的事

- 不要修改 `data/` 目录下的数据库文件（已加入 `.gitignore`）
- 不要直接修改 `dist_new/` 下的打包产物
- 不要绕过 ViewModel 直接操作数据库（UI 层应通过 ViewModel 交互）

## 会话记录规范

每次开发对话结束时，必须在 `SESSION_RECORD.md` 文件底部追加一条记录。

### 记录格式

```
## [YYYY-MM-DD] 会话摘要（一句话概括）

**背景：** 本次会话的上下文或触发原因
**完成工作：** 清单列出完成的改动
**当前状态：** 关键状态说明（测试结果、已知问题等）
**待办事项：** 后续需要处理的事项
**决策记录：** 本次会话中做出的架构/设计决策
```

AGENTS.md 本身不包含对话状态信息，对话状态全部记录在 `SESSION_RECORD.md` 中。
