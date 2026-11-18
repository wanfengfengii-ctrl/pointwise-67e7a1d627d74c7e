# 澄湾薄膜圈划质控

澄湾薄膜试验线的工位用闭合折线记录返工区域。质控员按固定分析号为选定复检窗签发面积分级，接班员据此区分未覆盖、重复圈划和反向抵消，并可在源材料归档后复检。

## 运行

在项目根目录使用 Python 3.11 或以上版本，仅需标准库和随 Python 提供的 SQLite。`run-manifest.json` 列出操作入口，`.pointwise-runtime.json` 登记同一组核验和演示命令。运行清单的 `version` 为 1，`kind` 为 `cli`，`setup` 无需安装步骤，`verify` 和 `demo` 分别执行完整业务核验与交班演示。

```sh
python3 -B -m scripts.init_db inspection.sqlite3
python3 -B -m unittest discover -s tests -t . -v
python3 -B -m scripts.verify
python3 -B -m scripts.demo
```

初始化可重复执行并保留原库中的试片、修订、分析和报告。演示使用独立临时库，读取 `examples/shift_inputs.json`，对照 `examples/shift_expected.json` 完成签发、补正、归档、重开、按号读回和换窗复检。

## Python 接口

先以 `records.schema.initialize_database(path)` 初始化，再用 `with records.connection.open_database(path) as db` 打开。每次写入操作管理自己的事务。

| 模块 | 接口 | 返回值 |
| --- | --- | --- |
| `specimen.registry` | `register_trial(db, trial_id, bounds)` / `get_trial(db, trial_id)` | 试片号 / 固定试片与测量框 |
| `traces.import_rows` | `import_traces(db, trial_id, rows, parent_id=None)` | 新源修订号 |
| `traces.revisions` | `load_revision_identity(db, revision_id)` / `load_online_revision(db, revision_id)` | 修订身份 / 带有序原始圈划的在线修订 |
| `analysis.freeze` | `freeze_revision(db, revision_id)` | 新冻结分析号 |
| `analysis.catalog` | `get_analysis(db, analysis_id)` | 固定分析、来源和冻结证据 |
| `reports.issue` | `issue_report(db, analysis_id, bounds)` | 已提交的签发报告 |
| `records.readback` | `read_report(db, number)` | 原签发报告 |
| `traces.archive` | `archive_revision(db, revision_id)` | 保留谱系的已归档修订身份 |

试片号是非空白字符串。其余编号由业务库分配。框和窗口按 `[左, 下, 右, 上]` 输入，两轴都要求严格递增。坐标单位为毫米，可用整数、Python `Fraction` 或 `[整数分子, 非零整数分母]`。例如 `[[1, 3], 2]` 表示点 `(1/3, 2)`。`rows` 是折线数组，每条折线至少给出一段的两个端点，首末点相同，所有点都在测量框内或边界上。空数组表示没有圈划。补正必须以同试片修订为父，并交付完整圈划集。已经归档的修订仍可作为补正父项。

分析固定到传入的源修订，归档后拒绝对此来源新增冻结。已冻结编号可继续用于任意正面积窗口，包括完全在测量框之外的窗口。逆时针绕数为正。每次经过按方向累计，反向经过抵消，静止经过和边界面积为零。自交按各处的实际绕数计算。报告包含 `number`、`analysis_id`、`revision_id` 和 `breakdown`。分级含窗口、有序的 `(winding, area)` 行及合计。面积为精确 `Fraction` 平方毫米，每级仅在面积为正时出现，含符合此条件的零级，合计等于窗口面积。

未知试片、修订、分析和报告以各模块的 `LookupError` 子类报告。非法输入、登记冲突、父项不合法以及归档源没有在线明细以 `ValueError` 子类报告。拒绝的导入或签发不会留下业务记录。`issue_report` 可选的 `before_commit(number)` 在正文和索引暂存后执行。回调异常由调用方收到，两处写入一起回滚。不同成功签发分别取得稳定编号。重开数据库后按原号读回签发时的窗口、来源及面积。

## 复检核账

同一个 2×2 方框单圈、同向两圈、正反各一圈及单独反向一圈，在原方框窗口内的正确面积分级依次为 `{1: 4}`、`{2: 4}`、`{0: 4}` 和 `{-1: 4}`。当前同向重复和正反相抵的复检均报为 `{1: 4}`。下面的命令执行原事故断言。

```sh
python3 -B -m unittest -v tests.test_reports.ReportTests.test_repeated_loop_area tests.test_reports.ReportTests.test_directed_counts
```

把自交圈划 `(0,0) → (2,2) → (0,2) → (2,0) → (0,0)` 放入 `[0,0,1,2]` 窗口，正确分级为 `{-1: 1/2, 0: 1, 1: 1/2}`。两个错开一毫米的同向 2×2 方框在 3×2 外接窗口内，正确分级为 `{1: 4, 2: 2}`。

交班演示中，工位把两圈补正成一圈并归档旧来源。旧号读回及凭旧分析重新签发原窗均应为 `{2: 4}`，新分析为 `{1: 4}`。旧分析换查 `[0,0,[1,3],2]` 窗口仍应为 `{2: 2/3}`。报告所用圈划证据来自指定的冻结分析。
