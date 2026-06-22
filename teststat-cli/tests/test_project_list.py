import os
import tempfile
import unittest

from utils import ProjectList


def _write_yaml(content):
    fd, path = tempfile.mkstemp(suffix=".yaml")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


# project: ラッパーありの旧形式
LEGACY_YAML = """\
project:
  project_name: サンプルプロジェクト
  testing_id: 1001
  subtask_id: 999
  files:
  - label: テストA
    path: input/sample1.xlsx
    subtask_id: 111
    target_sheets:
      - テスト項目
  - label: テストB
    path: input/sample2.xlsx
"""

# project: ラッパーなしの新形式（同等の内容）
NEW_YAML = """\
project_name: サンプルプロジェクト
testing_id: 1001
subtask_id: 999
files:
- label: テストA
  path: input/sample1.xlsx
  subtask_id: 111
  target_sheets:
    - テスト項目
- label: テストB
  path: input/sample2.xlsx
"""


class ReadYamlProjectListTest(unittest.TestCase):
    def setUp(self):
        self._paths = []

    def tearDown(self):
        for p in self._paths:
            try:
                os.remove(p)
            except OSError:
                pass

    def _read(self, content):
        path = _write_yaml(content)
        self._paths.append(path)
        return ProjectList.read_yaml_project_list(path)

    def test_legacy_format(self):
        """project: ラッパーありの旧形式が従来どおり読み込める（後方互換）"""
        result = self._read(LEGACY_YAML)
        self.assertEqual(result["project_name"], "サンプルプロジェクト")
        self.assertEqual(result["testing_id"], 1001)
        self.assertEqual(result["subtask_id"], 999)
        self.assertEqual(len(result["files"]), 2)

    def test_new_format(self):
        """project: ラッパーなしの新形式が読み込める"""
        result = self._read(NEW_YAML)
        self.assertEqual(result["project_name"], "サンプルプロジェクト")
        self.assertEqual(result["testing_id"], 1001)
        self.assertEqual(result["subtask_id"], 999)
        self.assertEqual(len(result["files"]), 2)

    def test_legacy_and_new_are_equivalent(self):
        """新旧形式で同一の戻り値になる"""
        self.assertEqual(self._read(LEGACY_YAML), self._read(NEW_YAML))

    def test_file_options_parsed_in_new_format(self):
        """新形式でも files 内オプションが解釈される"""
        result = self._read(NEW_YAML)
        self.assertEqual(result["files"][0]["subtask_id"], 111)
        self.assertEqual(result["files"][0]["target_sheets"], ["テスト項目"])
        self.assertFalse(result["files"][0]["is_remote"])

    def test_missing_files_raises(self):
        """新形式で files キーが無い場合はエラー"""
        with self.assertRaises(ValueError):
            self._read("project_name: foo\ntesting_id: 1\n")

    def test_missing_project_name_raises(self):
        """新形式で project_name が無い場合はエラー"""
        with self.assertRaises(ValueError):
            self._read("testing_id: 1\nfiles:\n- label: a\n  path: b.xlsx\n")

    def test_empty_file_raises(self):
        """空ファイル（トップレベルが dict でない）はエラー"""
        with self.assertRaises(ValueError):
            self._read("")

    def test_project_value_not_mapping_raises(self):
        """project: の値がマッピングでない場合はエラー"""
        with self.assertRaises(ValueError):
            self._read("project: just-a-string\n")

    def test_remote_path_in_new_format(self):
        """新形式でもリモートパスは is_remote=True として扱われる"""
        content = (
            "project_name: remote\n"
            "files:\n"
            "- label: SharePoint\n"
            '  path: "https://contoso.sharepoint.com/:x:/s/site/Eabcd123"\n'
        )
        result = self._read(content)
        self.assertTrue(result["files"][0]["is_remote"])


if __name__ == "__main__":
    unittest.main()
