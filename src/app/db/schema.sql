PRAGMA foreign_keys = ON;

-- files: 以 file_hash 作为稳定识别（路径变更也可匹配）
CREATE TABLE IF NOT EXISTS files (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  file_name TEXT NOT NULL,
  file_ext TEXT,
  full_path TEXT NOT NULL,
  file_size INTEGER,
  create_time INTEGER,
  modify_time INTEGER,
  file_hash TEXT NOT NULL,
  is_deleted INTEGER NOT NULL DEFAULT 0,
  deleted_at INTEGER,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_files_file_hash ON files(file_hash);
CREATE INDEX IF NOT EXISTS idx_files_file_name ON files(file_name);
CREATE INDEX IF NOT EXISTS idx_files_full_path ON files(full_path);
CREATE INDEX IF NOT EXISTS idx_files_create_time ON files(create_time);

-- tags: 支持最多 3 级层级（通过 parent_id 形成树）
CREATE TABLE IF NOT EXISTS tags (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tag_name TEXT NOT NULL,
  tag_type TEXT,
  parent_id INTEGER,
  is_deleted INTEGER NOT NULL DEFAULT 0,
  deleted_at INTEGER,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  FOREIGN KEY(parent_id) REFERENCES tags(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_tags_tag_name ON tags(tag_name);
CREATE INDEX IF NOT EXISTS idx_tags_tag_type ON tags(tag_type);
CREATE INDEX IF NOT EXISTS idx_tags_parent_id ON tags(parent_id);

-- 关联表：文件与标记多对多
CREATE TABLE IF NOT EXISTS file_tag_relation (
  file_id INTEGER NOT NULL,
  tag_id INTEGER NOT NULL,
  created_at INTEGER NOT NULL,
  PRIMARY KEY(file_id, tag_id),
  FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE,
  FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_file_tag_relation_file_id ON file_tag_relation(file_id);
CREATE INDEX IF NOT EXISTS idx_file_tag_relation_tag_id ON file_tag_relation(tag_id);

-- 搜索历史：最近 N 条
CREATE TABLE IF NOT EXISTS search_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  query_json TEXT NOT NULL,
  created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_search_history_created_at ON search_history(created_at DESC);

-- 文件文档简介
CREATE TABLE IF NOT EXISTS file_notes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  file_id INTEGER NOT NULL,
  content TEXT,
  updated_at INTEGER NOT NULL,
  FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_file_notes_file_id ON file_notes(file_id);

-- 文件特定印记
CREATE TABLE IF NOT EXISTS file_imprints (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  file_id INTEGER NOT NULL,
  content TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_file_imprints_file_id ON file_imprints(file_id);
CREATE INDEX IF NOT EXISTS idx_file_imprints_created_at ON file_imprints(created_at DESC);
