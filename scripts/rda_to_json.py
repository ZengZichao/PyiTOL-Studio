"""Convert itol.toolkit R data files (``data/*.rda``) into JSON resources.

One-off archive script from the development plan §8: run it once against
``PyiTOL-参考软件/软件-itol.toolkit-1.2.2/data`` to regenerate the raw
parameter-range table used to curate ``resources/param_ranges.json``.

Requires R with jsonlite on PATH (``Rscript -e 'install.packages("jsonlite",
repos="https://cloud.r-project.org")'``).

Usage:
    python scripts/rda_to_json.py <itol.toolkit-data-dir> <output.json>
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

R_SCRIPT = r"""
suppressPackageStartupMessages(library(jsonlite))
args <- commandArgs(trailingOnly = TRUE)
input <- args[[1]]
output <- args[[2]]
convert <- function(name) {
  obj <- get(load(name))
  as.list(as.data.frame(obj))
}
tables <- list()
for (path in list.files(input, pattern = "\\.rda$", full.names = TRUE)) {
  key <- tools::file_path_sans_ext(basename(path))
  tables[[key]] <- convert(path)
}
write_json(tables, output, auto_unbox = TRUE, pretty = TRUE, na = "null")
"""


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    data_dir, output = Path(argv[1]), Path(argv[2])
    if not data_dir.is_dir():
        print(f"输入目录不存在：{data_dir}", file=sys.stderr)
        return 1
    r_files = sorted(data_dir.glob("*.rda"))
    if not r_files:
        print(f"目录中没有 .rda 文件：{data_dir}", file=sys.stderr)
        return 1
    with tempfile.NamedTemporaryFile("w", suffix=".R", delete=False) as script:
        script.write(R_SCRIPT)
        script_path = script.name
    result = subprocess.run(
        ["Rscript", script_path, str(data_dir), str(output)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(f"Rscript 失败：\n{result.stderr}", file=sys.stderr)
        return 1
    payload = json.loads(output.read_text(encoding="utf-8"))
    print(f"已转换 {len(payload)} 个数据表 → {output}")
    print("提醒：该 JSON 为原始范围表；运行时资源 resources/param_ranges.json 需人工策展合并（开发方案 §6.2）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
