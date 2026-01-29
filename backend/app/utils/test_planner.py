from backend.app.agents.planner_agent import PlannerAgent


def main():
    planner = PlannerAgent()
    plan = planner.create_plan(
        "Build a FastAPI CRUD API with PostgreSQL"
    )

    print("\n=== EXECUTION PLAN ===\n")
    print(plan.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
