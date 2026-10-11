# PAM Execution Environments

Reference for proportionate technology/resource selection and eventual execution
planning. This document authorizes no installation, spending or deployment.

## Development Mac

The Mac is the primary development and Codex execution environment. Exact hardware
specifications have not been supplied: CPU/architecture/instruction sets, RAM,
GPU/accelerators and storage capacities are **UNKNOWN**. Mac development capabilities
must not automatically be assumed available on the operational Chromebook.

## Chromebook / Linux Crostini

**Measurement date: 2026-10-11.** The CEO supplied these measurements from read-only
commands in the Linux Crostini terminal. They are verified owner-reported values,
not independently measured by Codex. They describe Linux-visible resources, not
necessarily the complete physical device.

| Property | Verified owner-reported value |
|---|---|
| Machine role | Chromebook running Linux Crostini |
| Current PAM role | Operational V1 host |
| Processor | Intel Celeron N3350 @ 1.10 GHz |
| CPU architecture | x86_64 |
| CPU mode | 64-bit |
| Logical CPUs available to Linux | 2 |
| Linux-visible total RAM | 2.7 GiB |
| Linux-visible available RAM at measurement | 2.6 GiB |
| Swap | 0 B |
| Linux filesystem total | 30 GB |
| Linux filesystem used | 4.9 GB |
| Linux filesystem available | 25 GB |
| Linux distribution | Debian GNU/Linux 12 (bookworm) |
| System Python | 3.11.2 |
| Cgroup memory limit | UNKNOWN — not obtained |
| GPU/accelerator availability | UNKNOWN |
| Exact Chromebook model | UNKNOWN |
| Exact ChromeOS version | UNKNOWN |

Only two logical CPUs are established; do not infer more available cores or threads.
The 2.6 GiB available RAM and 25 GB free storage are snapshots, not permanent
resource guarantees. No reported swap means memory-risk assessments must not assume
swap can absorb excess demand. Effective cgroup limits remain UNKNOWN.

## Operational boundaries and runtimes

- V1 remains frozen operational authority. Routine V2 development must not change
  Chromebook production or disturb existing scheduled production activities.
- Later V2 integration requires separately authorized, isolated shadow deployment.
  Shadow deployment grants no investment or production authority. Runtime isolation
  and provenance requirements remain mandatory.
- Chromebook system Python is **3.11.2**. The recent pinned V2 development-validation
  environment uses **CPython 3.12.13**, as recorded in the repository's
  [Python pin](../../.python-version). These are distinct runtime facts; dependency
  compatibility with either version does not establish compatibility with the other.
  This document authorizes no production Python-environment modification.

## Resource-selection principles

Use the verified Chromebook profile as the conservative default when planning
eventual local execution. Prefer efficient Python libraries, streaming/incremental
processing, bounded memory, modest CPU requirements and dependency footprints,
small controlled caches, deterministic/explainable computation and reliable reused
components.

Assess large Hugging Face models, GPU-dependent inference, high-memory processing,
large model weights/caches, heavy native dependencies, continuous compute services,
large databases and unbounded ingestion/archive growth cautiously. Distinguish local
deployment, development-only experimentation and separately authorized external
execution; weight alone is not a categorical technology ban. Include installation,
peak/sustained RAM, no-swap risk, downloads, temporary storage, runtime compatibility,
execution time, maintenance and ongoing cloud/API costs. Preserve approved financial
constraints; no spending exception follows from this reference.

Hardware fit is a planning assessment, not a real benchmark result. Mac success does
not prove Chromebook compatibility. Record compatibility as established for the Mac,
plausible for Chromebook/Linux, requiring separately authorized external compute, or
not established, with evidence and remaining unknowns.

## Refreshing owner-reported measurements

The CEO can run these read-only commands in the Chromebook Linux terminal. Record
the date and Linux-visible scope; leave unreadable/missing values UNKNOWN. Do not
infer GPU availability, ChromeOS version or device model from these commands.

```sh
# CPU fields only; avoid unnecessary device identifiers.
LC_ALL=C lscpu | sed -n '/^Architecture:/p; /^CPU op-mode(s):/p; /^CPU(s):/p; /^Model name:/p'
# RAM and swap snapshot.
free -h
# Root filesystem capacity only, without personal paths or device names.
df -h --output=size,used,avail,pcent /
# Distribution and system Python.
sed -n '/^PRETTY_NAME=/p; /^VERSION_ID=/p' /etc/os-release
python3 --version
# Current process memory limits, where readable (cgroup v2 or v1).
for limit in memory.max memory.high memory.swap.max; do
    group=$(awk -F: '$1 == "0" {print $3}' /proc/self/cgroup)
    file="/sys/fs/cgroup${group}/$limit"
    if [ -r "$file" ]; then
        printf '%s: ' "$limit"
        cat "$file"
    else
        printf '%s: UNKNOWN\n' "$limit"
    fi
done
group=$(awk -F: '$2 ~ /(^|,)memory(,|$)/ {print $3}' /proc/self/cgroup)
file="/sys/fs/cgroup/memory${group}/memory.limit_in_bytes"
if [ -n "$group" ] && [ -r "$file" ]; then
    printf 'memory.limit_in_bytes: '
    cat "$file"
fi
```

A readable value of `max` means no finite limit at that cgroup node, not unlimited
physical RAM; ancestor limits can still constrain it. These commands install nothing,
modify no configuration and require no production-data or credential access. Keep
refreshes free of usernames, hostnames, serial numbers and personal filesystem paths.
