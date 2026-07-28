# Task 5 Report: Sidebar Dynamic Counts

## What Was Implemented

1. **Database Layer (`src/app/db/database.py`)**:
   - Added `count_all_files(self) -> int` to query total non-deleted (`is_deleted = 0`) files.
   - Added `count_files_by_tag(self, tag_id: int) -> int` to query total non-deleted files associated with a specific tag ID in `file_tag_relation`.

2. **ViewModel Layer (`src/app/viewmodel/main_viewmodel.py`)**:
   - Added `count_files(self, tag_id: Optional[int] = None) -> int` to delegate count queries to `Database`. Returns 0 if DB is `None`.

3. **UI Layer (`src/app/ui/main_window.py`)**:
   - Updated `MainWindow._update_tag_tree()` to append ` (count)` to "所有文件" (e.g. `所有文件 (123)`) and to each tag node (e.g. `工作 (5)`).

## TDD Evidence

### RED Phase
- **Command:** `conda run -n py311-pack pytest tests/viewmodel/test_main_viewmodel_counts.py`
- **Failing Output:**
  ```text
  FAILED tests/viewmodel/test_main_viewmodel_counts.py::test_count_files_without_db - AttributeError: 'MainViewModel' object has no attribute 'count_files'
  FAILED tests/viewmodel/test_main_viewmodel_counts.py::test_count_files_with_db - AttributeError: 'MainViewModel' object has no attribute 'count_files'
  ```
- **Why Failure Was Expected:** `count_files` had not been implemented on `MainViewModel` yet.

### GREEN Phase
- **Command:** `conda run -n py311-pack pytest tests/viewmodel/test_main_viewmodel_counts.py`
- **Passing Output:**
  ```text
  tests\viewmodel\test_main_viewmodel_counts.py .. [100%]
  2 passed in 0.04s
  ```

## Full Test Suite Results

- **Command:** `conda run -n py311-pack pytest`
- **Output:**
  ```text
  collected 13 items

  tests\test_env.py ..                                                     [ 15%]
  tests\ui\test_command_palette.py .                                       [ 23%]
  tests\ui\test_main_window_ctrl_k.py .                                    [ 30%]
  tests\ui\test_sidebar_counts.py .                                        [ 38%]
  tests\viewmodel\test_main_viewmodel_counts.py ..                         [ 53%]
  tests\viewmodel\test_main_viewmodel_search.py ......                     [100%]

  ============================= 13 passed in 0.52s ==============================
  ```

## Files Changed

- `src/app/db/database.py` (Modified)
- `src/app/viewmodel/main_viewmodel.py` (Modified)
- `src/app/ui/main_window.py` (Modified)
- `tests/viewmodel/test_main_viewmodel_counts.py` (Created)
- `tests/ui/test_sidebar_counts.py` (Created)

## Self-Review Findings

- **Completeness:** All interfaces specified in Task 5 brief implemented. Soft-deleted files filtering handled accurately across all queries.
- **Quality:** Clean and minimal implementation, proper type annotations and docstrings provided.
- **Discipline:** Strictly followed TDD rules. No schema modifications to SQLite database.
- **Testing:** Unit tests cover both viewmodel (with and without DB) and UI tag tree count display rendering. Test output pristine.

## Issues / Concerns

None.
