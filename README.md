# video-shotcraft-draft-verify

A zero-dependency, offline verifier for the JianYing / CapCut draft directories
that [video-shotcraft](https://github.com/Vincentwei1021/video-shotcraft)'s
`jianying-export` writes — so a broken draft is caught before JianYing is opened,
not after it says “内容已损坏 / 媒体丢失 / 暂无访问权限”.

Upstream: https://github.com/Vincentwei1021/video-shotcraft

Why now: video-shotcraft is on GitHub Trending (monthly list, 2026-11-16) and its
JianYing export is the step users run last. The export doc already demands a
post-install self-check of tracks, segments, duration, media registration and
paths, and it admits the Windows path has never been verified on a real machine.
The repository implements neither check as code: `install()` only copies,
registers and swaps directories, while `smoke_test.py` ends by asking a human to
open JianYing and look. This tool turns that missing step into an exit code.

## What the upstream does and what it does not

`video-shotcraft` renders a Remotion timeline and exports an editable
JianYing/CapCut draft: `draft_info.json` (Mac) / `draft_content.json` (Windows),
`draft_meta_info.json`, bundled `Resources/`, text and audio tracks.

The gap, from the upstream's own docs and source:

- **B-level**: `references/jianying-export.md` §6 验收, item 1 requires
  “脚本自检：读装好的 `draft_info.json` 核对轨道数/段数/时长，媒体登记逐条
  `os.path.exists` 且路径都在草稿目录内。”
  ([doc lines 173–174](https://github.com/Vincentwei1021/video-shotcraft/blob/main/references/jianying-export.md#L173-L174)).
- **C-level**: no function implements it. `mac_draft.py` has 15 top-level
  functions — `install()` at
  [lines 330–378](https://github.com/Vincentwei1021/video-shotcraft/blob/main/jianying-export/mac_draft.py#L330-L378)
  checks whether JianYing is running, backs up the registry and swaps the
  directory; it never re-reads the installed draft to verify track/segment
  references or the `draft_materials(type 0)` pool.
- **B-level**: the same doc says the Windows path is
  “[按上游支持路径实现但未真机验证](https://github.com/Vincentwei1021/video-shotcraft/blob/main/references/jianying-export.md#L11-L12)”,
  so the first Windows run is a manual smoke test.
- **B-level**: the exporter writes device fingerprints
  (`device_id`/`hard_disk_id`/`mac_address`) and the doc warns
  “[自包含草稿目录不要直接分发给他人](https://github.com/Vincentwei1021/video-shotcraft/blob/main/references/jianying-export.md#L181-L183)”;
  nothing checks for that leakage before a directory is shared.

## What this tool does / does not do

It reads a draft directory and checks, entirely offline:

| ID | Severity | Check |
| --- | --- | --- |
| J001/J002/J004/J005/J006 | error/warn | top-level fields, material ids, duplicates |
| J003 | error | `draft_info.json` and `draft_content.json` disagree (Mac and Windows would import different timelines) |
| J010/J011/J012 | error | track type, dangling `material_id`, material on the wrong track type |
| J013/J014/J015 | error | negative/zero target range, target beyond draft duration, source range beyond material duration |
| J016 | error | two segments overlap on the same track, with the exact ranges |
| J020/J021 | error/warn | media file missing, media path escaping the draft directory |
| J022/J023/J024/J031 | error/warn | media missing from `draft_meta_info` type-0 pool, stale registration, missing meta, `tm_duration` drift |
| J025/J030 | warn | Windows absolute path uncheckable here, machine-fingerprint fields present |

It **does not** launch JianYing, decode media, judge whether a cut looks good,
or validate encrypted drafts (JianYing rewrites plaintext drafts after opening —
a one-way conversion). It validates structure and references, not aesthetics.

## Install

Python 3.8+, standard library only. Nothing to install:

```bash
git clone git@github-linmoxi33:linmoxi33/video-shotcraft-draft-verify.git
cd video-shotcraft-draft-verify
python3 bin/video-shotcraft-draft-verify examples/in/valid-mac
```

## Usage

```bash
python3 bin/video-shotcraft-draft-verify <draft-dir>
python3 bin/video-shotcraft-draft-verify <draft-dir> --json
python3 bin/video-shotcraft-draft-verify <draft-dir> --json --strict
python3 bin/video-shotcraft-draft-verify <draft-dir> --allow-external-media
```

`--strict` promotes warnings to errors (useful in CI before publishing a draft).
`--allow-external-media` suppresses J021 for Windows drafts that legitimately
reference media outside the draft directory.

Real output on the broken fixture (`examples/in/broken-mac`):

```json
{
  "draft": "examples/in/broken-mac",
  "entry": "draft_info.json",
  "findings": [
    {"id": "J011", "severity": "error", "where": "tracks[1].segments[1]",
     "message": "segment references unknown material_id 'm-missing'"},
    {"id": "J016", "severity": "error", "where": "tracks[0]",
     "message": "segments 0 and 1 overlap on the same track (0.000000s..6.000000s vs 5.000000s..6.000000s)"}
  ],
  "ok": false,
  "stats": {"errors": 9, "materials": 3, "media": 2, "segments": 5,
            "tracks": 3, "warnings": 3},
  "tool": "video-shotcraft-draft-verify",
  "version": "1.0.0"
}
```

(The snippet is shortened; the full deterministic output is
`examples/out/broken-mac.json` and is asserted by the tests.)

### Exit codes

| Code | Meaning |
| --- | --- |
| 0 | verified, no error-severity finding (warnings allowed unless `--strict`) |
| 1 | at least one error-severity finding |
| 2 | usage error, missing directory, missing entry file, unreadable/invalid JSON |

## Tests

```bash
python3 -m py_compile bin/video-shotcraft-draft-verify tests/test_cli.py
python3 tests/test_cli.py
```

17 tests, all driving the CLI as a subprocess (input → findings → exit code),
plus golden-output comparison and the Mac/Windows entry-drift case. Last run:
`Ran 17 tests ... OK` in about 0.7 s on Python 3.12.

Fixtures are synthetic minimal drafts modelled on the format; the `.mp4`/`.mp3`
files are placeholders, because the checks are about references, not bytes.

Real-world check (manual, not committed because the draft is third-party): the
populated template in
[notinmood/JianyingDraft.PY `.draftDemo/Normal/draft_content.json`](https://github.com/notinmood/JianyingDraft.PY/blob/main/.draftDemo/Normal/draft_content.json)
(17,817 bytes, 12 materials, 2 tracks, 2 segments, Windows absolute media paths)
returns `rc=0` with 4 warnings: two `J025` uncheckable Windows paths, `J024`
(no meta in that repo), and `J030` fingerprint fields — no false positives on a
draft this tool did not author.

## 与同类项目的差异

- `GuanYixuan/pyCapCut` (753★) **generates** CapCut drafts. This tool never
  generates; it consumes an existing directory and reports violations, so it can
  audit drafts produced by any exporter.
- `capcut-project-exporter` exports segments to MP4; `capcut-srt-exporter`
  extracts subtitles; `Jianying-CapCut2XML` converts formats. None checks
  referential integrity or media registration.
- `video-shotcraft`'s own `smoke_test.py` builds and installs a draft, then asks
  a human to open JianYing. This tool needs no GUI and returns machine-readable
  findings.

## 本轮创新

First offline verifier that implements video-shotcraft's own §6.1 post-install
self-check as code, and extends it from “count tracks and `os.path.exists`” to
cross-file referential integrity: Mac/Windows entry drift, segment→material→
`draft_materials(type 0)` closure, same-track overlap with exact ranges, source
vs material duration, path escape, and fingerprint leakage. The generator
ecosystem (pyCapCut et al.) has no equivalent; the upstream's only acceptance
path is human eyes.

## Limits

- Format knowledge is read from `mac_draft.py` / `draft_content.json`; encrypted
  drafts written by newer JianYing versions are intentionally rejected (invalid
  JSON → exit 2).
- Text materials are not parsed (`content` is an opaque string), so text style
  errors are out of scope.
- Windows absolute paths (`C:\...`) are reported as uncheckable (J025) on POSIX.
- `J021` is a warning by default because Windows non-sandbox installs may
  reference external media; use `--strict` to make it fatal.

## License

MIT. No upstream code is copied; the checks are derived from the documented
format and the upstream doc's acceptance criteria. Upstream is Apache-2.0 licensed.