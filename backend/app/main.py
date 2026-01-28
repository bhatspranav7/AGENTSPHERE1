from fastapi import FastAPI
from datetime import datetime

from app.agents.planner_agent import PlannerAgent
from app.agents.research_agent import ResearchAgent
from app.agents.code_agent import CodeAgent
from app.agents.automation_agent import AutomationAgent
from app.agents.supervisor_agent import SupervisorAgent

from app.db.session import SessionLocal
from app.models.agent_log import AgentLog


app = FastAPI(
    title="AgentSphere",
    description="Enterprise-grade Autonomous Multi-Agent Workflow System",
    version="1.1.0"
)

# ---------------- AGENTS ----------------
planner = PlannerAgent()
research_agent = ResearchAgent()
code_agent = CodeAgent()
automation_agent = AutomationAgent()
supervisor = SupervisorAgent()


# ---------------- HEALTH ----------------
@app.get("/")
def health_check():
    return {"status": "AgentSphere backend running 🚀"}


# ---------------- EXECUTION ----------------
@app.post("/execute")
def execute_workflow(request: dict):
    logs = []  # 🔥 ALWAYS present
    db = SessionLocal()

    try:
        query = request.get("query")
        if not query:
            raise ValueError("Query is required")

        # -------- PLAN --------
        plan = planner.plan(query)

        state = {
            "research": None,
            "code": None,
            "automation": None
        }

        # -------- EXECUTE PLAN --------
        for step in plan:
            agent_name = step["agent"]
            attempt = 0

            while True:
                # -------- AGENT EXECUTION --------
                if agent_name == "research_agent":
                    output = research_agent.run(step["input"]["query"])
                    state["research"] = output

                elif agent_name == "code_agent":
                    if not state["research"]:
                        raise ValueError("Research output missing")
                    output = code_agent.run(state["research"]["summary"])
                    state["code"] = output

                elif agent_name == "automation_agent":
                    output = automation_agent.run({
                        "research": state["research"],
                        "code": state["code"]
                    })
                    state["automation"] = output

                else:
                    raise ValueError(f"Unknown agent: {agent_name}")

                # -------- SUPERVISOR DECISION --------
                decision = supervisor.supervise(
                    agent_name=agent_name,
                    output=output,
                    attempt=attempt
                )

                # -------- PERSIST LOG --------
                db_log = AgentLog(
                    agent_name=agent_name,
                    action=step["agent"],
                    status=decision["decision"],
                    attempt=attempt
                )

                db.add(db_log)
                db.commit()
                db.refresh(db_log)

                # -------- RESPONSE LOG --------
                logs.append({
                    "id": db_log.id,
                    "timestamp": db_log.timestamp.isoformat(),
                    "agent": agent_name,
                    "attempt": attempt,
                    "decision": decision["decision"],
                    "output_preview": output
                })

                # -------- SUPERVISOR CONTROL --------
                if decision["decision"] == "APPROVE":
                    break

                if decision["decision"] == "ABORT":
                    return {
                        "status": "FAILED",
                        "result": state,
                        "logs": logs
                    }

                attempt += 1

        # -------- SUCCESS --------
        return {
            "status": "SUCCESS",
            "result": state,
            "logs": logs
        }

    except Exception as e:
        return {
            "status": "ERROR",
            "error": str(e),
            "logs": logs
        }

    finally:
        db.close()
