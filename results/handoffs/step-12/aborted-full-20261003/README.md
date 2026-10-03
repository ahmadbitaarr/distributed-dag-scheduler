# Aborted full-matrix attempt: 2026-10-03 (not a benchmark result)

- **Driver commit:** f7860f3. **Backend:** Compose (each service capped at 1 CPU / 512 MiB).
- **Outcome:** run `c1-w1-r1` was **censored** (22 of 24 measured jobs finished within the 120 s measured-phase timeout). The operator then stopped the matrix by hand during `c1-w1-r2`. No later run was recorded.

## Diagnosis

The job times are bimodal:

- The first 13 jobs took about 1.5–1.7 s each.
- After that, jobs took 10–20 s. Single 100 ms tasks took 3.5–8.2 s to execute, and scheduling waits reached 10 s.

The scheduler and the worker slowed down together. The censored job's history is complete and consistent: task F was RUNNING when the budget expired, and the next job had not yet been submitted. So no event or completion was lost.

During the following run, the host showed this:

| Measurement | Value |
|---|---|
| Free physical memory | **711 MB of 16 GB** |
| Windows "Memory Compression" | about 2 GB |
| Host CPU load | 47% |
| Containers | 50–80 MiB and under 15% CPU each |

Under that memory pressure, Windows pages out the Docker VM, which explains the stalls that hit every service at once. The Docker Desktop engine also crashed twice during this session.

The attempt was stopped because its timings would describe host memory pressure rather than the scheduler. It is kept here, unmodified, as a censored or aborted record. It is **not** used in the reported results and is **not** replaced by invented samples. The complete matrix is re-run in a new output directory after host memory is freed.

The smoke check `../smoke-2/` (c1-w1 and c16-w4, one repetition each, 24/24 jobs, correct outputs) ran before the pressure built up. `../smoke-1-docker-crash/` records a smoke attempt that failed because the Docker engine had crashed. The driver recorded it as an error run.
