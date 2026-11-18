import json
from pathlib import Path
from tempfile import TemporaryDirectory

from analysis.freeze import freeze_revision
from records.connection import open_database
from records.readback import read_report
from records.schema import initialize_database
from reports.breakdown import InspectionReport
from reports.issue import issue_report
from specimen.registry import register_trial
from traces.archive import archive_revision
from traces.import_rows import import_traces
from traces.revisions import load_revision_identity


EXAMPLES = Path(__file__).resolve().parents[1] / 'examples'


def summarize(report: InspectionReport) -> list[list[int | str]]:
    return [[row.winding, str(row.area)] for row in report.breakdown.rows]


def run_shift(path: Path, inputs: dict) -> tuple[dict, dict]:
    initialize_database(path)
    with open_database(path) as db:
        trial = register_trial(db, inputs['trial'], inputs['frame'])
        old_revision = import_traces(db, trial, inputs['initial'])
        old_analysis = freeze_revision(db, old_revision)
        original = issue_report(db, old_analysis, inputs['window'])
        correction = import_traces(db, trial, inputs['correction'], old_revision)
        new_analysis = freeze_revision(db, correction)
        archive_revision(db, old_revision)

    with open_database(path) as db:
        recovered = read_report(db, original.number)
        rechecked = issue_report(db, old_analysis, inputs['window'])
        corrected = issue_report(db, new_analysis, inputs['window'])
        followup = issue_report(db, old_analysis, inputs['followup_window'])
        old_source = load_revision_identity(db, old_revision)
        new_source = load_revision_identity(db, correction)

    actual = {'issued': summarize(original), 'total_area': str(original.breakdown.total_area)}
    downstream = {
        'readback': summarize(recovered),
        'old_recheck': summarize(rechecked),
        'corrected': summarize(corrected),
        'followup': summarize(followup),
        'history_matches': recovered == original,
        'sources_match': (
            (rechecked.analysis_id, rechecked.revision_id) == (old_analysis, old_revision)
            and (followup.analysis_id, followup.revision_id) == (old_analysis, old_revision)
            and (corrected.analysis_id, corrected.revision_id) == (new_analysis, correction)
            and new_source.parent_id == old_revision
        ),
        'archived': old_source.archived,
    }
    return actual, downstream


def main() -> None:
    inputs = json.loads((EXAMPLES / 'shift_inputs.json').read_text(encoding='utf-8'))
    expectation = json.loads((EXAMPLES / 'shift_expected.json').read_text(encoding='utf-8'))
    with TemporaryDirectory() as directory:
        actual, downstream = run_shift(Path(directory) / 'shift.sqlite3', inputs)
    expected = expectation['expected']
    downstream_expected = expectation['downstream_expected']
    if actual != expected or downstream != downstream_expected:
        raise SystemExit(f'Shift reconciliation mismatch: issued={actual!r}, handoff={downstream!r}')
    print('POINTWISE_SCENARIO ' + json.dumps({
        'case_id': 'v8.signed_reopen',
        'input': inputs,
        'expected': expected,
        'actual': actual,
        'downstream_expected': downstream_expected,
        'downstream_actual': downstream,
        'code_paths': [
            'specimen/registry.py', 'traces/import_rows.py', 'analysis/freeze.py',
            'reports/area.py', 'reports/issue.py', 'traces/archive.py', 'records/readback.py',
        ],
        'oracle': '两圈沿同方向包住同一块 2×2 方框，窗口内部绕数为 2。补正为一圈后为 1。旧分析的 1/3×2 窄窗仍为两层，面积为 2/3。',
    }, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
