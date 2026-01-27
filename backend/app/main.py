from fastapi import FastAPI, HTTPException
from app.agents.planner_agent import PlannerAgent
from app.agents.research_agent import ResearchAgent
from app.agents.code_agent import CodeAgent
from app.agents.automation_agent import AutomationAgent
from app.agents.supervisor_agent import SupervisorAgent

app = FastAPI(
    title="AgentSphere",
    description="Enterprise-grade Autonomous Multi-Agent Workflow System",
    version="1.0.1"
)

planner = PlannerAgent()
research_agent = ResearchAgent()
code_agent = CodeAgent()
automation_agent = AutomationAgent()
supervisor = SupervisorAgent()


@app.get("/")
def health_check():
    return {"status": "AgentSphere backend running 🚀"}


@app.post("/execute")
def execute_workflow(request: dict):
    logs = []  # 🔥 always initialized first

    try:
        query = request.get("query")
        if not query:
            raise ValueError("Query is required")

        plan = planner.plan(query)

        state = {
            "research": None,
            "code": None,
            "automation": None
        }

        for step in plan:
            agent_name = step["agent"]
            attempt = 0

            while True:
                # ---------------- AGENT EXECUTION ----------------
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

                # ---------------- SUPERVISOR DECISION ----------------
                supervisor_log = supervisor.supervise(
                    agent_name=agent_name,
                    output=output,
                    attempt=attempt
                )

                logs.append(supervisor_log)

                if supervisor_log["decision"] == "APPROVE":
                    break

                if supervisor_log["decision"] == "ABORT":
                    return {
                        "status": "FAILED",
                        "result": state,
                        "logs": logs
                    }

                attempt += 1

        # 🔥 SUCCESS PATH ALWAYS RETURNS LOGS
        return {
            "status": "SUCCESS",
            "result": state,
            "logs": logs
        }

    except Exception as e:
        # 🔥 even errors return logs
        return {
            "status": "ERROR",
            "error": str(e),
            "logs": logs
        }
