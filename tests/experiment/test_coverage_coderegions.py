import unittest

from varats.experiments.playground.coverage import CodeRegion

CODE_REGION_1 = CodeRegion.from_list([9, 79, 17, 2, 4, 0, 0, 0], "main")


class TestCodeRegion(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.CODE_REGION_1 = CodeRegion(
            start_line=9,
            start_column=79,
            end_line=17,
            end_column=2,
            count=4,
            function="main"
        )
        self.CODE_REGION_2 = CodeRegion(
            start_line=9,
            start_column=80,
            end_line=17,
            end_column=1,
            count=0,
            function="main"
        )
        self.CODE_REGION_1.insert(self.CODE_REGION_2)

    def test_eq(self):
        self.assertEqual(self.CODE_REGION_1, CODE_REGION_1)

    def test_not_eq_1(self):
        self.CODE_REGION_1.start_line = 1
        self.assertNotEqual(self.CODE_REGION_1, CODE_REGION_1)

    def test_not_eq_2(self):
        self.CODE_REGION_1.end_line = 18
        self.assertNotEqual(self.CODE_REGION_1, CODE_REGION_1)

    def test_not_eq_3(self):
        self.CODE_REGION_1.end_column = 1
        self.assertNotEqual(self.CODE_REGION_1, CODE_REGION_1)

    def test_less_1(self):
        self.assertFalse(self.CODE_REGION_1 < CODE_REGION_1)
        self.assertTrue(self.CODE_REGION_1 <= CODE_REGION_1)

        self.CODE_REGION_1.start_column = 78
        self.assertTrue(self.CODE_REGION_1 < CODE_REGION_1)
        self.assertFalse(CODE_REGION_1 < self.CODE_REGION_1)

    def test_greater_1(self):
        self.assertFalse(self.CODE_REGION_1 > CODE_REGION_1)
        self.assertTrue(self.CODE_REGION_1 >= CODE_REGION_1)

        self.CODE_REGION_1.start_column = 80
        self.assertTrue(self.CODE_REGION_1 > CODE_REGION_1)
        self.assertFalse(CODE_REGION_1 > self.CODE_REGION_1)

    def test_subregions(self):
        self.assertFalse(self.CODE_REGION_1.is_subregion(self.CODE_REGION_1))

        self.assertTrue(self.CODE_REGION_1.is_subregion(self.CODE_REGION_2))
        self.assertFalse(self.CODE_REGION_2.is_subregion(self.CODE_REGION_1))

        self.CODE_REGION_1.start_line = 10
        self.CODE_REGION_2.end_column = 2
        self.assertFalse(self.CODE_REGION_1.is_subregion(self.CODE_REGION_2))
        self.assertFalse(self.CODE_REGION_2.is_subregion(self.CODE_REGION_1))

    def test_is_covered(self):
        self.assertTrue(self.CODE_REGION_1.is_covered())
        self.assertFalse(self.CODE_REGION_2.is_covered())

    def test_contains(self):
        self.assertTrue(self.CODE_REGION_2 in self.CODE_REGION_1)
        self.assertFalse(self.CODE_REGION_1 in self.CODE_REGION_2)

    def test_parent(self):
        self.assertFalse(self.CODE_REGION_1.has_parent())
        self.assertIsNone(self.CODE_REGION_1.parent)

        self.assertTrue(self.CODE_REGION_2.has_parent())
        self.assertEqual(self.CODE_REGION_2.parent, self.CODE_REGION_1)

    def test_insert(self):
        root = CodeRegion.from_list([0, 0, 100, 100, 5], "main")
        left = CodeRegion.from_list([0, 1, 49, 100, 5], "main")
        right = CodeRegion.from_list([50, 0, 100, 99, 5], "main")
        left_left = CodeRegion.from_list([30, 0, 40, 100, 3], "main")
        left_left_2 = CodeRegion.from_list([10, 0, 20, 100, 3], "main")
        right_right = CodeRegion.from_list([60, 0, 80, 100, 2], "main")

        root.insert(left)
        root.insert(right)
        root.insert(left_left)
        root.insert(left_left_2)
        root.insert(right_right)

        self.assertTrue(root.is_subregion(left))
        self.assertTrue(root.is_subregion(right))
        self.assertTrue(root.is_subregion(left_left))
        self.assertTrue(root.is_subregion(right_right))
        self.assertTrue(left.is_subregion(left_left))
        self.assertTrue(left.is_subregion(left_left_2))
        self.assertTrue(right.is_subregion(right_right))

        self.assertFalse(right.is_subregion(left))
        self.assertFalse(right.is_subregion(left_left))
        self.assertFalse(right.is_subregion(left_left_2))
        self.assertFalse(left.is_subregion(right))
        self.assertFalse(left.is_subregion(right_right))
        self.assertFalse(left.is_subregion(root))
        self.assertFalse(right.is_subregion(root))
