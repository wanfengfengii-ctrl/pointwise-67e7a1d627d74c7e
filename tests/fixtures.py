import unittest
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory

from analysis.freeze import freeze_revision
from records.connection import open_database
from records.schema import initialize_database
from reports.breakdown import InspectionReport
from specimen.registry import register_trial
from traces.import_rows import import_traces


TRIAL = 'CW-QA-01'
FRAME = (0, 0, 2, 2)


def box(left=0, bottom=0, right=2, top=2):
    return ((left, bottom), (right, bottom), (right, top), (left, top), (left, bottom))


SQUARE = box()


def area_rows(report: InspectionReport):
    return tuple((row.winding, row.area) for row in report.breakdown.rows)


class DatabaseTestCase(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(TemporaryDirectory())
        self.path = Path(directory) / 'inspection.sqlite3'
        initialize_database(self.path)
        self.sessions = self.enterContext(ExitStack())
        self.reopen()

    def reopen(self):
        self.sessions.close()
        self.db = self.sessions.enter_context(open_database(self.path))

    def register(self, trial_id=TRIAL, bounds=FRAME):
        return register_trial(self.db, trial_id, bounds)

    def analysis_for(self, loops, trial_id=TRIAL, parent_id=None):
        revision_id = import_traces(self.db, trial_id, loops, parent_id)
        return revision_id, freeze_revision(self.db, revision_id)

    def revision_count(self):
        return self.db.execute('SELECT count(*) FROM trace_revision').fetchone()[0]

    def analysis_count(self):
        return self.db.execute('SELECT count(*) FROM frozen_analysis').fetchone()[0]

    def report_counts(self):
        row = self.db.execute(
            '''SELECT (SELECT count(*) FROM inspection_report),
                      (SELECT count(*) FROM report_index)''',
        ).fetchone()
        return tuple(row)
