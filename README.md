# bash-scripts

* `ocp-checkout`: Copy branch path (eg., `aireilly:xref-script`) from github UI and checkout that branch directly from anywhere.
* `ocp-checkout-other`: Copy PR URL, and checkout that PR
* `show-xrefs`: Copy a module and assembly path, calculate the available xref(s) with resolved context and title.
* `ff`: Simple grep utility that presents search returns as clickable files in the cmd window.
* `release-change-report.py`: Compare release branches and generate an HTML report of `.adoc` file and line changes, plus monthly branch-exclusive commit volume.

## Release change report

Run the script from a Git repository that has the release branch refs available. Supply branch names in chronological order; the first branch is compared with `--base-ref`, and each later branch is compared with the preceding branch. If you omit `--base-ref`, the script tries `origin/HEAD`, `main`, then `master`.

```bash
python3 ~/bash-scripts/release-change-report.py --base-ref upstream/stage-3.2 stage-3.3 stage-3.4 stage-3.5 --output release-change-report.html
```

The report includes `.adoc` file counts, added and removed lines, line-composition charts, and a monthly timeline of commits unique to each branch. Commit counts include all repository paths. Use `--exclude PATHSPEC` one or more times to omit matching `.adoc` paths; the HTML output defaults to `release-change-report.html`.

To use `show-xrefs` script, add the following line to `~/.gitconfig`:

```
[ocpd-repo]
    name = <repo-path>
```
Replace `<repo-path>` with (for example): `/home/aireilly/openshift-docs`.

```bash
$ show-xrefs modules/oadp-checking-api-group-versions.adoc

==================================
generated the following xref(s)...
==================================

xref:../backup_and_restore/application_backup_and_restore/oadp-advanced-topics.adoc/backup_and_restore/application_backup_and_restore/oadp-advanced-topics.adoc#oadp-checking-api-group-versions_oadp-advanced-topics[Listing the Kubernetes API group versions on a cluster]
```
