# Functional workload (architecture §12)

`functional.json` is the five-task DAG:

- A writes 3.
- B adds 4, giving 7.
- C multiplies by 5, giving 15.
- D sums B and C, giving 22.
- E formats the result as `result=22\n`.

B and C are independent branches, D is a join, and E checks that data propagated through the graph. Each fixture operation waits 100 ms.

`expected.json` lists every task's exact output bytes. `job_id` is a placeholder: clients must replace it with a fresh UUID per submission, because a job ID is immutable within a scheduler run.

Run it against a running deployment with the Java client:

```bash
python3 -c 'import json,uuid;m=json.load(open("workloads/functional/functional.json"));m["job_id"]=str(uuid.uuid4());json.dump(m,open("/tmp/f.json","w"))'
java -jar client/target/client-0.2.0.jar submit /tmp/f.json
```

The integration test `test_committed_functional_workload` runs exactly this file.
