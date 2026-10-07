// Data loader: passes the committed summary file through to the page. Pages never read raw rows.
import {readFileSync} from "node:fs";

process.stdout.write(readFileSync(new URL("../../data/summaries/dq_by_month.csv", import.meta.url)));
