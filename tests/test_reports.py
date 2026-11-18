from fractions import Fraction

from analysis.catalog import UnknownAnalysis
from records.connection import open_database
from records.readback import ReportNotFound, read_report
from reports.issue import issue_report
from tests.fixtures import FRAME, SQUARE, DatabaseTestCase, area_rows, box


class SignoffInterrupted(RuntimeError):
    pass


class ReportTests(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.register()

    def test_single_loop_outside_area(self):
        revision, analysis = self.analysis_for([SQUARE])
        report = issue_report(self.db, analysis, (0, 0, 3, 2))
        self.assertEqual(area_rows(report), ((0, 2), (1, 4)))
        self.assertEqual(report.breakdown.total_area, 6)
        self.assertEqual((report.analysis_id, report.revision_id), (analysis, revision))
        self.assertEqual(read_report(self.db, report.number), report)

    def test_repeated_loop_area(self):
        revision, analysis = self.analysis_for([SQUARE, SQUARE])
        report = issue_report(self.db, analysis, FRAME)
        self.assertEqual(area_rows(report), ((2, 4),), 'WINDING_AREA_MISMATCH')
        self.assertEqual(report.breakdown.total_area, 4)
        self.assertEqual((report.analysis_id, report.revision_id), (analysis, revision))

    def test_directed_counts(self):
        cases = [
            ([SQUARE], ((1, 4),)),
            ([SQUARE, SQUARE], ((2, 4),)),
            ([SQUARE, SQUARE[::-1]], ((0, 4),)),
            ([SQUARE[::-1]], ((-1, 4),)),
        ]
        for loops, expected in cases:
            with self.subTest(expected=expected):
                revision, analysis = self.analysis_for(loops)
                report = issue_report(self.db, analysis, FRAME)
                self.assertEqual(area_rows(report), expected, 'WINDING_AREA_MISMATCH')
                self.assertEqual((report.analysis_id, report.revision_id), (analysis, revision))

    def test_partial_overlap(self):
        self.register('CW-WIDE', (0, 0, 3, 2))
        shifted = box(1, 0, 3, 2)
        _, same = self.analysis_for([SQUARE, shifted], 'CW-WIDE')
        _, opposite = self.analysis_for([SQUARE, shifted[::-1]], 'CW-WIDE')
        window = (0, 0, 3, 2)
        self.assertEqual(area_rows(issue_report(self.db, same, window)), ((1, 4), (2, 2)))
        self.assertEqual(area_rows(issue_report(self.db, opposite, window)), ((-1, 2), (0, 2), (1, 2)))

    def test_self_cross_crop(self):
        loop = [(0, 0), (2, 2), (0, 2), (2, 0), (0, 0)]
        _, analysis = self.analysis_for([loop])
        half = issue_report(self.db, analysis, (0, 0, 1, 2))
        self.assertEqual(area_rows(half), ((-1, Fraction(1, 2)), (0, 1), (1, Fraction(1, 2))))
        self.assertEqual(half.breakdown.total_area, 2)
        whole = issue_report(self.db, analysis, FRAME)
        self.assertEqual(area_rows(whole), ((-1, 1), (0, 2), (1, 1)))

    def test_sloped_window(self):
        loop = [(0, 0), (2, 0), (2, 2), (0, 0)]
        _, analysis = self.analysis_for([loop])
        report = issue_report(self.db, analysis, (0, 0, 2, (3, 2)))
        self.assertEqual(area_rows(report), ((0, Fraction(9, 8)), (1, Fraction(15, 8))))
        self.assertEqual(report.breakdown.total_area, 3)

    def test_outside_only(self):
        _, analysis = self.analysis_for([SQUARE])
        report = issue_report(self.db, analysis, (3, 0, 4, 2))
        self.assertEqual(area_rows(report), ((0, 2),))

    def test_stationary_and_repeated_passages_in_one_loop(self):
        traced_twice = SQUARE + SQUARE[:1] + SQUARE[1:]
        _, analysis = self.analysis_for([traced_twice, ((1, 1), (1, 1))])
        self.assertEqual(area_rows(issue_report(self.db, analysis, (0, 1, 2, 3))), ((0, 2), (2, 2)))

    def test_unknown_analysis(self):
        _, analysis = self.analysis_for([SQUARE])
        previous = issue_report(self.db, analysis, FRAME)
        with self.assertRaises(UnknownAnalysis):
            issue_report(self.db, analysis + 1000, FRAME)
        self.assertEqual(self.report_counts(), (1, 1))
        self.assertEqual(read_report(self.db, previous.number), previous)

    def test_degenerate_window(self):
        _, analysis = self.analysis_for([SQUARE])
        with self.assertRaises(ValueError):
            issue_report(self.db, analysis, (1, 0, 1, 2))
        self.assertEqual(self.report_counts(), (0, 0))

    def test_invalid_bounds(self):
        _, analysis = self.analysis_for([SQUARE])
        for bounds in ((2, 0, 0, 2), (0, 1, 2, 1), (0, 0, (1, 0), 2)):
            with self.subTest(bounds=bounds), self.assertRaises(ValueError):
                issue_report(self.db, analysis, bounds)
        self.assertEqual(self.report_counts(), (0, 0))

    def test_commit_failure(self):
        _, analysis = self.analysis_for([SQUARE])
        original = issue_report(self.db, analysis, FRAME)
        attempted = []

        def interrupt(number):
            self.assertEqual(self.report_counts(), (2, 2))
            self.assertEqual(area_rows(read_report(self.db, number)), ((1, 2),))
            attempted.append(number)
            raise SignoffInterrupted('shift signoff was interrupted')

        with self.assertRaises(SignoffInterrupted):
            issue_report(self.db, analysis, (0, 0, 1, 2), before_commit=interrupt)
        self.assertEqual(len(attempted), 1)
        self.assertEqual(self.report_counts(), (1, 1))
        self.assertEqual(read_report(self.db, original.number), original)
        with self.assertRaises(ReportNotFound):
            read_report(self.db, attempted[0])

    def test_retry_after_rollback(self):
        _, analysis = self.analysis_for([SQUARE])
        original = issue_report(self.db, analysis, FRAME)
        attempts = []

        def interrupt(number):
            attempts.append(number)
            with open_database(self.path) as observer:
                with self.assertRaises(ReportNotFound):
                    read_report(observer, number)
                self.assertEqual(read_report(observer, original.number), original)
            raise SignoffInterrupted('shift signoff was interrupted')

        window = (0, 0, (1, 3), 2)
        with self.assertRaises(SignoffInterrupted):
            issue_report(self.db, analysis, window, before_commit=interrupt)
        self.reopen()
        self.assertEqual(self.report_counts(), (1, 1))
        self.assertEqual(len(attempts), 1)
        with self.assertRaises(ReportNotFound):
            read_report(self.db, attempts[0])
        retried = issue_report(self.db, analysis, window)
        self.reopen()
        self.assertEqual(self.report_counts(), (2, 2))
        self.assertNotEqual(retried.number, original.number)
        self.assertEqual(read_report(self.db, retried.number), retried)
        self.assertEqual(read_report(self.db, original.number), original)
        self.assertEqual(area_rows(retried), ((1, Fraction(2, 3)),))
