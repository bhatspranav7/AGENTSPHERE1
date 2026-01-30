from backend.app.agents.planner_agent import PlannerAgent


def main():
    planner = PlannerAgent()
    execution_id, plan = planner.create_plan(
        "Build a FastAPI CRUD API with PostgreSQL"
    )

    print("\n=== EXECUTION APPROVED ===\n")
    print(f"Execution ID: {execution_id}")
    print(plan.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
