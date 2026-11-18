from fractions import Fraction

from analysis.evidence import (
    DirectedPassage, FrozenEvidence, build_evidence, decode_evidence, encode_evidence,
)
from records.codec import encode_payload, encode_point
from reports.area import calculate_winding_areas, winding_at
from reports.window import make_window
from specimen.coordinates import Point
from tests.fixtures import FRAME, SQUARE, DatabaseTestCase, area_rows, box


def _points(loop):
    return tuple(Point(Fraction(x), Fraction(y)) for x, y in loop)


class SignedEvidenceTests(DatabaseTestCase):
    def test_repeated_and_opposite_passages_keep_signed_multiplicity(self):
        evidence = build_evidence((_points(SQUARE), _points(SQUARE)))
        # The 2x2 square has four distinct passages, each traversed twice.
        self.assertEqual(len(evidence.passages), 8)
        twice = FrozenEvidence(evidence.passages)
        decoded = decode_evidence(encode_evidence(twice))
        self.assertEqual(decoded, evidence)

        opposite = build_evidence((_points(SQUARE), _points(SQUARE[::-1])))
        # Opposite traversals remain distinct passages instead of collapsing or
        # being canonicalized into one undirected support segment.
        self.assertEqual(len(opposite.passages), 8)
        directed = {(passage.start, passage.end) for passage in opposite.passages}
        for passage in opposite.passages:
            self.assertIn((passage.end, passage.start), directed)

    def test_stationary_passages_are_dropped(self):
        stationary = ((Point(Fraction(1), Fraction(1)), Point(Fraction(1), Fraction(1))),)
        self.assertEqual(build_evidence(stationary), FrozenEvidence(()))
        self.assertEqual(build_evidence(()), FrozenEvidence(()))

    def test_legacy_undirected_payload_still_decodes(self):
        start = encode_point(Point(Fraction(0), Fraction(0)))
        end = encode_point(Point(Fraction(2), Fraction(0)))
        legacy = encode_payload({
            'version': 1,
            'kind': 'directed-passages',
            'passages': [[start, end]],
        })
        evidence = decode_evidence(legacy)
        self.assertEqual(evidence, FrozenEvidence((
            DirectedPassage(Point(Fraction(0), Fraction(0)), Point(Fraction(2), Fraction(0))),
        )))
        with self.assertRaises(ValueError):
            decode_evidence(encode_payload({'version': 99, 'kind': 'directed-passages', 'passages': []}))


class SignedWindingTests(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.register()

    def _analysis(self, loops):
        from analysis.catalog import get_analysis
        analysis_id = self.analysis_for(loops)[1]
        return get_analysis(self.db, analysis_id)

    def test_accident_reconciliation_cases(self):
        window = make_window(FRAME)
        expected = [
            ([SQUARE], {1: Fraction(4)}),
            ([SQUARE, SQUARE], {2: Fraction(4)}),
            ([SQUARE, SQUARE[::-1]], {0: Fraction(4)}),
            ([SQUARE[::-1]], {-1: Fraction(4)}),
        ]
        for loops, areas in expected:
            with self.subTest(loops=len(loops)):
                analysis = self._analysis(loops)
                self.assertEqual(calculate_winding_areas(analysis.evidence, window), areas)

    def test_self_crossing_uses_local_winding(self):
        loop = [(0, 0), (2, 2), (0, 2), (2, 0), (0, 0)]
        analysis = self._analysis([loop])
        report_rows = area_rows(self._issue(analysis.analysis_id, (0, 0, 1, 2)))
        self.assertEqual(report_rows, ((-1, Fraction(1, 2)), (0, 1), (1, Fraction(1, 2))))

    def _issue(self, analysis_id, bounds):
        from reports.issue import issue_report
        return issue_report(self.db, analysis_id, bounds)

    def test_offset_same_direction_squares_level_two(self):
        shifted = box(1, 0, 3, 2)
        self.register('CW-WIDE', (0, 0, 3, 2))
        analysis = self.analysis_for([SQUARE, shifted], 'CW-WIDE')[1]
        rows = area_rows(self._issue(analysis, (0, 0, 3, 2)))
        self.assertEqual(rows, ((1, Fraction(4)), (2, Fraction(2))))

    def test_rationals_and_partial_window_keep_exact_fractions(self):
        analysis = self._analysis([SQUARE])
        rows = area_rows(self._issue(analysis.analysis_id, (0, 0, [1, 3], 2)))
        self.assertEqual(rows, ((1, Fraction(2, 3)),))
        for _, area in rows:
            self.assertIsInstance(area, Fraction)

    def test_window_outside_trace_is_single_zero_level(self):
        analysis = self._analysis([SQUARE])
        report = self._issue(analysis.analysis_id, (3, 0, 4, 2))
        self.assertEqual(area_rows(report), ((0, Fraction(2)),))
        self.assertEqual(report.breakdown.total_area, Fraction(2))

    def test_rows_are_sorted_and_levels_sum_to_window_area(self):
        shifted = box(1, 0, 3, 2)
        self.register('CW-WIDE', (0, 0, 3, 2))
        analysis = self.analysis_for([SQUARE, shifted[::-1]], 'CW-WIDE')[1]
        report = self._issue(analysis, (0, 0, 3, 2))
        windings = [row.winding for row in report.breakdown.rows]
        self.assertEqual(windings, sorted(windings))
        self.assertEqual(
            sum((row.area for row in report.breakdown.rows), Fraction()),
            report.breakdown.window.area,
        )
        self.assertTrue(all(row.area > 0 for row in report.breakdown.rows))

    def test_winding_at_helper_signs(self):
        evidence = build_evidence((_points(SQUARE), _points(SQUARE)))
        self.assertEqual(winding_at(evidence.passages, Fraction(1), Fraction(1)), 2)
        reversed_evidence = build_evidence((_points(SQUARE[::-1]),))
        self.assertEqual(winding_at(reversed_evidence.passages, Fraction(1), Fraction(1)), -1)
        canceled = build_evidence((_points(SQUARE), _points(SQUARE[::-1])))
        self.assertEqual(winding_at(canceled.passages, Fraction(1), Fraction(1)), 0)
        self.assertEqual(winding_at(evidence.passages, Fraction(5), Fraction(1)), 0)
