### Task 5: Sidebar Dynamic Counts

**Files:**
- Modify: `src/app/viewmodel/main_viewmodel.py`
- Modify: `src/app/ui/main_window.py`
- Create: `tests/viewmodel/test_main_viewmodel_counts.py`

**Constraints:**
- Execute in Conda `py311-pack` environment.
- No schema changes to V1.0 SQLite database.

**Interfaces:**
- Add `count_files(self, tag_id: Optional[int] = None) -> int` to `MainViewModel`.
- Update `MainWindow._update_tag_tree()` to append ` (count)` to the UI text of "所有文件" and each tag.

- [ ] **Step 1: Write the failing tests**
In `tests/viewmodel/test_main_viewmodel_counts.py`, test `count_files(None)` and `count_files(tag_id)` by mocking the DB. Since the database is SQLite, you can query `SELECT COUNT(*) FROM files` or `SELECT COUNT(*) FROM file_tags WHERE tag_id = ?`.

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement `count_files` in `MainViewModel` and `Database`**
Wait, if you modify `Database` class in `src/app/db/database.py`, that's fine as long as no schema changes are made.
Add `count_all_files(self) -> int` and `count_files_by_tag(self, tag_id: int) -> int` to `Database`.
Then expose `count_files(self, tag_id: Optional[int] = None) -> int` in `MainViewModel`.

- [ ] **Step 4: Update `MainWindow._update_tag_tree`**
In `src/app/ui/main_window.py`:
Change `root_item = QTreeWidgetItem(self.tag_tree, ["所有文件"])` to append the total count.
Change `item = QTreeWidgetItem([tag.tag_name])` to append the count for that tag.
Example text: `所有文件 (123)`

- [ ] **Step 5: Run tests and Commit**
Commit message: `feat: add dynamic counts to sidebar smart navigation`
