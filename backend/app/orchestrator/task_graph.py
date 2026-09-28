from dataclasses import dataclass, field

from ..schemas import PlanStep


class GraphError(ValueError):
    pass


@dataclass
class TaskGraph:
    """Directed acyclic graph of plan steps.

    Steps whose dependencies are satisfied run concurrently; `levels` groups
    steps by depth so the UI can lay the DAG out left-to-right.
    """

    steps: dict[int, PlanStep]
    order: list[int] = field(default_factory=list)
    levels: dict[int, int] = field(default_factory=dict)

    @classmethod
    def from_steps(cls, steps: list[PlanStep]) -> "TaskGraph":
        by_id: dict[int, PlanStep] = {}
        for s in steps:
            if s.step_id in by_id:
                raise GraphError(f"Duplicate step_id {s.step_id}")
            by_id[s.step_id] = s

        for s in steps:
            for dep in s.depends_on:
                if dep == s.step_id:
                    raise GraphError(f"Step {s.step_id} depends on itself")
                if dep not in by_id:
                    raise GraphError(f"Step {s.step_id} depends on unknown step {dep}")

        graph = cls(steps=by_id)
        graph.order = graph._topological_order()
        for sid in graph.order:
            deps = by_id[sid].depends_on
            graph.levels[sid] = 1 + max((graph.levels[d] for d in deps), default=-1)
        return graph

    def _topological_order(self) -> list[int]:
        # Kahn's algorithm; leftover nodes mean a cycle
        indegree = {sid: len(set(s.depends_on)) for sid, s in self.steps.items()}
        children: dict[int, list[int]] = {sid: [] for sid in self.steps}
        for sid, s in self.steps.items():
            for dep in set(s.depends_on):
                children[dep].append(sid)

        ready = sorted(sid for sid, n in indegree.items() if n == 0)
        order = []
        while ready:
            sid = ready.pop(0)
            order.append(sid)
            for child in children[sid]:
                indegree[child] -= 1
                if indegree[child] == 0:
                    ready.append(child)
            ready.sort()

        if len(order) != len(self.steps):
            cyclic = sorted(set(self.steps) - set(order))
            raise GraphError(f"Dependency cycle between steps {cyclic}")
        return order

    def ready(self, done: set[int], started: set[int]) -> list[int]:
        return [
            sid for sid in self.order
            if sid not in started and all(d in done for d in self.steps[sid].depends_on)
        ]

    def to_dict(self) -> dict:
        return {
            "nodes": [
                {**self.steps[sid].model_dump(), "level": self.levels[sid]}
                for sid in self.order
            ],
            "depth": max(self.levels.values(), default=0) + 1,
        }
