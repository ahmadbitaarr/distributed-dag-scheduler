"""Import the accepted oracles; no Hokea-specific scheduling assertions."""
from tests.integration.test_hokea_smoke import test_service_exchange
from tests.integration.test_functional_workload import test_committed_functional_workload
from tests.faults.test_worker_crash import test_worker_crash_reassignment
