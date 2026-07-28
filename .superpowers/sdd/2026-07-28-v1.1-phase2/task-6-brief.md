### Task 6: Inspector Panel In-Place Editing (Tags)

**Files:**
- Modify: `src/app/ui/main_window.py`
- Modify: `src/app/ui/command_palette.py`
- Create: `tests/ui/test_inspector_tags.py`

**Constraints:**
- Execute in Conda `py311-pack` environment.

**Interfaces:**
- Refactor the right-side `file_preview` (currently a single `QTextEdit`) to split out the tags into an interactive chip layout.
- Add "×" (remove) button to each tag chip. Clicking it removes the tag via `self.vm.remove_file_tag(file_id, tag.id)` and refreshes.
- Add "+" (add tag) button at the end of the tags. Clicking it opens the `CommandPalette` in a specific context.
- Update `CommandPalette` to support a "context mode": `set_context_file(file_id: int, file_name: str)`. When set, it changes the search box placeholder to `为文件 {file_name} 添加标签...`.
- Add a new signal to `CommandPalette`: `tag_selected_for_file = pyqtSignal(int, int)` (file_id, tag_id).
- Wire up `CommandPalette` so that if it's in `file_id` mode and the user selects a tag (by pressing Enter or double clicking the list), it emits `tag_selected_for_file(file_id, tag_id)`, and then `MainWindow` receives this, calls `self.vm.add_file_tag(file_id, tag_id)`, and refreshes the preview.

- [ ] **Step 1: Write the failing tests**
In `tests/ui/test_inspector_tags.py`, mock the UI and DB to ensure:
1. `_load_file_preview` creates tag widgets with `x` buttons.
2. Clicking `x` calls `remove_file_tag`.
3. Clicking `+` calls `toggle_command_palette` (or equivalent) and passes the file context.
4. `CommandPalette` context mode changes the placeholder.

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Update `CommandPalette`**
Add `set_context_file` method. Add logic to emit `tag_selected_for_file` when an item is activated.

- [ ] **Step 4: Update `MainWindow` file preview**
Create a custom `QWidget` (e.g. `FlowLayout` or `QHBoxLayout` with wrapping, or even just a horizontal box for simple rendering) for tags.
Create a small `TagChipWidget` with a QLabel and a QPushButton("×").
Wire up the `+` button to call `self.command_palette.set_context_file(...)` and `self.toggle_command_palette()`.
Wire up `CommandPalette.tag_selected_for_file` to perform the DB insertion and UI refresh.

- [ ] **Step 5: Run tests and Commit**
Commit message: `feat: add in-place tag editing in inspector panel and link command palette`
