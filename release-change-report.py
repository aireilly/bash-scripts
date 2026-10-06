#!/usr/bin/env python3
"""Compare release branches and write an HTML change report.

Branches are compared in the order supplied. The first branch is compared
with --base-ref, or with the repository's default branch when that can be
detected. Each later branch is compared with the branch immediately before it.

Example:
    python scripts/release-change-report.py --base-ref 3.3 3.4 3.5

Git reports inserted and deleted lines. Total changed lines is the sum of
insertions and deletions; net line growth is insertions minus deletions. Git
rename detection is enabled, though substantial rewrites might not be matched
as renames. Only .adoc paths are included. Use --exclude to omit generated .adoc files.
"""

import argparse
import html
import math
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path


COLORS = ("#0066cc", "#e68619", "#5e40be", "#238636")


@dataclass
class FileChange:
    """Line and status totals for one changed path."""

    path: str
    old_path: str
    status: str
    added_lines: int
    removed_lines: int

    @property
    def changed_lines(self):
        return self.added_lines + self.removed_lines


@dataclass
class ChangeStats:
    """Change totals for one comparison between two branch snapshots."""

    previous: str
    branch: str
    added_lines: int
    removed_lines: int
    changed_lines: int
    net_lines: int
    new_lines: int
    modified_lines_estimate: int
    total_release_lines: int
    new_files: int
    modified_files: int
    deleted_files: int
    files: list


@dataclass
class CommitSeries:
    """Monthly commits unique to one branch since its comparison point."""

    branch: str
    start_month: str
    monthly_counts: dict
    total_commits: int


def git_output(args, *, check=True):
    """Run Git and return its output as bytes."""
    try:
        result = subprocess.run(
            ["git", *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        raise RuntimeError(f"Unable to run git: {exc}") from exc
    if check and result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(detail or f"git {' '.join(args)} failed")
    return result


def resolve_ref(ref):
    """Resolve a branch or tag name to a commit hash."""
    result = git_output(["rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"], check=False)
    if result.returncode:
        raise RuntimeError(f"Git reference {ref!r} does not resolve to a commit")
    return result.stdout.decode("ascii").strip()


def detect_base_ref():
    """Find the remote default branch or a conventional local default branch."""
    result = git_output(
        ["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"],
        check=False,
    )
    if result.returncode == 0:
        candidate = result.stdout.decode("utf-8", errors="replace").strip()
        if candidate and git_output(
            ["rev-parse", "--verify", "--quiet", f"{candidate}^{{commit}}"],
            check=False,
        ).returncode == 0:
            return candidate
    for candidate in ("main", "master"):
        if git_output(
            ["rev-parse", "--verify", "--quiet", f"{candidate}^{{commit}}"],
            check=False,
        ).returncode == 0:
            return candidate
    return None


def parse_numstat(output):
    """Return line totals by post-image path and the old path for detected renames."""
    fields = output.split(b"\0")
    totals = {}
    renamed_from = {}
    index = 0
    while index < len(fields) and fields[index]:
        columns = fields[index].split(b"\t", 2)
        if len(columns) != 3:
            raise RuntimeError("Could not parse git diff numstat output")
        added, removed, path = columns
        # Git reports '-' for binary files, which have no line counts.
        additions = int(added) if added != b"-" else 0
        deletions = int(removed) if removed != b"-" else 0
        if path:
            totals[path] = (additions, deletions)
            index += 1
            continue
        # With -z, a rename has an empty pathname field followed by old and new paths.
        if index + 2 >= len(fields):
            raise RuntimeError("Could not parse renamed path in git diff numstat output")
        old_path, new_path = fields[index + 1:index + 3]
        totals[new_path] = (additions, deletions)
        renamed_from[new_path] = old_path
        index += 3
    return totals, renamed_from


def parse_raw_status(output):
    """Return status and old-path mappings keyed by post-image path."""
    fields = output.split(b"\0")
    statuses = {}
    index = 0
    while index < len(fields) and fields[index]:
        metadata = fields[index].split()
        if not metadata or index + 1 >= len(fields):
            raise RuntimeError("Could not parse git diff raw output")
        status = metadata[-1].decode("ascii", errors="replace")
        if status.startswith(("R", "C")):
            if index + 2 >= len(fields):
                raise RuntimeError("Could not parse renamed path in git diff raw output")
            old_path, new_path = fields[index + 1:index + 3]
            statuses[new_path] = (status[0], old_path)
            index += 3
        else:
            path = fields[index + 1]
            statuses[path] = (status[0], b"")
            index += 2
    return statuses


def count_adoc_lines(ref):
    """Count text lines in all .adoc files at a release ref."""
    result = git_output(
        ["grep", "--count", "-h", "-I", "-e", "^", ref, "--", ":(glob)**/*.adoc"],
        check=False,
    )
    if result.returncode not in (0, 1):
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(detail or f"Unable to count .adoc lines in {ref!r}")
    try:
        return sum(int(line) for line in result.stdout.splitlines() if line)
    except ValueError as exc:
        raise RuntimeError(f"Could not parse .adoc line totals for {ref!r}") from exc


def compare_refs(previous_name, previous_hash, branch_name, branch_hash, excludes=None):
    """Collect line and file totals for two branch snapshots."""
    pathspecs = ["--", ":(glob)**/*.adoc", *(excludes or [])]
    numstat = git_output(["diff", "--find-renames=50%", "--numstat", "-z", previous_hash, branch_hash, *pathspecs])
    raw_status = git_output(["diff", "--find-renames=50%", "--raw", "-z", previous_hash, branch_hash, *pathspecs])
    line_counts, numstat_renames = parse_numstat(numstat.stdout)
    statuses = parse_raw_status(raw_status.stdout)

    added = sum(counts[0] for counts in line_counts.values())
    removed = sum(counts[1] for counts in line_counts.values())
    modified_estimate = sum(
        min(*line_counts.get(path, (0, 0)))
        for path, (status, _) in statuses.items()
        if status in ("M", "T", "R")
    )
    release_lines = count_adoc_lines(branch_hash)
    files = []
    for path in sorted(set(statuses) | set(line_counts)):
        status, old_path = statuses.get(path, ("M", numstat_renames.get(path, b"")))
        old_path = old_path or numstat_renames.get(path, b"")
        additions, deletions = line_counts.get(path, (0, 0))
        files.append(FileChange(
            path=path.decode("utf-8", errors="replace"),
            old_path=old_path.decode("utf-8", errors="replace"),
            status=status,
            added_lines=additions,
            removed_lines=deletions,
        ))

    return ChangeStats(
        previous=previous_name,
        branch=branch_name,
        added_lines=added,
        removed_lines=removed,
        changed_lines=added + removed,
        net_lines=added - removed,
        new_lines=added - modified_estimate,
        modified_lines_estimate=modified_estimate,
        total_release_lines=release_lines,
        new_files=sum(status[0] == "A" for status, _ in statuses.values()),
        modified_files=sum(status[0] in ("M", "T") for status, _ in statuses.values()),
        deleted_files=sum(status[0] == "D" for status, _ in statuses.values()),
        files=files,
    )


def commit_activity(previous_hash, branch_name, branch_hash):
    """Count branch-exclusive commits by committer month from its merge base."""
    merge_base = git_output(["merge-base", previous_hash, branch_hash]).stdout.decode("ascii").strip()
    merge_base_date = git_output(["show", "-s", "--format=%cs", merge_base]).stdout.decode("ascii").strip()
    if len(merge_base_date) < 7:
        raise RuntimeError(f"Could not determine the start month for {branch_name!r}")

    commits = git_output(["log", "--format=%cs", branch_hash, f"^{previous_hash}"])
    monthly_counts = {}
    for commit_date in commits.stdout.decode("ascii").splitlines():
        if len(commit_date) < 7:
            raise RuntimeError(f"Could not parse a commit date on {branch_name!r}")
        month = commit_date[:7]
        monthly_counts[month] = monthly_counts.get(month, 0) + 1
    return CommitSeries(
        branch=branch_name,
        start_month=min(merge_base_date[:7], min(monthly_counts, default=merge_base_date[:7])),
        monthly_counts=monthly_counts,
        total_commits=sum(monthly_counts.values()),
    )


def _month_keys(start_month, end_month):
    """Return inclusive YYYY-MM month keys."""
    year, month = map(int, start_month.split("-"))
    end_year, end_month_number = map(int, end_month.split("-"))
    months = []
    while (year, month) <= (end_year, end_month_number):
        months.append(f"{year:04d}-{month:02d}")
        month += 1
        if month == 13:
            month = 1
            year += 1
    return months


def commit_timeline_svg(series, as_of=None):
    """Render monthly branch commit counts as a dependency-free SVG line chart."""
    as_of = as_of or date.today()
    current_month = f"{as_of.year:04d}-{as_of.month:02d}"
    start_month = min((row.start_month for row in series), default=current_month)
    months = _month_keys(start_month, current_month)
    if not months:
        months = [current_month]

    ordered_series = list(reversed(series))
    maximum = max(
        (
            row.monthly_counts.get(month, 0)
            for row in ordered_series
            for month in months
            if month >= row.start_month
        ),
        default=0,
    )
    scale_max = max(4, math.ceil(maximum / 4) * 4)
    legend_columns = min(3, max(1, len(ordered_series)))
    legend_rows = math.ceil(len(ordered_series) / legend_columns)
    width = max(960, 180 + len(months) * 34)
    height = 405 + legend_rows * 25
    left, right, top, bottom = 72, 34, 58, 120 + legend_rows * 25
    plot_width = width - left - right
    plot_height = height - top - bottom
    x_position = lambda index: left + plot_width * index / max(1, len(months) - 1)
    parts = [
        '<svg class="chart timeline-chart" width="%d" height="%d" viewBox="0 0 %d %d" role="img" aria-label="%s">'
        % (width, height, width, height, html.escape("Monthly commit volume by release branch", quote=True)),
        f'<text class="chart-title" x="{left}" y="28">Monthly commit volume by release branch</text>',
    ]

    for tick in range(5):
        value = scale_max * tick // 4
        y = top + plot_height * (1 - tick / 4)
        parts.append(f'<line class="grid" x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}"/>')
        parts.append(f'<text class="axis-label" x="{left-10}" y="{y+4:.1f}" text-anchor="end">{value}</text>')

    label_step = max(1, math.ceil(len(months) / 12))
    label_indexes = set(range(0, len(months), label_step))
    label_indexes.add(len(months) - 1)
    for index in sorted(label_indexes):
        x = x_position(index)
        y = top + plot_height + 23
        parts.append(f'<text class="axis-label" transform="translate({x:.1f},{y:.1f}) rotate(-42)" text-anchor="end">{months[index]}</text>')

    legend_items = []
    for series_index, row in enumerate(ordered_series):
        color = COLORS[series_index % len(COLORS)]
        first_index = next((i for i, month in enumerate(months) if month >= row.start_month), len(months))
        points = []
        for index in range(first_index, len(months)):
            month = months[index]
            value = row.monthly_counts.get(month, 0)
            x = x_position(index)
            y = top + plot_height * (1 - value / scale_max)
            points.append((x, y, month, value))
        if points:
            point_list = " ".join(f"{x:.1f},{y:.1f}" for x, y, _, _ in points)
            parts.append(
                f'<polyline points="{point_list}" fill="none" stroke="{color}" '
                'stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>'
            )
            for x, y, month, value in points:
                parts.append(
                    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.3" fill="{color}">'
                    f'<title>{html.escape(row.branch)}: {month}: {value} commits</title></circle>'
                )
        legend_items.append((row.branch, color, row.total_commits))

    legend_start_y = height - 18 - legend_rows * 25
    legend_cell_width = (width - left - right) / legend_columns
    for index, (branch, color, total) in enumerate(legend_items):
        legend_row, legend_column = divmod(index, legend_columns)
        x = left + legend_column * legend_cell_width
        y = legend_start_y + legend_row * 25
        parts.append(f'<line x1="{x:.1f}" y1="{y-4}" x2="{x+18:.1f}" y2="{y-4}" stroke="{color}" stroke-width="3"/>')
        parts.append(
            f'<text class="legend-label" x="{x+25:.1f}" y="{y}">{html.escape(branch)} '
            f'({total:,} commits)</text>'
        )

    parts.append("</svg>")
    return "\n".join(parts)


def chart_svg(title, rows, series):
    """Render a grouped bar chart as an inline, dependency-free SVG."""
    width = max(800, 105 * len(rows) + 170)
    height = 370
    left, right, top, bottom = 66, 28, 54, 105
    plot_width = width - left - right
    plot_height = height - top - bottom
    values = [value for row in rows for _, key, _ in series for value in [getattr(row, key)]]
    maximum = max(values, default=0)
    scale_max = max(1, maximum)
    group_width = plot_width / max(1, len(rows))
    bar_width = min(30, group_width * 0.68 / max(1, len(series)))
    parts = [
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title, quote=True)}">',
        f'<text class="chart-title" x="{left}" y="27">{html.escape(title)}</text>',
    ]

    for tick in range(5):
        value = scale_max * tick / 4
        y = top + plot_height * (1 - tick / 4)
        parts.append(f'<line class="grid" x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}"/>')
        parts.append(f'<text class="axis-label" x="{left-10}" y="{y+4:.1f}" text-anchor="end">{value:.0f}</text>')

    for row_index, row in enumerate(rows):
        center = left + group_width * (row_index + 0.5)
        group_span = bar_width * len(series)
        for series_index, (label, key, color_index) in enumerate(series):
            value = getattr(row, key)
            bar_height = plot_height * value / scale_max
            x = center - group_span / 2 + series_index * bar_width
            y = top + plot_height - bar_height
            safe_title = html.escape(f"{label}: {value}")
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(2, bar_width-2):.1f}" '
                f'height="{bar_height:.1f}" fill="{COLORS[color_index]}"><title>{safe_title}</title></rect>'
            )
        label_y = top + plot_height + 26
        label_x = center - 4
        branch = html.escape(row.branch, quote=True)
        parts.append(
            f'<text class="branch-label" transform="translate({label_x:.1f},{label_y}) rotate(-38)" '
            f'text-anchor="end">{branch}</text>'
        )

    legend_y = height - 12
    legend_width = width / len(series)
    for index, (label, _, color_index) in enumerate(series):
        x = left + index * legend_width
        parts.append(f'<rect x="{x:.1f}" y="{legend_y-12}" width="12" height="12" fill="{COLORS[color_index]}"/>')
        parts.append(f'<text class="legend-label" x="{x+18:.1f}" y="{legend_y-2}">{html.escape(label)}</text>')

    parts.append("</svg>")
    return "\n".join(parts)


def pie_svg(row):
    """Render one line-composition pie for a release."""
    total = row.total_release_lines
    if total <= 0:
        return '<p class="note">No .adoc lines in this release.</p>'

    new_lines = max(0, row.new_lines)
    modified_lines = max(0, row.modified_lines_estimate)
    unchanged_lines = max(0, total - new_lines - modified_lines)
    slices = (
        ("New lines", new_lines, "#0066cc"),
        ("Modified lines (estimate)", modified_lines, "#e68619"),
        ("Unchanged lines", unchanged_lines, "#d8dee4"),
    )
    center_x, center_y, radius = 76, 86, 62
    angle = -math.pi / 2
    elements = [
        '<svg class="pie" viewBox="0 0 380 180" role="img" '
        f'aria-label="Line composition for {html.escape(row.branch, quote=True)}">'
    ]
    for label, value, color in slices:
        if value <= 0:
            continue
        fraction = value / total
        next_angle = angle + 2 * math.pi * fraction
        if fraction >= 0.999999:
            elements.append(
                f'<circle cx="{center_x}" cy="{center_y}" r="{radius}" fill="{color}">'
                f'<title>{html.escape(label)}: {value:,} lines (100%)</title></circle>'
            )
        else:
            start_x = center_x + radius * math.cos(angle)
            start_y = center_y + radius * math.sin(angle)
            end_x = center_x + radius * math.cos(next_angle)
            end_y = center_y + radius * math.sin(next_angle)
            large_arc = 1 if fraction > 0.5 else 0
            elements.append(
                f'<path d="M {center_x} {center_y} L {start_x:.2f} {start_y:.2f} '
                f'A {radius} {radius} 0 {large_arc} 1 {end_x:.2f} {end_y:.2f} Z" '
                f'fill="{color}" stroke="white" stroke-width="1">'
                f'<title>{html.escape(label)}: {value:,} lines ({fraction * 100:.1f}%)</title></path>'
            )
        angle = next_angle

    for index, (label, value, color) in enumerate(slices):
        y = 48 + index * 38
        percent = value / total * 100
        elements.append(f'<rect x="162" y="{y-12}" width="13" height="13" fill="{color}"/>')
        elements.append(
            f'<text class="pie-label" x="183" y="{y}">{html.escape(label)}: '
            f'{value:,} ({percent:.1f}%)</text>'
        )
    elements.append("</svg>")
    return "\n".join(elements)


def _status_label(status):
    return {
        "A": "Added",
        "M": "Modified",
        "T": "Type changed",
        "D": "Deleted",
        "R": "Renamed",
        "C": "Copied",
    }.get(status, status)


def _top_directories(row, limit=12):
    """Aggregate changes by top-level directory."""
    totals = {}
    for change in row.files:
        directory = change.path.split("/", 1)[0] if "/" in change.path else "(repository root)"
        counts = totals.setdefault(directory, {"files": 0, "added": 0, "removed": 0})
        counts["files"] += 1
        counts["added"] += change.added_lines
        counts["removed"] += change.removed_lines
    ranked = sorted(
        totals.items(),
        key=lambda item: (-(item[1]["added"] + item[1]["removed"]), item[0]),
    )
    return ranked[:limit]


def _top_files(row, limit=15):
    """Return the paths with the most inserted and deleted lines."""
    ranked = sorted(
        (change for change in row.files if change.changed_lines),
        key=lambda change: (-change.changed_lines, change.path),
    )
    return ranked[:limit]


def render_report(rows, excludes=None, commit_series=None):
    """Build a self-contained HTML report."""
    as_of = date.today()
    commit_chart = commit_timeline_svg(commit_series or [], as_of)
    line_chart = chart_svg(
        "Lines added and removed by release",
        list(reversed(rows)),
        (("Added lines", "added_lines", 0), ("Removed lines", "removed_lines", 2)),
    )
    file_chart = chart_svg(
        "File changes by release",
        list(reversed(rows)),
        (
            ("New files", "new_files", 0),
            ("Modified files", "modified_files", 1),
            ("Deleted files", "deleted_files", 2),
        ),
    )
    pie_charts = "".join(
        f'<div class="pie-card"><h3>{html.escape(row.branch)} compared with '
        f'{html.escape(row.previous)}</h3>{pie_svg(row)}</div>'
        for row in reversed(rows)
    )
    file_summary_rows = []
    line_summary_rows = []
    for row in reversed(rows):
        file_summary_rows.append(
            "<tr>"
            f"<th scope=\"row\">{html.escape(row.branch)}</th>"
            f"<td>{html.escape(row.previous)}</td>"
            f"<td>{row.new_files:,}</td><td>{row.modified_files:,}</td>"
            f"<td>{row.deleted_files:,}</td>"
            "</tr>"
        )
        line_summary_rows.append(
            "<tr>"
            f"<th scope=\"row\">{html.escape(row.branch)}</th>"
            f"<td>{html.escape(row.previous)}</td>"
            f"<td>{row.added_lines:,}</td><td>{row.removed_lines:,}</td>"
            f"<td>{row.changed_lines:,}</td><td>{row.net_lines:+,}</td>"
            "</tr>"
        )
    contributor_sections = []
    for row in reversed(rows):
        directories = _top_directories(row)
        directory_rows = "".join(
            "<tr>"
            f"<th scope=\"row\">{html.escape(directory)}</th>"
            f"<td>{totals['files']:,}</td><td>{totals['added']:,}</td>"
            f"<td>{totals['removed']:,}</td><td>{totals['added'] + totals['removed']:,}</td>"
            "</tr>"
            for directory, totals in directories
        ) or '<tr><td colspan="5">No changed paths</td></tr>'
        file_rows = []
        for change in _top_files(row):
            shown_path = (
                f"{change.old_path} → {change.path}"
                if change.status == "R" and change.old_path
                else change.path
            )
            file_rows.append(
                "<tr>"
                f"<td>{html.escape(_status_label(change.status))}</td>"
                f"<th scope=\"row\">{html.escape(shown_path)}</th>"
                f"<td>{change.added_lines:,}</td><td>{change.removed_lines:,}</td>"
                f"<td>{change.changed_lines:,}</td>"
                "</tr>"
            )
        file_table_rows = "".join(file_rows) or '<tr><td colspan="5">No text lines changed</td></tr>'
        contributor_sections.append(
            f"<section><h2>{html.escape(row.branch)} compared with {html.escape(row.previous)}</h2>"
            "<h3>Top-level directories by line changes</h3>"
            "<div class=\"table-wrap\"><table><thead><tr><th>Directory</th><th>Changed paths</th>"
            "<th>Added</th><th>Removed</th><th>Lines changed</th></tr></thead>"
            f"<tbody>{directory_rows}</tbody></table></div>"
            "<h3>Top files by line changes</h3>"
            "<div class=\"table-wrap\"><table><thead><tr><th>Status</th><th>File</th>"
            "<th>Added</th><th>Removed</th><th>Lines changed</th></tr></thead>"
            f"<tbody>{file_table_rows}</tbody></table></div></section>"
        )
    scope_note = "Only .adoc paths are included."
    if excludes:
        scope_note += " Additional excluded Git pathspecs: " + ", ".join(excludes) + "."
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Release change report</title>
<style>
body {{ color: #1f2328; font: 16px/1.5 system-ui, sans-serif; margin: 2rem auto; max-width: 1200px; padding: 0 1rem; }}
h1 {{ margin-bottom: .25rem; }}
.note {{ color: #57606a; margin-top: 0; }}
.chart-wrap {{ margin: 1.5rem 0 2rem; overflow-x: auto; }}
.chart {{ display: block; min-width: 800px; width: 100%; }}
.timeline-chart {{ max-width: none; width: auto; }}
.chart-title {{ font-size: 17px; font-weight: 650; }}
.grid {{ stroke: #d8dee4; stroke-width: 1; }}
.axis-label, .branch-label, .legend-label {{ fill: #57606a; font-size: 12px; }}
.pie-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 1rem; }}
.pie-card {{ border: 1px solid #d8dee4; border-radius: 6px; padding: .75rem; }}
.pie-card h3 {{ margin: .25rem 0; }}
.pie {{ display: block; width: 100%; }}
.pie-label {{ fill: #1f2328; font-size: 12px; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border-bottom: 1px solid #d8dee4; padding: .55rem .65rem; text-align: right; white-space: nowrap; }}
thead th {{ background: #f6f8fa; }}
th:first-child, td:nth-child(2) {{ text-align: left; }}
.table-wrap {{ overflow-x: auto; }}
section {{ margin-top: 2.5rem; }}
h2 {{ border-bottom: 1px solid #d8dee4; padding-bottom: .35rem; }}
h3 {{ margin-top: 1.5rem; }}
</style>
</head>
<body>
<h1>Release change report</h1>
<p class="note">Branches are compared in the order supplied. Total lines changed equals inserted plus deleted lines; net growth equals inserted minus deleted lines. A replaced line counts as one insertion and one deletion. Git rename detection uses a 50% similarity threshold. {html.escape(scope_note)}</p>
<h2>File changes by release</h2>
<div class="table-wrap">
<table>
<thead><tr><th scope="col">Release</th><th scope="col">Compared with</th><th scope="col">New files</th><th scope="col">Modified files</th><th scope="col">Deleted files</th></tr></thead>
<tbody>{''.join(file_summary_rows)}</tbody>
</table>
</div>
<div class="chart-wrap">{file_chart}</div>
<h2>Line changes by release</h2>
<div class="chart-wrap">{line_chart}</div>
<div class="table-wrap">
<table>
<thead><tr><th scope="col">Release</th><th scope="col">Compared with</th><th scope="col">Added lines</th><th scope="col">Removed lines</th><th scope="col">Total lines changed</th><th scope="col">Net line growth</th></tr></thead>
<tbody>{''.join(line_summary_rows)}</tbody>
</table>
</div>
<h2>Commit volume over time</h2>
<p class="note">Monthly commit counts include commits reachable from each release branch but not from the preceding comparison reference. Git does not record branch creation dates, so each line starts at the earlier of the merge-base month and the earliest branch-exclusive commit month. The merge base estimates when the histories diverged, though cherry-picked commits can have earlier committer dates. The timeline runs through {as_of.isoformat()}; its current month is partial. Counts include all repository paths.</p>
<div class="chart-wrap">{commit_chart}</div>
{''.join(contributor_sections)}
<h2>New and modified lines as a share of each release</h2>
<p class="note">Each pie uses the total number of .adoc lines in that release as its denominator. New lines are insertions not paired as replacements. Modified lines are estimated by pairing insertions and deletions within a changed file. Unchanged lines are the remaining lines that Git does not report as insertions; this depends on Git's diff matching.</p>
<div class="pie-grid">{pie_charts}</div>
</body>
</html>
"""


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "branches",
        nargs="+",
        metavar="BRANCH",
        help="release branches in chronological order",
    )
    parser.add_argument(
        "--base-ref",
        help="reference to compare with the first branch; defaults to origin/HEAD, main, or master",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("release-change-report.html"),
        help="HTML report path (default: release-change-report.html)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="PATHSPEC",
        help="Git pathspec to exclude from .adoc files; repeat for multiple exclusions",
    )
    args = parser.parse_args(argv)

    base_ref = args.base_ref or detect_base_ref()
    if not base_ref:
        parser.error("could not detect a base branch; specify --base-ref")
    try:
        base_hash = resolve_ref(base_ref)
        branch_hashes = [(name, resolve_ref(name)) for name in args.branches]
        comparisons = []
        commit_series = []
        previous_name, previous_hash = base_ref, base_hash
        for branch_name, branch_hash in branch_hashes:
            comparisons.append(
                compare_refs(previous_name, previous_hash, branch_name, branch_hash, args.exclude)
            )
            commit_series.append(commit_activity(previous_hash, branch_name, branch_hash))
            previous_name, previous_hash = branch_name, branch_hash
        args.output.write_text(
            render_report(comparisons, args.exclude, commit_series),
            encoding="utf-8",
        )
    except (RuntimeError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Report written to {args.output}")
    print("Release\tCompared with\tAdded\tRemoved\tChanged\tNet\tNew files\tModified files\tDeleted files")
    for row in reversed(comparisons):
        print(
            f"{row.branch}\t{row.previous}\t{row.added_lines}\t{row.removed_lines}\t"
            f"{row.changed_lines}\t{row.net_lines:+}\t{row.new_files}\t"
            f"{row.modified_files}\t{row.deleted_files}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
