# bash-scripts

* `ocp-checkout`: Copy branch path (eg., `aireilly:xref-script`) from github UI and checkout that branch directly from anywhere.
* `ocp-checkout-other`: Copy PR URL, and checkout that PR
* `show-xrefs`: Copy a module and assembly path, calculate the available xref(s) with resolved context and title.
* `ff`: Simple grep utility that presents search returns as clickable files in the cmd window.

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
