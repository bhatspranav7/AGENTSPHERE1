from backend.app.agents.planner_agent import PlannerAgent
from backend.app.services.execution_engine import ExecutionEngine


def main():
    planner = PlannerAgent()
    engine = ExecutionEngine()

    execution_id, plan = planner.create_plan(
        "Build a FastAPI CRUD API with PostgreSQL"
    )

    print("\n=== PLAN APPROVED ===\n")
    print(f"Execution ID: {execution_id}\n")
    print(plan.model_dump_json(indent=2))

    print("\n=== EXECUTING PLAN ===\n")
    engine.run(execution_id, plan)

    print("Execution completed successfully.")


if __name__ == "__main__":
    main()
