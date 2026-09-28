import unittest

from scripts.ci_unittest_runner import (
    HEAVY_MODULE,
    PartitionError,
    discover_partition,
    partition_tests,
)


def synthetic_test(module, class_name="SyntheticTest"):
    case_type = type(
        class_name,
        (unittest.TestCase,),
        {"__module__": module, "runTest": lambda self: None},
    )
    return case_type()


class CIUnittestRunnerTests(unittest.TestCase):
    def test_full_inventory_partitions_without_overlap_or_loss(self):
        ordinary = synthetic_test("tests.test_ordinary")
        heavy_one = synthetic_test(HEAVY_MODULE, "HeavyOne")
        heavy_two = synthetic_test(HEAVY_MODULE, "HeavyTwo")
        full = [ordinary, heavy_one, heavy_two]

        standard, heavy = partition_tests(full)

        self.assertEqual(standard, [ordinary])
        self.assertEqual(heavy, [heavy_one, heavy_two])
        self.assertFalse(set(map(id, standard)) & set(map(id, heavy)))
        self.assertCountEqual(standard + heavy, full)

    def test_ordinary_synthetic_test_naturally_lands_in_standard(self):
        existing = synthetic_test(HEAVY_MODULE, "Heavy")
        newly_added = synthetic_test("tests.test_future_feature", "FutureTest")
        standard, heavy = partition_tests([existing, newly_added])
        self.assertEqual(standard, [newly_added])
        self.assertEqual(heavy, [existing])

    def test_exact_module_boundary_does_not_exclude_similar_name(self):
        exact = synthetic_test(HEAVY_MODULE, "ExactHeavy")
        similar = synthetic_test(HEAVY_MODULE + "_extra", "SimilarName")
        standard, heavy = partition_tests([exact, similar])
        self.assertEqual(standard, [similar])
        self.assertEqual(heavy, [exact])

    def test_empty_heavy_partition_fails_closed(self):
        with self.assertRaises(PartitionError):
            partition_tests([synthetic_test("tests.test_ordinary")])

    def test_repository_discovery_has_nonempty_exact_heavy_partition(self):
        standard, heavy = discover_partition()
        self.assertTrue(standard)
        self.assertTrue(heavy)
        self.assertTrue(
            all(test.__class__.__module__ == HEAVY_MODULE for test in heavy)
        )
        self.assertFalse(set(test.id() for test in standard) & set(test.id() for test in heavy))


if __name__ == "__main__":
    unittest.main()
