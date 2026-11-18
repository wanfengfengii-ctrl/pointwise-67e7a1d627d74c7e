import sqlite3
from fractions import Fraction

from analysis.catalog import get_analysis
from analysis.freeze import freeze_revision
from records.readback import ReportNotFound, read_report
from records.schema import initialize_database
from reports.issue import issue_report
from specimen.registry import get_trial
from tests.fixtures import FRAME, SQUARE, TRIAL, DatabaseTestCase, area_rows
from traces.archive import archive_revision
from traces.import_rows import import_traces
from traces.lineage import InvalidParentRevision
from traces.revisions import ArchivedRevision, UnknownRevision, load_online_revision, load_revision_identity


class HandoffTests(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.register()

    def test_revision_and_reopen(self):
        old_revision, old_analysis = self.analysis_for([SQUARE])
        old_report = issue_report(self.db, old_analysis, FRAME)
        new_revision, new_analysis = self.analysis_for([], parent_id=old_revision)
        self.reopen()
        self.assertEqual(read_report(self.db, old_report.number), old_report)
        self.assertEqual(area_rows(old_report), ((1, 4),))
        old_recheck = issue_report(self.db, old_analysis, FRAME)
        new_report = issue_report(self.db, new_analysis, FRAME)
        self.assertEqual(area_rows(old_recheck), ((1, 4),))
        self.assertEqual(area_rows(new_report), ((0, 4),))
        self.assertEqual((old_recheck.analysis_id, old_recheck.revision_id), (old_analysis, old_revision))
        self.assertEqual((new_report.analysis_id, new_report.revision_id), (new_analysis, new_revision))
        self.assertEqual(load_revision_identity(self.db, new_revision).parent_id, old_revision)

    def test_parent_scope(self):
        other = self.register('CW-QA-02')
        a = import_traces(self.db, TRIAL, [SQUARE])
        b = import_traces(self.db, other, [SQUARE])
        original_a = load_online_revision(self.db, a)
        original_b = load_online_revision(self.db, b)
        for invalid_parent in (a, b + 1000):
            with self.subTest(invalid_parent=invalid_parent), self.assertRaises(InvalidParentRevision):
                import_traces(self.db, other, [], invalid_parent)
        self.assertEqual(self.revision_count(), 2)
        self.assertEqual(load_online_revision(self.db, a), original_a)
        self.assertEqual(load_online_revision(self.db, b), original_b)
        correction = import_traces(self.db, other, [], b)
        identity = load_revision_identity(self.db, correction)
        self.assertEqual((identity.trial_id, identity.parent_id), (other, b))

    def test_fraction_readback(self):
        revision, analysis = self.analysis_for([SQUARE])
        original = issue_report(self.db, analysis, (0, 0, (1, 3), 2))
        self.reopen()
        recovered = read_report(self.db, original.number)
        self.assertEqual(recovered, original)
        self.assertEqual((recovered.analysis_id, recovered.revision_id), (analysis, revision))
        self.assertEqual(recovered.breakdown.window.bounds(), (0, 0, Fraction(1, 3), 2))
        self.assertEqual(area_rows(recovered), ((1, Fraction(2, 3)),))
        self.assertIsInstance(recovered.breakdown.rows[0].area, Fraction)
        self.assertEqual(recovered.breakdown.total_area, Fraction(2, 3))

    def test_reinitialize_existing(self):
        trial = self.register('USER-TRIAL', (0, 0, 4, 2))
        old_revision, old_analysis = self.analysis_for([], trial)
        new_revision, new_analysis = self.analysis_for([SQUARE], trial, old_revision)
        original = issue_report(self.db, new_analysis, (0, 0, 1, 2))
        specimen = get_trial(self.db, trial)
        revisions = tuple(load_online_revision(self.db, number) for number in (old_revision, new_revision))
        analyses = tuple(get_analysis(self.db, number) for number in (old_analysis, new_analysis))
        counts = (self.revision_count(), self.analysis_count(), self.report_counts())

        initialize_database(self.path)
        initialize_database(self.path)
        self.reopen()
        self.assertEqual((self.revision_count(), self.analysis_count(), self.report_counts()), counts)
        self.assertEqual(get_trial(self.db, trial), specimen)
        self.assertEqual(tuple(load_online_revision(self.db, number) for number in (old_revision, new_revision)), revisions)
        self.assertEqual(tuple(get_analysis(self.db, number) for number in (old_analysis, new_analysis)), analyses)
        self.assertEqual(read_report(self.db, original.number), original)
        self.assertEqual(area_rows(original), ((1, 2),))
        newest, latest = self.analysis_for([], trial, new_revision)
        added = issue_report(self.db, latest, FRAME)
        self.assertEqual((added.analysis_id, added.revision_id), (latest, newest))
        self.assertEqual(area_rows(added), ((0, 4),))

    def test_unknown_report(self):
        _, analysis = self.analysis_for([SQUARE])
        original = issue_report(self.db, analysis, FRAME)
        self.reopen()
        with self.assertRaises(ReportNotFound):
            read_report(self.db, original.number + 1000)
        self.assertEqual(read_report(self.db, original.number), original)

    def test_source_archive(self):
        revision, analysis = self.analysis_for([SQUARE])
        archived = archive_revision(self.db, revision)
        self.reopen()
        self.assertTrue(archived.archived)
        self.assertEqual(load_revision_identity(self.db, revision), archived)
        with self.assertRaises(ArchivedRevision):
            freeze_revision(self.db, revision)
        self.assertEqual(self.analysis_count(), 1)
        report = issue_report(self.db, analysis, (0, 0, 1, 2))
        self.assertEqual(area_rows(report), ((1, 2),))
        self.assertEqual(report.revision_id, revision)

    def test_signed_reopen(self):
        old_revision, old_analysis = self.analysis_for([SQUARE, SQUARE])
        original = issue_report(self.db, old_analysis, FRAME)
        new_revision, new_analysis = self.analysis_for([SQUARE], parent_id=old_revision)
        archive_revision(self.db, old_revision)
        self.reopen()
        recovered = read_report(self.db, original.number)
        old_recheck = issue_report(self.db, old_analysis, FRAME)
        new_report = issue_report(self.db, new_analysis, FRAME)
        self.assertEqual(recovered, original)
        self.assertEqual(area_rows(recovered), ((2, 4),))
        self.assertEqual(area_rows(old_recheck), ((2, 4),))
        self.assertEqual(area_rows(new_report), ((1, 4),))
        self.assertEqual((old_recheck.analysis_id, old_recheck.revision_id), (old_analysis, old_revision))
        self.assertEqual((new_report.analysis_id, new_report.revision_id), (new_analysis, new_revision))
        with self.assertRaises(ArchivedRevision):
            freeze_revision(self.db, old_revision)
        self.assertEqual(self.analysis_count(), 2)

    def test_archive_replay(self):
        parent = import_traces(self.db, TRIAL, [])
        revision, analysis = self.analysis_for([SQUARE], parent_id=parent)
        previous_analysis = get_analysis(self.db, analysis)
        original = issue_report(self.db, analysis, FRAME)
        original_payload = self.db.execute(
            'SELECT payload FROM online_traces WHERE revision_id = ?', (revision,),
        ).fetchone()[0]
        first = archive_revision(self.db, revision)
        self.reopen()
        self.assertEqual(archive_revision(self.db, revision), first)
        self.assertEqual(first.parent_id, parent)
        self.assertTrue(first.archived)
        self.assertIsNone(self.db.execute('SELECT 1 FROM online_traces WHERE revision_id = ?', (revision,)).fetchone())
        archived_payload = self.db.execute(
            'SELECT payload FROM archived_traces WHERE revision_id = ?', (revision,),
        ).fetchone()[0]
        self.assertEqual(archived_payload, original_payload)
        self.assertEqual(get_analysis(self.db, analysis), previous_analysis)
        self.assertEqual(read_report(self.db, original.number), original)
        for action in (archive_revision, freeze_revision):
            with self.assertRaises(UnknownRevision):
                action(self.db, revision + 1000)
        self.assertEqual(self.analysis_count(), 1)
        child = import_traces(self.db, TRIAL, [], revision)
        self.assertEqual(load_revision_identity(self.db, child).parent_id, revision)

    def test_archive_write_failure_leaves_source_online(self):
        revision, analysis = self.analysis_for([SQUARE])
        source = load_online_revision(self.db, revision)
        self.db.execute('''CREATE TEMP TRIGGER abort_archive_state
            BEFORE UPDATE OF archived ON trace_revision
            BEGIN SELECT RAISE(ABORT, 'archive state could not be written'); END''')
        with self.assertRaisesRegex(sqlite3.IntegrityError, 'archive state could not be written'):
            archive_revision(self.db, revision)
        self.assertEqual(load_online_revision(self.db, revision), source)
        self.assertEqual(self.db.execute('SELECT count(*) FROM archived_traces').fetchone()[0], 0)
        self.assertEqual(area_rows(issue_report(self.db, analysis, FRAME)), ((1, 4),))

    def test_freeze_commit_failure_leaves_no_analysis(self):
        revision = import_traces(self.db, TRIAL, [SQUARE])
        self.db.execute('CREATE TEMP TABLE approvals (analysis_id INTEGER PRIMARY KEY)')
        self.db.execute('''CREATE TEMP TABLE pending_freezes (
            analysis_id INTEGER REFERENCES approvals(analysis_id) DEFERRABLE INITIALLY DEFERRED
        )''')
        self.db.execute('''CREATE TEMP TRIGGER require_approval AFTER INSERT ON frozen_analysis
            BEGIN INSERT INTO pending_freezes(analysis_id) VALUES (new.analysis_id); END''')
        with self.assertRaisesRegex(sqlite3.IntegrityError, 'FOREIGN KEY constraint failed'):
            freeze_revision(self.db, revision)
        self.assertEqual(self.analysis_count(), 0)
        self.assertEqual(self.db.execute('SELECT count(*) FROM pending_freezes').fetchone()[0], 0)
        self.db.execute('DROP TRIGGER require_approval')
        analysis = freeze_revision(self.db, revision)
        self.assertEqual(area_rows(issue_report(self.db, analysis, FRAME)), ((1, 4),))
