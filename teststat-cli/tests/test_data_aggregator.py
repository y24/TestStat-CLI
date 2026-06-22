import unittest

from utils import DataAggregator


# default_config.json と同じ定義
RESULTS = ["Pass", "Fixed", "Fail", "Blocked", "Suspend", "N/A"]
COMPLETED_RESULTS = ["Pass", "Fixed", "Suspend", "N/A"]
EXECUTED_RESULTS = ["Pass", "Fixed", "Fail", "Blocked", "Suspend", "N/A"]
COMPLETED_LABEL = "完了数"
EXECUTED_LABEL = "消化数"
PLAN_LABEL = "計画数"


def _aggregate(data, invalid_results=None):
    return DataAggregator.aggregate_daily_results(
        data, RESULTS, COMPLETED_LABEL, COMPLETED_RESULTS,
        EXECUTED_LABEL, EXECUTED_RESULTS, PLAN_LABEL,
        plan_data=None, invalid_results=invalid_results,
    )


class AggregateDailyResultsInvalidTests(unittest.TestCase):
    def test_excluded_result_with_date_is_not_in_daily(self):
        """対象外＋日付ありの行は daily に日付を作らない"""
        data = [
            ["Pass", "alice", "2026-05-01", "Sheet1"],
            ["対象外", "bob", "2026-06-01", "Sheet1"],
        ]
        daily, _ = _aggregate(data, invalid_results=["対象外", "準備"])

        self.assertIn("2026-05-01", daily)
        self.assertNotIn("2026-06-01", daily)

    def test_na_with_date_kept_in_count_but_not_in_daily(self):
        """N/A を無効指定すると、daily に日付は出ないが no_date でカウントは保持される"""
        data = [
            ["Pass", "alice", "2026-05-01", "Sheet1"],
            ["N/A", "bob", "2026-06-01", "Sheet1"],
        ]
        daily, no_date = _aggregate(data, invalid_results=["対象外", "準備", "N/A"])

        # 日付範囲には現れない
        self.assertNotIn("2026-06-01", daily)
        # no_date 側に N/A と完了/消化カウントが残る
        self.assertEqual(no_date["no_date"]["N/A"], 1)
        self.assertEqual(no_date["no_date"][COMPLETED_LABEL], 1)
        self.assertEqual(no_date["no_date"][EXECUTED_LABEL], 1)

    def test_na_total_count_preserved_via_calculate_total(self):
        """N/A を無効指定しても calculate_total_results で完了数が保持される"""
        data = [
            ["Pass", "alice", "2026-05-01", "Sheet1"],
            ["N/A", "bob", "2026-06-01", "Sheet1"],
        ]
        daily, no_date = _aggregate(data, invalid_results=["対象外", "準備", "N/A"])
        total = DataAggregator.calculate_total_results(
            daily, no_date, [COMPLETED_LABEL, EXECUTED_LABEL, PLAN_LABEL]
        )

        # Pass と N/A の両方がカウントされる
        self.assertEqual(total.get("Pass", 0), 1)
        self.assertEqual(total.get("N/A", 0), 1)
        completed = DataAggregator.sum_completed_results(total, COMPLETED_RESULTS)
        self.assertEqual(completed, 2)  # Pass + N/A

    def test_valid_result_keeps_date(self):
        """有効結果は従来どおり日付を保持する"""
        data = [["Pass", "alice", "2026-05-01", "Sheet1"]]
        daily, _ = _aggregate(data, invalid_results=["対象外", "準備", "N/A"])

        self.assertIn("2026-05-01", daily)
        self.assertEqual(daily["2026-05-01"]["Pass"], 1)

    def test_mixed_valid_and_invalid_same_date(self):
        """同一日に有効＋無効が混在する場合、その日は残り件数は有効分のみ"""
        data = [
            ["Pass", "alice", "2026-05-01", "Sheet1"],
            ["対象外", "bob", "2026-05-01", "Sheet1"],
        ]
        daily, _ = _aggregate(data, invalid_results=["対象外", "準備"])

        self.assertIn("2026-05-01", daily)
        self.assertEqual(daily["2026-05-01"]["Pass"], 1)
        self.assertEqual(daily["2026-05-01"][COMPLETED_LABEL], 1)

    def test_backward_compatible_without_invalid_results(self):
        """invalid_results 未指定時は従来挙動（日付がそのまま残る）"""
        data = [
            ["Pass", "alice", "2026-05-01", "Sheet1"],
            ["対象外", "bob", "2026-06-01", "Sheet1"],
        ]
        daily, _ = _aggregate(data)

        # 後方互換: 対象外の日付キーも生成される（全0内訳）
        self.assertIn("2026-05-01", daily)
        self.assertIn("2026-06-01", daily)

    def test_date_range_not_widened_by_invalid_result(self):
        """無効結果の未来日で範囲(min/max)が広がらない"""
        data = [
            ["Pass", "alice", "2026-05-01", "Sheet1"],
            ["Fixed", "alice", "2026-05-10", "Sheet1"],
            ["対象外", "bob", "2026-12-31", "Sheet1"],
        ]
        daily, _ = _aggregate(data, invalid_results=["対象外", "準備", "N/A"])

        self.assertEqual(min(daily.keys()), "2026-05-01")
        self.assertEqual(max(daily.keys()), "2026-05-10")


class AggregateDailyByPersonInvalidTests(unittest.TestCase):
    def test_excluded_result_not_in_person_breakdown(self):
        data = [
            ["Pass", "alice", "2026-05-01", "Sheet1"],
            ["対象外", "bob", "2026-06-01", "Sheet1"],
        ]
        by_name = DataAggregator.aggregate_daily_by_person(
            data, invalid_results=["対象外", "準備"]
        )

        self.assertIn("2026-05-01", by_name)
        self.assertEqual(by_name["2026-05-01"], {"alice": 1})
        self.assertNotIn("2026-06-01", by_name)

    def test_backward_compatible_without_invalid_results(self):
        data = [
            ["Pass", "alice", "2026-05-01", "Sheet1"],
            ["対象外", "bob", "2026-06-01", "Sheet1"],
        ]
        by_name = DataAggregator.aggregate_daily_by_person(data)

        self.assertIn("2026-06-01", by_name)


if __name__ == "__main__":
    unittest.main()
