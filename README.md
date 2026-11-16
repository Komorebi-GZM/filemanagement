# 本地文件多标记交叉管理系统（V1.3）

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![PyQt5](https://img.shields.io/badge/PyQt5-5.15.0+-green.svg)
![SQLite](https://img.shields.io/badge/SQLite-3.37.0+%20(FTS5)-orange.svg)

### 项目简介

**本地文件多标记交叉管理系统**是一款本地文件管理工具，基于 PyQt5 + SQLite 开发，采用 MVVM + Services 分层架构设计。系统提供异步文件导入、多标记层级分类、SQLite FTS5 全文搜索、实时文件监控同步、全局命令面板（`Ctrl+K`）、文件预览以及元数据管理（文档简介、特定印记）等功能。

### 核心特性

- **异步文件管理**：支持批量导入文件，后台线程（`ImportWorker`）异步计算 SHA256 哈希去重并汇报导入进度，避免主线程卡顿
- **多标记系统与就地编辑**：支持层级标签树、文件拖拽打标，并在右侧详情面板通过彩色标签胶囊（`TagChipWidget`）就地增删标签（`+` / `×`）
- **全局命令面板（`Ctrl+K`）**：支持在选中文件时快速打标，未选中文件时执行搜索并支持 `↑`/`↓` 键浏览最近搜索历史
- **全文搜索与多维筛选**：基于 SQLite FTS5 与 `IndexWorker` 后台增量索引，支持 `.txt`、`.md`、`.log`、`.csv`、`.pdf`、`.docx`、`.xlsx` 文件内容检索，并可结合文件名、扩展名与磁盘位置筛选
- **实时文件监控同步**：通过 `FileMonitor`（封装 `watchdog` + `QTimer` 防抖）监听已导入文件所在目录，自动同步外部移动、重命名、修改与删除事件并更新 FTS 索引
- **现代化 UI 与预览**：集中式 QSS 主题（`theme.py`）、OS 原生文件图标，支持图片/文本文件预览、文档简介备注与时间倒序特定印记
- **本地存储**：所有数据与索引存储在本地 SQLite 数据库中，保障数据安全

---

### 技术架构

#### 项目结构

```text
filemanagement/
├── config/
│   ├── commands.txt            # AI 开发指令参考文档
│   └── config.ini              # 应用配置文件
├── data/
│   └── users/
│       └── default/
│           └── app.sqlite3     # SQLite 数据库文件（运行后生成）
├── docs/                       # 需求文档、设计报告与版本 PRD/Plan
├── logs/
│   └── app.log                 # 运行日志（运行后生成）
├── src/
│   ├── __init__.py
│   ├── main.py                 # 应用入口文件（初始化 DB/IndexWorker/FileMonitor）
│   └── app/
│       ├── __init__.py
│       ├── core/               # 核心配置模块（日志、路径、配置加载）
│       ├── db/                 # 数据库连接、FTS5 方法与 schema.sql
│       ├── model/              # 数据模型层（FileRecord、Tag）
│       ├── services/           # 独立服务层（文件监控、异步导入、全文提取与后台索引）
│       │   ├── file_monitor.py
│       │   ├── import_worker.py
│       │   ├── index_worker.py
│       │   └── text_extractor.py
│       ├── viewmodel/          # 视图模型层（MainViewModel、MainSignals）
│       └── ui/                 # 视图层（MainWindow、CommandPalette、QSS theme）
├── tests/                      # pytest + pytest-qt 单元测试与集成测试
├── dist_new/                   # PyInstaller 打包输出目录
├── requirements.txt            # Python 依赖
├── filemanagement.spec         # PyInstaller 打包配置
├── pytest.ini                  # pytest 配置
├── start.bat                   # 启动脚本（py311-pack）
└── package.bat                 # 打包脚本（py311-pack）
```

项目采用 **MVVM + Services** 分层架构：
- **Model**（`src/app/model/`）：定义 `FileRecord` 和 `Tag` 数据类
- **Services**（`src/app/services/`）：`FileMonitor`（watchdog + 防抖信号）、`ImportWorker`（异步导入与哈希）、`TextExtractor`（多格式文本抽取）与 `IndexWorker`（后台批量 FTS 索引）
- **ViewModel**（`src/app/viewmodel/`）：`MainViewModel` 封装业务逻辑、数据库同步与搜索，`MainSignals` 定义 PyQt5 信号
- **View**（`src/app/ui/`）：`MainWindow`、`CommandPalette` 与 `theme.py` 负责界面展示、主题样式与用户交互

#### 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| GUI 框架 | PyQt5 >= 5.15.0 | 桌面图形界面与异步线程/信号 |
| 运行环境 | Python 3.11+ | 推荐使用 `py311-pack` Conda 环境 |
| 数据库 | SQLite 3.37.0+ (FTS5) | 本地关系存储与全文检索 |
| 文件监控 | watchdog >= 4.0.1 | 文件系统实时变更监听 |
| 文本提取 | pymupdf / python-docx / openpyxl / chardet | PDF/DOCX/XLSX 与编码探测 |
| 图像处理 | Pillow >= 9.0.0 | 图片预览支持 |
| 自动化测试 | pytest / pytest-qt | ViewModel、Services 与 UI 测试 |

---

### 数据库结构

| 表名 | 用途 | 备注 |
|------|------|------|
| `files` | 存储文件记录 | 包含文件名、路径、大小、SHA256 哈希等，支持软删除 |
| `tags` | 存储标记信息 | 支持层级结构（`parent_id`），支持软删除 |
| `file_tag_relation` | 文件与标记关联 | 多对多关系，联合主键 |
| `search_history` | 搜索历史记录 | 记录最近搜索查询（自动清理保留上限 50 条） |
| `file_notes` | 文件简介备注 | 每个文件一条备注（UNIQUE 约束） |
| `file_imprints` | 文件特定印记 | 每个文件可有多条印记，按时间倒序 |
| `file_fts` | 全文检索虚表 | SQLite FTS5 (`unicode61`) 存储文件名与正文内容 |
| `file_content_status` | 全文索引状态 | 记录 `pending` / `indexed` / `skipped_*` / `error` 状态 |

---

### 安装与运行

#### 环境要求

- **操作系统**：Windows 10/11（开发环境亦支持 Linux/macOS 测试）
- **Python**：3.11+（`py311-pack` Conda 环境）
- **内存**：至少 2GB
- **磁盘空间**：至少 100MB 可用空间

#### 方法 1：直接运行可执行文件（Windows）

1. 进入 `dist_new` 目录
2. 运行 `文件管理系统.exe`

#### 方法 2：使用启动脚本

需要已配置 `py311-pack` conda 环境：

```bash
start.bat
```

#### 方法 3：使用 Python 直接运行与测试

```bash
pip install -r requirements.txt
conda run -n py311-pack python -m src.main

# 运行测试套件
conda run -n py311-pack python -m pytest
```

---

### 使用说明

#### 1. 添加文件
- 点击菜单「文件」->「导入文件...」或按快捷键 `Ctrl+I`
- 选择本地文件后后台异步计算 SHA256 并导入，状态栏实时显示导入与 FTS 索引进度

#### 2. 管理标记与就地打标
- 菜单「标签」->「添加标签...」或在标签树右键创建新标记
- **拖拽打标**：在文件列表中选择一个或多个文件拖拽到左侧标记树节点
- **就地编辑**：在右侧预览面板点击标签旁的 `+` 打开命令面板选择标签，或点击标签胶囊上的 `×` 直接移除
- **全局命令面板**：按 `Ctrl+K` 唤醒命令面板进行快捷搜索（支持 `↑`/`↓` 切换搜索历史）或打标

#### 3. 搜索与多维筛选
- **全文与文件名搜索**：在搜索框输入关键词后点击「搜索」，优先通过 FTS5 匹配文件内容与文件名，并合并文件名/扩展名模糊匹配结果
- **条件筛选**：点击左侧标签树节点（含实时计数），或使用顶部「类型」「位置」下拉框组合筛选

#### 4. 文件预览与元数据
- 选中文件后，右侧三个标签页分别展示：
  - **文件预览**：文件基本信息、标签胶囊管理与文本/图片内容预览
  - **文档注释**：编辑并保存文件自定义备注
  - **文件印记**：添加和查看文件特定印记记录

---

### 打包发布

使用 PyInstaller 打包为独立可执行文件（需 `py311-pack` 环境）：

```bash
package.bat
```

打包配置见 `filemanagement.spec`，产物输出到 `dist_new/` 目录。

---

### 许可证

本项目采用 MIT 许可证。
