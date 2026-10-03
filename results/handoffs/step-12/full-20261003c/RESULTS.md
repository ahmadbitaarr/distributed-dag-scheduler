# Benchmark results: `full-20261003c`

- Source revision: `8c5f3cb3c94ed9abdd18c4f178c0ef02e46ab1a3` (dirty tree: False)
- Backend: compose; Docker cpus: 1.0 per service; Docker mem_limit: 512m per service; JVM -Xmx128m (all services)
- Docker: client 27.1.1 server 27.1.1; host VM: Docker Desktop (containerized); 12 CPUs; 3050815488 bytes
- Started 2026-10-03T22:48:19.090699+00:00; finished 2026-10-03T23:25:58.270253+00:00
- Run statuses: {'complete': 45}
- Percentiles: nearest-rank; per-configuration p50/p95 pool the samples of complete runs; job_p95_ms_run_median is the median of per-run p95s

## Per configuration (complete runs only)

| C | W | runs complete/total | job p50 ms | job p95 ms | median of run p95 ms | sched p50 ms | sched p95 ms | throughput mean tasks/s | stdev | min–max |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 5/5 | 1,398 | 1,454 | 1,444 | 5.7 | 450 | 4.20 | 0.02 | 4.17–4.22 |
| 1 | 2 | 5/5 | 1,149 | 1,202 | 1,202 | 4.4 | 228 | 5.09 | 0.06 | 5.00–5.15 |
| 1 | 4 | 5/5 | 961 | 1,027 | 1,027 | 4.9 | 80 | 6.04 | 0.10 | 5.90–6.14 |
| 4 | 1 | 5/5 | 5,435 | 5,543 | 5,530 | 1,107.4 | 2,251 | 4.34 | 0.01 | 4.33–4.34 |
| 4 | 2 | 5/5 | 2,800 | 2,921 | 2,914 | 459.3 | 1,133 | 8.31 | 0.04 | 8.26–8.36 |
| 4 | 4 | 5/5 | 1,488 | 1,570 | 1,548 | 81.5 | 469 | 15.36 | 0.04 | 15.30–15.39 |
| 16 | 1 | 5/5 | 19,561 | 21,889 | 21,889 | 3,934.4 | 9,731 | 4.35 | 0.06 | 4.29–4.42 |
| 16 | 2 | 5/5 | 9,951 | 11,122 | 11,128 | 1,881.0 | 4,785 | 8.56 | 0.03 | 8.53–8.61 |
| 16 | 4 | 5/5 | 5,151 | 5,718 | 5,718 | 834.2 | 2,329 | 16.69 | 0.28 | 16.42–17.12 |

## Where task time goes (complete runs, medians in ms)

| C | W | READY→ASSIGNED | ASSIGNED→RUNNING | RUNNING→SUCCEEDED |
|---|---|---|---|---|
| 1 | 1 | 24.1 | 44.5 | 172.0 |
| 1 | 2 | 4.4 | 24.5 | 173.3 |
| 1 | 4 | 4.9 | 3.9 | 182.0 |
| 4 | 1 | 1,107.6 | 45.3 | 173.4 |
| 4 | 2 | 459.4 | 46.2 | 181.4 |
| 4 | 4 | 81.7 | 46.2 | 188.2 |
| 16 | 1 | 3,941.7 | 45.0 | 173.9 |
| 16 | 2 | 1,889.8 | 45.8 | 175.5 |
| 16 | 4 | 834.5 | 45.9 | 179.2 |

## Every run

| run | status | jobs done | max in flight | tasks/s | job p50 ms | wall s | error |
|---|---|---|---|---|---|---|---|
| c1-w1-r1 | complete | 24 | 1 | 4.17 | 1,401 | 61.4 |  |
| c1-w1-r2 | complete | 24 | 1 | 4.18 | 1,393 | 60.8 |  |
| c1-w1-r3 | complete | 24 | 1 | 4.20 | 1,401 | 60.0 |  |
| c1-w1-r4 | complete | 24 | 1 | 4.21 | 1,392 | 59.8 |  |
| c1-w1-r5 | complete | 24 | 1 | 4.22 | 1,396 | 59.8 |  |
| c1-w2-r1 | complete | 24 | 1 | 5.13 | 1,146 | 55.3 |  |
| c1-w2-r2 | complete | 24 | 1 | 5.07 | 1,149 | 55.5 |  |
| c1-w2-r3 | complete | 24 | 1 | 5.15 | 1,140 | 55.7 |  |
| c1-w2-r4 | complete | 24 | 1 | 5.00 | 1,181 | 55.6 |  |
| c1-w2-r5 | complete | 24 | 1 | 5.09 | 1,147 | 54.9 |  |
| c1-w4-r1 | complete | 24 | 1 | 6.14 | 952 | 54.3 |  |
| c1-w4-r2 | complete | 24 | 1 | 6.05 | 953 | 54.6 |  |
| c1-w4-r3 | complete | 24 | 1 | 6.13 | 943 | 55.1 |  |
| c1-w4-r4 | complete | 24 | 1 | 5.90 | 976 | 57.8 |  |
| c1-w4-r5 | complete | 24 | 1 | 5.97 | 973 | 56.6 |  |
| c4-w1-r1 | complete | 24 | 4 | 4.34 | 5,430 | 59.4 |  |
| c4-w1-r2 | complete | 24 | 4 | 4.34 | 5,434 | 59.2 |  |
| c4-w1-r3 | complete | 24 | 4 | 4.33 | 5,440 | 59.0 |  |
| c4-w1-r4 | complete | 24 | 4 | 4.33 | 5,456 | 59.4 |  |
| c4-w1-r5 | complete | 24 | 4 | 4.34 | 5,428 | 59.7 |  |
| c4-w2-r1 | complete | 24 | 4 | 8.34 | 2,811 | 43.2 |  |
| c4-w2-r2 | complete | 24 | 4 | 8.26 | 2,799 | 44.4 |  |
| c4-w2-r3 | complete | 24 | 4 | 8.33 | 2,791 | 43.1 |  |
| c4-w2-r4 | complete | 24 | 4 | 8.36 | 2,781 | 43.3 |  |
| c4-w2-r5 | complete | 24 | 4 | 8.27 | 2,821 | 43.9 |  |
| c4-w4-r1 | complete | 24 | 4 | 15.39 | 1,477 | 39.5 |  |
| c4-w4-r2 | complete | 24 | 4 | 15.30 | 1,483 | 39.5 |  |
| c4-w4-r3 | complete | 24 | 4 | 15.35 | 1,495 | 40.3 |  |
| c4-w4-r4 | complete | 24 | 4 | 15.37 | 1,474 | 39.5 |  |
| c4-w4-r5 | complete | 24 | 4 | 15.39 | 1,491 | 40.7 |  |
| c16-w1-r1 | complete | 24 | 16 | 4.29 | 19,714 | 59.8 |  |
| c16-w1-r2 | complete | 24 | 16 | 4.31 | 19,652 | 59.9 |  |
| c16-w1-r3 | complete | 24 | 16 | 4.32 | 19,628 | 59.9 |  |
| c16-w1-r4 | complete | 24 | 16 | 4.40 | 19,156 | 59.4 |  |
| c16-w1-r5 | complete | 24 | 16 | 4.42 | 19,194 | 57.9 |  |
| c16-w2-r1 | complete | 24 | 16 | 8.61 | 9,835 | 41.6 |  |
| c16-w2-r2 | complete | 24 | 16 | 8.53 | 9,878 | 42.0 |  |
| c16-w2-r3 | complete | 24 | 16 | 8.55 | 9,951 | 41.3 |  |
| c16-w2-r4 | complete | 24 | 16 | 8.55 | 9,882 | 41.3 |  |
| c16-w2-r5 | complete | 24 | 16 | 8.56 | 9,898 | 41.2 |  |
| c16-w4-r1 | complete | 24 | 16 | 16.61 | 5,161 | 36.0 |  |
| c16-w4-r2 | complete | 24 | 16 | 16.49 | 5,244 | 36.3 |  |
| c16-w4-r3 | complete | 24 | 16 | 16.42 | 5,204 | 37.0 |  |
| c16-w4-r4 | complete | 24 | 16 | 17.12 | 4,986 | 35.9 |  |
| c16-w4-r5 | complete | 24 | 16 | 16.82 | 5,051 | 35.3 |  |
