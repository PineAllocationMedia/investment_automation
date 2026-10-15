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

## Chromebook / Crostini runtime observations — 2026-10-12 to 2026-10-14

These are **later CEO-provided read-only native observations and attributed
independent-review findings**, not newly executed measurements in this governance
update. The original full native evidence archive is not independently revalidated
here. Keep the 2026-10-11 capacity table above as a dated snapshot; none of its
free-memory/disk values is a permanent allocation guarantee.

| Area | Observed / reported | Qualification and boundary |
|---|---|---|
| Cgroup layout | Hybrid/v1: named `systemd`, and v1 `memory`, `pids`, `cpu,cpuacct` controllers; `0::/` also appears; no cgroup2 mount observed | Membership and controller presence do **not** prove per-worker CPU/RAM/PID limits or full confinement. |
| Systemd user services | `systemctl --user` / mock-only coordinator were exercised; the historical service was later reported `inactive/dead`, `MainPID=0` | Inactivity is not positive proof of complete descendant disappearance or clean SQLite closure. No persistent autonomous Codex executor was certified. |
| /proc trust | A procfs mount was positively attested in a limited native probe; UID 65534 appeared on procfs virtual paths | A narrowly reviewed procfs-owner exception does not generalize to cgroups or other mounts. |
| Process/FD visibility | 27 PID directories visible; 16 FD directories accessible, 11 permission-denied; one FD metadata race reported | Global exclusion of unknown process/SQLite FD holders **not demonstrable** with these permissions. No process inventory is certified. |
| Cgroup mount metadata | Reported `name=systemd` cgroup mount with UID 65534 on intermediate `/sys` paths and group-writable systemd directory | Kernel-backed, non-escapable worker cgroup and full descendant-stop proof **NOT ESTABLISHED**. |
| Termina/LXD candidate | `lxc` and socket accessibility plus visible v1 controller indicators reported in #159–#161 | Offline LXD preparation accepted for review only; native per-job isolation, zero effective swap and independent stop were **NOT QUALIFIED**. |
| Power/session behavior | ChromeOS/Crostini suspension, logout and VM restart affect guest processes; Linux automatic restart after logout is **not established** | Target is best-effort availability with safe reconciliation after Linux returns, **not** guaranteed uninterrupted 24/7 execution. |
| Model/network/credentials | No independently certified worker separation, anti-dangerous-resume barrier or hard $0 model-billing gate | No real unattended Codex worker is authorized. |

**Historical acceptance boundary:** WO164/WO167 durable queue and coordinator
reached offline/device **MOCK-ONLY** acceptance, without real model calls,
GitHub-write execution or production authority. WO171's historical mock-service
clean exit remains `BLOCKED / NOT_CERTIFIED` with retained artifacts; #157
quarantines remain preserved. No automatic cleanup, restart or SQLite reuse is
authorized. Issue sources and scope: [#153](https://github.com/PineAllocationMedia/investment_automation/issues/153),
[#154](https://github.com/PineAllocationMedia/investment_automation/issues/154),
[#159](https://github.com/PineAllocationMedia/investment_automation/issues/159),
[#161](https://github.com/PineAllocationMedia/investment_automation/issues/161),
[#164](https://github.com/PineAllocationMedia/investment_automation/issues/164),
[#167](https://github.com/PineAllocationMedia/investment_automation/issues/167),
[#171](https://github.com/PineAllocationMedia/investment_automation/issues/171).

### Intended host role versus proven authority

The CEO intends the Chromebook to be the **permanent host of PAM's future
development orchestrator**, with best-effort 24/7 availability, autonomous
selection of tasks within a CEO-approved envelope and PR-only delivery. The CEO
also envisions later running the finished PAM product on that device. This is a
**planning objective**, not a performance qualification, deployment approval or
decision that the eventual commercial product can fit this hardware.

Presently the Chromebook hosts **operational V1**. The proposed development
orchestrator, any future V2 shadow, and any finished-product deployment are
**distinct security and authority domains**. Their co-location must not be
assumed safe: V1 noninterference, storage growth, CPU/memory headroom, runtime
availability, customer-data protection, legal/licensing restrictions and any
production authority require separate design, native validation and explicit
CEO approval. V2 remains a challenger; no commercial hosting/deployment is
authorized here.

**#161 CEO clarification (2026-10-14):** the complete 60-second absolute-stop
and numerical acceptance requirements remain in force for that **specific
one-shot synthetic LXD test**, not automatically for future different worker
architectures. Each future worker class still requires its own independently
validated and CEO-approved execution-safety contract; no safety relaxation,
device GO or real worker follows from this clarification. The repeated-unattended
financial spending barrier of #154 remains `NOT_PROVEN`.

### Refresh / evidence discipline

For new assessments record date, collection environment (Penguin/Termina/ChromeOS),
method, exact observation vs interpretation, source/receipt where accessible,
permissions denied and residual unknowns. Prefer one **separately authorized**,
bounded read-only probe only when a decision actually depends on missing native
information; never repeat broad process enumeration or reveal owner/private
paths, credentials or V1 data. Historical measurements are not live capacity
or proof of service/worker safety.

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
