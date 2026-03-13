from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from PyQt5.QtCore import Qt, QPoint, QRect, QMimeData
from PyQt5.QtGui import QDrag, QImage, QPainter, QPalette, QBrush, QColor, QFontMetrics
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget,
    QTreeWidgetItem, QListWidget, QListWidgetItem, QLabel, QLineEdit, QPushButton,
    QSplitter, QMenu, QAction, QInputDialog, QMessageBox, QTabWidget,
    QTextEdit, QDateTimeEdit, QFormLayout, QDialog, QDialogButtonBox, QFileDialog, QComboBox
)

from src.app.model.file_record import FileRecord
from src.app.viewmodel.main_viewmodel import MainViewModel
from src.app.viewmodel.signals import MainSignals


class FileListWidget(QListWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setSelectionMode(QListWidget.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DragOnly)
        self.setAlternatingRowColors(True)
        self.setMinimumWidth(400)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
    
    def show_context_menu(self, pos: QPoint):
        menu = QMenu(self)
        add_tag_action = QAction("添加标签", self)
        add_note_action = QAction("添加注释", self)
        add_imprint_action = QAction("添加印记", self)
        delete_action = QAction("删除", self)
        
        # 连接信号
        delete_action.triggered.connect(lambda: self._on_delete())
        
        menu.addAction(add_tag_action)
        menu.addAction(add_note_action)
        menu.addAction(add_imprint_action)
        menu.addSeparator()
        menu.addAction(delete_action)
        menu.exec_(self.mapToGlobal(pos))
    
    def _on_delete(self):
        """软删除文件"""
        selected_items = self.selectedItems()
        if not selected_items:
            return
        
        # 确认删除
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除选中的 {len(selected_items)} 个文件吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 调用ViewModel的软删除方法
            for item in selected_items:
                file_id = item.data(Qt.UserRole)
                if file_id:
                    # 找到MainWindow对象
                    main_window = self.parentWidget().parentWidget().parentWidget()
                    if hasattr(main_window, 'vm'):
                        main_window.vm.soft_delete_file(file_id)
            
            # 显示成功提示
            QMessageBox.information(self, "删除成功", f"已删除 {len(selected_items)} 个文件")
            # 刷新文件列表
            main_window = self.parentWidget().parentWidget().parentWidget()
            if hasattr(main_window, '_update_file_list'):
                main_window._update_file_list()
    
    def startDrag(self, supportedActions):
        selected_items = self.selectedItems()
        if not selected_items:
            return
        
        mime_data = QMimeData()
        file_ids = []
        for item in selected_items:
            file_id = item.data(Qt.UserRole)
            if file_id:
                file_ids.append(str(file_id))
        
        mime_data.setText(",".join(file_ids))
        mime_data.setData("application/x-file-ids", ",".join(file_ids).encode())
        
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec_(Qt.CopyAction)


class TagTreeWidget(QTreeWidget):
    def __init__(self, parent: Optional[QWidget] = None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setHeaderLabel("标签")
        self.setAcceptDrops(True)
        self.setDragDropMode(QTreeWidget.DropOnly)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
    
    def show_context_menu(self, pos: QPoint):
        menu = QMenu(self)
        add_tag_action = QAction("添加标签", self)
        delete_tag_action = QAction("删除标签", self)
        menu.addAction(add_tag_action)
        menu.addAction(delete_tag_action)
        menu.exec_(self.mapToGlobal(pos))
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-file-ids"):
            event.accept()
        else:
            event.ignore()
    
    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-file-ids"):
            # 高亮显示当前拖拽位置的标签
            item = self.itemAt(event.pos())
            if item:
                self.setCurrentItem(item)
            event.accept()
        else:
            event.ignore()
    
    def dropEvent(self, event):
        if event.mimeData().hasFormat("application/x-file-ids"):
            file_ids = event.mimeData().data("application/x-file-ids").data().decode().split(",")
            item = self.itemAt(event.pos())
            if item:
                tag_id = item.data(0, Qt.UserRole)
                if tag_id and self.main_window:
                    # 处理文件拖拽到标签的逻辑
                    for file_id_str in file_ids:
                        try:
                            file_id = int(file_id_str)
                            self.main_window.vm.add_tag_to_file(file_id, tag_id)
                        except ValueError:
                            pass
                    # 显示成功提示
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.information(self, "标记成功", f"已为 {len(file_ids)} 个文件添加标签")
            event.accept()
        else:
            event.ignore()


class NoteDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None, note: str = ""):
        super().__init__(parent)
        self.setWindowTitle("编辑文档注释")
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)
        
        layout = QVBoxLayout(self)
        self.note_edit = QTextEdit(self)
        self.note_edit.setText(note)
        layout.addWidget(QLabel("注释内容:"))
        layout.addWidget(self.note_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def get_note(self) -> str:
        return self.note_edit.toPlainText()


class ImprintDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("添加文件印记")
        self.setMinimumWidth(400)
        
        layout = QFormLayout(self)
        self.imprint_edit = QTextEdit(self)
        self.imprint_edit.setPlaceholderText("输入印记内容...")
        layout.addRow(QLabel("印记内容:"), self.imprint_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def get_imprint(self) -> str:
        return self.imprint_edit.toPlainText()


class MainWindow(QMainWindow):
    def __init__(self, app_name: str, vm: MainViewModel, signals: MainSignals):
        super().__init__()
        self.setWindowTitle(app_name)
        self.setMinimumSize(1000, 600)
        
        self.vm = vm
        self.signals = signals
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 添加菜单栏
        self._create_menu_bar()
        
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # 搜索和筛选栏
        self.search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索文件...")
        self.search_button = QPushButton("搜索")
        
        # 类型筛选
        self.filter_type_combo = QComboBox()
        self.filter_type_combo.addItem("所有类型")
        self.filter_type_combo.currentIndexChanged.connect(self._on_filter_change)
        
        # 位置筛选
        self.filter_location_combo = QComboBox()
        self.filter_location_combo.addItem("所有位置")
        self.filter_location_combo.currentIndexChanged.connect(self._on_filter_change)
        
        # 排序按钮
        self.sort_button = QPushButton("排序")
        
        # 重置按钮
        self.reset_button = QPushButton("重置筛选")
        self.reset_button.clicked.connect(self._on_reset_filter)
        
        self.search_layout.addWidget(self.search_input)
        self.search_layout.addWidget(self.search_button)
        self.search_layout.addWidget(QLabel("类型:"))
        self.search_layout.addWidget(self.filter_type_combo)
        self.search_layout.addWidget(QLabel("位置:"))
        self.search_layout.addWidget(self.filter_location_combo)
        self.search_layout.addWidget(self.sort_button)
        self.search_layout.addWidget(self.reset_button)
        
        self.main_layout.addLayout(self.search_layout)
        
        # 主内容区域
        self.splitter = QSplitter(Qt.Horizontal)
        
        # 标签树
        self.tag_tree = TagTreeWidget(main_window=self)
        self.tag_tree.setMinimumWidth(200)
        self.splitter.addWidget(self.tag_tree)
        
        # 文件列表
        self.file_list = FileListWidget()
        self.splitter.addWidget(self.file_list)
        
        # 预览窗口
        self.preview_tab = QTabWidget()
        self.preview_tab.setMinimumWidth(300)
        
        # 文件预览
        file_preview_layout = QVBoxLayout()
        self.file_preview = QTextEdit()
        self.file_preview.setReadOnly(True)
        file_preview_layout.addWidget(self.file_preview)
        file_preview_widget = QWidget()
        file_preview_widget.setLayout(file_preview_layout)
        
        # 文档注释
        note_layout = QVBoxLayout()
        self.note_tab = QTextEdit()
        self.save_note_button = QPushButton("保存注释")
        self.save_note_button.clicked.connect(self._on_save_note)
        note_layout.addWidget(self.note_tab)
        note_layout.addWidget(self.save_note_button)
        note_widget = QWidget()
        note_widget.setLayout(note_layout)
        
        # 文件印记
        imprint_layout = QVBoxLayout()
        self.imprint_tab = QTextEdit()
        self.imprint_tab.setReadOnly(True)
        self.add_imprint_button = QPushButton("添加印记")
        self.add_imprint_button.clicked.connect(self._on_add_imprint)
        imprint_layout.addWidget(self.imprint_tab)
        imprint_layout.addWidget(self.add_imprint_button)
        imprint_widget = QWidget()
        imprint_widget.setLayout(imprint_layout)
        
        self.preview_tab.addTab(file_preview_widget, "文件预览")
        self.preview_tab.addTab(note_widget, "文档注释")
        self.preview_tab.addTab(imprint_widget, "文件印记")
        
        self.splitter.addWidget(self.preview_tab)
        
        # 设置分割比例
        self.splitter.setSizes([250, 500, 450])
        
        self.main_layout.addWidget(self.splitter)
        
        # 底部状态栏
        self.status_bar = self.statusBar()
        
        # 连接信号
        self._connect_signals()
        
        # 初始化数据
        self._initialize_data()
    
    def _connect_signals(self):
        # 搜索和筛选
        self.search_button.clicked.connect(self._on_search)
        self.sort_button.clicked.connect(self._on_sort)
        
        # 文件列表
        self.file_list.itemSelectionChanged.connect(self._on_file_selected)
        
        # 标签树
        self.tag_tree.itemClicked.connect(self._on_tag_clicked)
        
        # 信号连接
        self.signals.files_updated.connect(self._update_file_list)
        self.signals.tags_updated.connect(self._update_tag_tree)
    
    def _initialize_data(self):
        # 加载标签
        self._update_tag_tree()
        # 加载文件
        self._update_file_list()
        # 加载筛选选项
        self._load_filter_options()
    
    def _load_filter_options(self):
        """加载筛选选项"""
        # 加载文件类型
        self.filter_type_combo.clear()
        self.filter_type_combo.addItem("所有类型")
        file_extensions = self.vm.get_all_file_extensions()
        for ext in file_extensions:
            self.filter_type_combo.addItem(ext)
        
        # 加载磁盘位置
        self.filter_location_combo.clear()
        self.filter_location_combo.addItem("所有位置")
        drive_letters = self.vm.get_all_drive_letters()
        for drive in drive_letters:
            self.filter_location_combo.addItem(drive)
    
    def _on_filter_change(self):
        """筛选条件变化处理"""
        file_ext = None
        drive_letter = None
        
        # 获取类型筛选
        if self.filter_type_combo.currentIndex() > 0:
            file_ext = self.filter_type_combo.currentText()
        
        # 获取位置筛选
        if self.filter_location_combo.currentIndex() > 0:
            drive_letter = self.filter_location_combo.currentText()
        
        # 应用筛选
        files = self.vm.list_files(file_ext=file_ext, drive_letter=drive_letter)
        self._update_file_list(files)
    
    def _on_reset_filter(self):
        """重置筛选条件"""
        self.search_input.setText("")
        self.filter_type_combo.setCurrentIndex(0)
        self.filter_location_combo.setCurrentIndex(0)
        self._update_file_list()
    
    def _update_file_list(self, files: Optional[List[FileRecord]] = None):
        if files is None:
            files = self.vm.get_all_files()
        
        self.file_list.clear()
        for file in files:
            item = QListWidgetItem(file.file_name)
            item.setData(Qt.UserRole, file.id)
            # 添加工具提示
            tooltip = f"路径: {file.full_path}\n大小: {file.file_size} bytes\n修改时间: {file.modify_time}"
            item.setToolTip(tooltip)
            self.file_list.addItem(item)
    
    def _update_tag_tree(self):
        self.tag_tree.clear()
        tags = self.vm.get_all_tags()
        
        # 构建标签树
        tag_map = {}
        root_item = QTreeWidgetItem(self.tag_tree, ["所有文件"])
        root_item.setData(0, Qt.UserRole, None)
        
        for tag in tags:
            item = QTreeWidgetItem([tag.tag_name])
            item.setData(0, Qt.UserRole, tag.id)
            
            if tag.parent_id:
                if tag.parent_id in tag_map:
                    tag_map[tag.parent_id].addChild(item)
            else:
                root_item.addChild(item)
            
            tag_map[tag.id] = item
        
        self.tag_tree.expandAll()
    
    def _on_search(self):
        query = self.search_input.text()
        files = self.vm.search_files(query)
        self._update_file_list(files)
    
    def _on_sort(self):
        # 切换排序顺序
        files = self.vm.get_all_files(sort_by="name", sort_order="asc")
        self._update_file_list(files)
    
    def _on_file_selected(self):
        selected_items = self.file_list.selectedItems()
        if not selected_items:
            return
        
        file_id = selected_items[0].data(Qt.UserRole)
        if not file_id:
            return
        
        # 加载文件预览
        file = self.vm.get_file_by_id(file_id)
        if file:
            self._load_file_preview(file)
            
            # 加载文档注释
            note = self.vm.get_file_note(file_id)
            self.note_tab.setText(note or "无注释")
            
            # 加载文件印记
            imprints = self.vm.get_file_imprints(file_id)
            imprint_text = "\n\n".join([f"{imprint.created_at}: {imprint.content}" for imprint in imprints])
            self.imprint_tab.setText(imprint_text or "无印记")
    
    def _on_tag_clicked(self, item: QTreeWidgetItem, column: int):
        tag_id = item.data(0, Qt.UserRole)
        if tag_id is None:
            # 显示所有文件
            files = self.vm.get_all_files()
        else:
            # 显示标签下的文件
            files = self.vm.get_files_by_tag(tag_id)
        self._update_file_list(files)
    
    def _create_menu_bar(self):
        """创建菜单栏"""
        menu_bar = self.menuBar()
        
        # 文件菜单
        file_menu = menu_bar.addMenu("文件")
        
        # 导入文件动作
        import_action = QAction("导入文件...", self)
        import_action.setShortcut("Ctrl+I")
        import_action.triggered.connect(self._on_import_files)
        file_menu.addAction(import_action)
        
        # 退出动作
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 标签菜单
        tag_menu = menu_bar.addMenu("标签")
        
        # 添加标签动作
        add_tag_action = QAction("添加标签...", self)
        add_tag_action.triggered.connect(self._on_add_tag)
        tag_menu.addAction(add_tag_action)
    
    def _on_import_files(self):
        """导入文件"""
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择要导入的文件", "", "所有文件 (*);;文本文件 (*.txt);;图片文件 (*.jpg *.jpeg *.png *.gif)", options=options
        )
        
        if files:
            from pathlib import Path
            from src.app.viewmodel.main_viewmodel import ImportCandidate
            
            # 创建导入候选对象
            candidates = []
            for file_path in files:
                path = Path(file_path)
                try:
                    st = path.stat()
                    candidates.append(ImportCandidate(path=path, size=int(st.st_size)))
                except OSError:
                    continue
            
            # 导入文件
            if candidates:
                inserted = self.vm.import_files(candidates)
                QMessageBox.information(self, "导入完成", f"成功导入 {inserted} 个文件")
    
    def _on_add_tag(self):
        """添加标签"""
        tag_name, ok = QInputDialog.getText(self, "添加标签", "请输入标签名称:")
        if ok and tag_name:
            self.vm.create_tag(tag_name)
    
    def _on_save_note(self):
        """保存文档注释"""
        selected_items = self.file_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择一个文件")
            return
        
        file_id = selected_items[0].data(Qt.UserRole)
        note = self.note_tab.toPlainText()
        self.vm.set_file_note(file_id, note)
        QMessageBox.information(self, "保存成功", "文档注释已保存")
    
    def _on_add_imprint(self):
        """添加文件印记"""
        selected_items = self.file_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择一个文件")
            return
        
        file_id = selected_items[0].data(Qt.UserRole)
        dialog = ImprintDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            imprint = dialog.get_imprint()
            if imprint:
                self.vm.add_file_imprint(file_id, imprint)
                # 重新加载印记
                imprints = self.vm.get_file_imprints(file_id)
                imprint_text = "\n\n".join([f"{imprint.created_at}: {imprint.content}" for imprint in imprints])
                self.imprint_tab.setText(imprint_text or "无印记")
                QMessageBox.information(self, "添加成功", "文件印记已添加")
    
    def _load_file_preview(self, file: FileRecord):
        try:
            # 构建文件信息预览
            preview_content = []
            
            # 文件基本信息
            preview_content.append(f"文件名称: {file.file_name}")
            preview_content.append(f"文件位置: {file.full_path}")
            preview_content.append(f"文件大小: {file.file_size} bytes")
            preview_content.append(f"修改时间: {file.modify_time}")
            
            # 文件标签
            tags = self.vm.get_file_tags(file.id)
            if tags:
                preview_content.append("\n标签:")
                for tag in tags:
                    # 构建标签的父子关系显示
                    tag_path = []
                    current_tag = tag
                    while current_tag:
                        tag_path.insert(0, current_tag.tag_name)
                        if current_tag.parent_id:
                            # 查找父标签
                            for t in tags:
                                if t.id == current_tag.parent_id:
                                    current_tag = t
                                    break
                            else:
                                current_tag = None
                        else:
                            current_tag = None
                    preview_content.append(f"  - {' / '.join(tag_path)}")
            else:
                preview_content.append("\n标签: 无")
            
            # 文件注释
            note = self.vm.get_file_note(file.id)
            preview_content.append("\n注释:")
            preview_content.append(note or "无")
            
            # 文件简介（这里使用注释作为简介，因为它们在功能上是相同的）
            preview_content.append("\n简介:")
            preview_content.append(note or "无")
            
            # 对于文本文件，添加文件内容预览
            if file.file_name.lower().endswith((".txt", ".md", ".py", ".java", ".cpp", ".h", ".json", ".xml")):
                try:
                    with open(file.full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    preview_content.append("\n文件内容预览:")
                    # 限制预览内容长度
                    if len(content) > 1000:
                        content = content[:1000] + "...\n\n[内容已截断]"
                    preview_content.append(content)
                except Exception as e:
                    preview_content.append(f"\n文件内容预览: 无法读取 ({str(e)})")
            # 对于图片文件，显示图片
            elif file.file_name.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp")):
                image = QImage(file.full_path)
                if not image.isNull():
                    # 调整图片大小以适应预览窗口
                    scaled_image = image.scaled(self.file_preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.file_preview.setPixmap(scaled_image)
                    # 在图片下方显示文件信息
                    self.file_preview.append("\n" + "\n".join(preview_content))
                    return
                else:
                    preview_content.append("\n图片预览: 无法加载")
            
            # 设置预览内容
            self.file_preview.setText("\n".join(preview_content))
        except Exception as e:
            self.file_preview.setText(f"预览失败: {str(e)}")


def run_ui(app_name: str, vm: MainViewModel, signals: MainSignals) -> int:
    app = QApplication(sys.argv)
    window = MainWindow(app_name, vm, signals)
    window.show()
    return app.exec_()