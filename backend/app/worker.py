from __future__ import annotations

import argparse
import socket

from .config import get_settings
from .db import SessionLocal, init_business_db
from .fact_service import process_materials_and_facts
from .models import JobStatus, RunStatus
from .review_service import evaluate_review_core
from .service import claim_job
from .workflow import CreditReviewState, build_checkpointer, build_graph, invoke_config

LEASE_SECONDS = 60
RENEW_SECONDS = 20
MAX_ATTEMPTS = 3


class Worker:
    def __init__(self, worker_id: str | None = None, allow_memory_checkpoint: bool = False) -> None:
        self.worker_id = worker_id or f"worker-{socket.gethostname()}"
        settings = get_settings()
        self.allow_memory_checkpoint = allow_memory_checkpoint or settings.allow_memory_checkpoint

    def run_once(self) -> bool:
        with SessionLocal() as db:
            claimed = claim_job(db, self.worker_id)
            if not claimed:
                return False
            task, run = claimed
            material_result = process_materials_and_facts(db, run)
            if material_result.requires_review:
                run.status = RunStatus.WAITING_FACT_REVIEW
                run.stage = "detect_conflicts"
                run.progress_percent = 50
                run.waiting_gate = "FACT_REVIEW"
                run.retryable = False
                task.status = JobStatus.SUCCEEDED
                task.owner = self.worker_id
                db.commit()
                return True
            core_result = evaluate_review_core(db, run)
            # The graph owns stage progression and checkpointing; business snapshots
            # are produced before entering the report-review interrupt.
            checkpointer = build_checkpointer(
                get_settings().checkpoint_db_path,
                allow_memory=self.allow_memory_checkpoint,
            )
            graph = build_graph(checkpointer)
            state: CreditReviewState = {
                "case_id": run.case_id,
                "run_id": run.id,
                "thread_id": run.id,
                "trace_id": run.id,
                "workflow_version": run.workflow_version,
                "rule_pack_version": run.rule_pack_version,
                "policy_pack_version": run.policy_pack_version,
                "policy_index_version": run.policy_index_version,
                "prompt_versions": run.prompt_versions or {},
                "model_profile": run.model_profile or {},
                "stage": run.stage,
                "document_version_ids": run.document_version_ids,
                "snapshot_refs": {},
                "conflict_ids": [],
                "decision_refs": [],
                "retry_count": task.attempt,
                "needs_fact_review": False,
            }
            state["snapshot_refs"] = {
                "fact": core_result.fact_snapshot_id,
                "retrieval": str(core_result.retrieval_payload["snapshot_id"]),
                "tool": str(core_result.tool_payload["snapshot_id"]),
                "rule": str(core_result.rule_payload["snapshot_id"]),
                "risk": str(core_result.risk_payload["snapshot_id"]),
                "report": str(core_result.report_payload["snapshot_id"]),
            }
            try:
                graph.invoke(state, config=invoke_config(run.id))
            except Exception:
                # An interrupt is expected at REPORT_REVIEW in this skeleton. The
                # production worker will classify GraphInterrupt separately.
                run.status = RunStatus.WAITING_REPORT_REVIEW
                run.stage = "render_report"
                run.waiting_gate = "REPORT_REVIEW"
                run.retryable = False
                task.status = JobStatus.SUCCEEDED
                task.owner = self.worker_id
                db.commit()
                return True
            run.status = RunStatus.WAITING_REPORT_REVIEW
            run.stage = "render_report"
            run.waiting_gate = "REPORT_REVIEW"
            task.status = JobStatus.SUCCEEDED
            task.owner = self.worker_id
            db.commit()
            return True

    def run_forever(self, poll_seconds: float = 2.0) -> None:
        import time

        while True:
            if not self.run_once():
                time.sleep(poll_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="CreditGuard AI Worker")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--allow-memory-checkpoint", action="store_true")
    args = parser.parse_args()
    init_business_db()
    worker = Worker(allow_memory_checkpoint=args.allow_memory_checkpoint)
    if args.once:
        worker.run_once()
    else:
        worker.run_forever()


if __name__ == "__main__":
    main()
