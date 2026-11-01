from langchain.agents.middleware import AgentMiddleware

class MarkAllTasksCompleteMiddleware(AgentMiddleware):
    """在 agent 完成后，确保所有任务都标记为完成状态"""
    
    def after_agent(self, state: dict) -> dict:
        todos = state.get("todos", [])
        
        if not isinstance(todos, list) or len(todos) == 0:
            return {}
        
        all_completed = all(
            task.get("status") == "completed" 
            for task in todos
        )
        
        if all_completed:
            return {}
        
        for task in todos:
            if task.get("status") != "completed":
                task["status"] = "completed"
        
        return {"todos": todos}