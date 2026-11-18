from fractions import Fraction

from specimen.coordinates import Point
from specimen.intake_policy import RegistrationConflict
from specimen.registry import UnknownTrial, get_trial, register_trial
from tests.fixtures import FRAME, SQUARE, TRIAL, DatabaseTestCase, box
from traces.import_rows import import_traces
from traces.loop_validation import InvalidTrace
from traces.revisions import load_online_revision


class IntakeTests(DatabaseTestCase):
    def test_register_and_import(self):
        self.assertEqual(self.register(), TRIAL)
        self.assertEqual(self.register(), TRIAL)
        self.assertEqual(self.db.execute('SELECT count(*) FROM trial').fetchone()[0], 1)
        revision_id = import_traces(self.db, TRIAL, [SQUARE])
        stored = load_online_revision(self.db, revision_id)
        self.assertEqual(self.revision_count(), 1)
        self.assertEqual(stored.identity.trial_id, TRIAL)
        self.assertIsNone(stored.identity.parent_id)
        self.assertFalse(stored.identity.archived)
        expected = tuple(Point(Fraction(x), Fraction(y)) for x, y in SQUARE)
        self.assertEqual(stored.loops, (expected,))

    def test_frame_conflict(self):
        self.register()
        revision_id = import_traces(self.db, TRIAL, [SQUARE])
        stored = load_online_revision(self.db, revision_id)
        self.assertEqual(self.register(bounds=([0, 2], 0, [4, 2], [6, 3])), TRIAL)
        with self.assertRaises(RegistrationConflict):
            self.register(bounds=(0, 0, 3, 2))
        self.reopen()
        self.assertEqual(get_trial(self.db, TRIAL).frame.bounds(), FRAME)
        with self.assertRaises(InvalidTrace):
            import_traces(self.db, TRIAL, [box(right=(5, 2))])
        self.assertEqual(self.revision_count(), 1)
        self.assertEqual(load_online_revision(self.db, revision_id), stored)

    def test_invalid_frame_creates_no_trial(self):
        with self.assertRaises(ValueError):
            register_trial(self.db, TRIAL, (2, 0, 0, 2))
        with self.assertRaises(UnknownTrial):
            get_trial(self.db, TRIAL)

    def test_open_trace_rejected(self):
        self.register()
        revision_id = import_traces(self.db, TRIAL, [SQUARE])
        stored = load_online_revision(self.db, revision_id)
        with self.assertRaises(InvalidTrace):
            import_traces(self.db, TRIAL, [SQUARE, SQUARE[:-1]])
        self.assertEqual(self.revision_count(), 1)
        self.assertEqual(load_online_revision(self.db, revision_id), stored)

    def test_coordinate_inputs(self):
        self.register()
        original = import_traces(self.db, TRIAL, [SQUARE])
        stored = load_online_revision(self.db, original)
        bad_points = [(1,), ([1, 0], 0), (3, 0), (None, 1), (0.5, 0)]
        for point in bad_points:
            with self.subTest(point=point), self.assertRaises(InvalidTrace):
                import_traces(self.db, TRIAL, [SQUARE, [(0, 0), point, (1, 1), (0, 0)]])
        self.assertEqual(self.revision_count(), 1)
        self.assertEqual(load_online_revision(self.db, original), stored)

        loop = [(0, 0), ([1, 3], 0), (1, [1, 3]), (0, 0)]
        revision_id = import_traces(self.db, TRIAL, [loop])
        self.reopen()
        actual = load_online_revision(self.db, revision_id).loops
        expected = (
            Point(Fraction(0), Fraction(0)),
            Point(Fraction(1, 3), Fraction(0)),
            Point(Fraction(1), Fraction(1, 3)),
            Point(Fraction(0), Fraction(0)),
        )
        self.assertEqual(actual, (expected,))
