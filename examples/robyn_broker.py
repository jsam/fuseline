from __future__ import annotations
import os
from robyn import Robyn
from fuseline.broker import MemoryBroker, StepReport
from fuseline.storage import PostgresRuntimeStorage
from fuseline.workflow import WorkflowSchema

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://fuseline:fuseline@localhost:5432/fuseline")

store = PostgresRuntimeStorage(DATABASE_URL)
broker = MemoryBroker()
broker._store = store  # use postgres-backed storage

app = Robyn(__file__)

@app.post("/worker/register")
async def register(request):
    workflows = [WorkflowSchema(**wf) for wf in request.json]
    return broker.register_worker(workflows)

@app.post("/workflow/dispatch")
async def dispatch(request):
    wf = WorkflowSchema(**request.json["workflow"])
    return broker.dispatch_workflow(wf, request.json.get("inputs"))

@app.get("/workflow/step")
async def get_step(request):
    wid = request.qs_params.get("worker_id")
    assignment = broker.get_step(wid)
    if assignment is None:
        return {"status_code": 204}
    return assignment.model_dump()

@app.post("/workflow/step")
async def report_step(request):
    wid = request.qs_params.get("worker_id")
    broker.report_step(wid, StepReport(**request.json))
    return ""

if __name__ == "__main__":
    app.start(port=8000)
