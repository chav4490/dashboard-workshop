// Data loader: passes the committed summary file through to the page. Pages never read raw rows.
import {readFileSync} from "node:fs";

process.stdout.write(readFileSync(new URL("../../data/summaries/daily.csv", import.meta.url)));
