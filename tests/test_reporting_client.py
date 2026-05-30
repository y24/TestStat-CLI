import unittest

from utils.ReportingClient import build_progress_payload


class ReportingClientPayloadTests(unittest.TestCase):
    def test_build_progress_payload_expands_daily_and_person_rows(self):
        project_info = {"testing_id": 1001, "project_name": "Sample"}
        results = [
            (
                r"C:\work\sample1.xlsx",
                {
                    "label": "TEST001",
                    "target_environments": ["env-a"],
                    "stats": {
                        "all": 10,
                        "available": 8,
                        "excluded": 2,
                        "completed": 5,
                        "executed": 6,
                        "incompleted": 2,
                    },
                    "total": {
                        "Pass": 4,
                        "Fixed": 1,
                        "Fail": 1,
                        "Blocked": 0,
                        "Suspend": 0,
                        "N/A": 0,
                        "未実施": 2,
                        "完了数": 5,
                        "消化数": 6,
                    },
                    "run": {"start_date": "2026-05-01", "last_update": "2026-05-02"},
                    "daily": {
                        "2026-05-01": {
                            "Pass": 3,
                            "Fixed": 1,
                            "Fail": 1,
                            "完了数": 4,
                            "消化数": 5,
                            "計画数": 7,
                        }
                    },
                    "by_name": {"2026-05-01": {"Alice": 3, "Bob": 2, "": 1}},
                },
            )
        ]

        payload = build_progress_payload(project_info, results, sender="sender-a")

        self.assertEqual(payload["testing_id"], 1001)
        self.assertEqual(payload["project_name"], "Sample")
        self.assertEqual(payload["sender"], "sender-a")
        self.assertEqual(len(payload["files"]), 1)

        file_payload = payload["files"][0]
        self.assertEqual(file_payload["file_name"], "sample1.xlsx")
        self.assertEqual(file_payload["environment"], "env-a")
        self.assertEqual(file_payload["available_cases"], 8)
        self.assertEqual(file_payload["completed_rate"], 62.5)
        self.assertEqual(file_payload["executed_rate"], 75.0)
        self.assertEqual(file_payload["results"]["Pass"], 4)
        self.assertEqual(file_payload["daily"][0]["planned"], 7)
        self.assertEqual(
            file_payload["by_person"],
            [
                {"date": "2026-05-01", "person": "Alice", "count": 3},
                {"date": "2026-05-01", "person": "Bob", "count": 2},
            ],
        )

    def test_build_progress_payload_preserves_error_files_for_server_validation(self):
        project_info = {"testing_id": 1001, "project_name": "Sample"}
        results = [
            (
                "missing.xlsx",
                {
                    "label": "TEST999",
                    "error": {"type": "sheet_not_found", "message": "sheet missing"},
                },
            )
        ]

        payload = build_progress_payload(project_info, results)

        self.assertEqual(payload["files"][0]["file_name"], "missing.xlsx")
        self.assertEqual(payload["files"][0]["available_cases"], 0)
        self.assertEqual(payload["files"][0]["error"], "sheet missing")


if __name__ == "__main__":
    unittest.main()
