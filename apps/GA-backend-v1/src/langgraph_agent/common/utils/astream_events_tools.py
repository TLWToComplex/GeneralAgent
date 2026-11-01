import json


from src.utils.sensitive_mask import mask_value, mask_sensitive_fields


def json_safe(value):
    try:
        if value is None:
            return None
        if isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            return {str(k): json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [json_safe(v) for v in value]
        return str(value)
    except Exception:
        return str(value)


def extract_todos(value):
    if value is None:
        return None
    if isinstance(value, dict):
        todos_val = value.get("todos")
        if isinstance(todos_val, list):
            return todos_val
    if isinstance(value, list) and all(isinstance(item, dict) for item in value):
        return value
    return None


def extract_stage(value):
    if value is None:
        return None
    if isinstance(value, dict):
        stage_val = value.get("stage")
        if isinstance(stage_val, str) and stage_val:
            return stage_val
    return None


def maybe_todos_line(todos, run_id: str, thread_id: str, last_todos_fingerprint: dict):
    todos = extract_todos(todos)
    if todos is None:
        return None
    safe_todos = json_safe(todos)
    try:
        fingerprint = json.dumps(safe_todos, ensure_ascii=False, sort_keys=True)
    except Exception:
        fingerprint = str(safe_todos)
    if fingerprint == last_todos_fingerprint.get("value"):
        return None
    last_todos_fingerprint["value"] = fingerprint
    payload = {
        "type": "todos",
        "todos": safe_todos,
        "run_id": run_id,
        "thread_id": thread_id,
    }
    return f"2:{json.dumps([payload], ensure_ascii=False)}\n"


def maybe_stage_line(value, run_id: str, thread_id: str, last_stage: dict):
    stage = extract_stage(value)
    if stage is None:
        return None
    if stage == last_stage.get("value"):
        return None
    last_stage["value"] = stage
    payload = {
        "type": "stage",
        "stage": stage,
        "run_id": run_id,
        "thread_id": thread_id,
    }
    return f"2:{json.dumps([payload], ensure_ascii=False)}\n"


async def process_event(event, thread_id: str, node_stage_by_name: dict = None, last_todos_fingerprint: dict = None, last_stage: dict = None):
    kind = event["event"]
    run_id = event.get("run_id") or ""

    if kind == "on_chat_model_stream":
        chunk = event["data"]["chunk"]
        # 方式 A：直接通过属性获取（取决于 langchain-deepseek 版本）
        reasoning_piece = getattr(chunk, "reasoning_content", None)

        # 方式 B：通过 additional_kwargs 获取（最通用）
        if not reasoning_piece:
            reasoning_piece = chunk.additional_kwargs.get("reasoning_content")

        # 如果有思考内容，单独用标签 1: 输出
        if reasoning_piece:
            if isinstance(reasoning_piece, str) and reasoning_piece.strip():
                yield f"1:{json.dumps(mask_value(reasoning_piece), ensure_ascii=False)}\n"
            elif isinstance(reasoning_piece, list) and reasoning_piece:
                for part in reasoning_piece:
                    if isinstance(part, dict) and part.get("type") == "text" and part.get('text', '').strip():
                        yield f"1:{json.dumps(mask_value(part.get('text', '')), ensure_ascii=False)}\n"

        # 正常内容用标签 0: 输出
        if hasattr(chunk, "content"):
            content = chunk.content
            if content:
                if isinstance(content, str) and content:
                    yield f"0:{json.dumps(content, ensure_ascii=False)}\n"
                elif isinstance(content, list) and content:
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            yield f"0:{json.dumps(part.get('text', ''), ensure_ascii=False)}\n"
    
    elif kind == "on_node_start":
        node_name = event.get("name") or event.get("data", {}).get("name")
        if node_name:
            if node_stage_by_name:
                stage = node_stage_by_name.get(node_name)
                if stage and last_stage:
                    stage_line = maybe_stage_line({"stage": stage}, run_id, thread_id, last_stage)
                    if stage_line:
                        yield stage_line
            
            state_update = {
                "type": "state_update",
                "node": node_name,
                "stage": f"node_{node_name}_start",
                "thread_id": thread_id
            }
            yield f"2:{json.dumps([state_update], ensure_ascii=False)}\n"
    
    elif kind == "on_node_end":
        node_name = event.get("name") or event.get("data", {}).get("name")
        if node_name:
            state_update = {
                "type": "state_update",
                "node": node_name,
                "stage": f"node_{node_name}_end",
                "thread_id": thread_id
            }
            yield f"2:{json.dumps([state_update], ensure_ascii=False)}\n"
    
    elif kind == "on_custom_event":
        event_name = event.get("name", "")
        if event_name == "interrupt":
            custom_data = event.get("data", {})
            interrupt_message = custom_data.get("message", "")
            if interrupt_message:
                interrupt_event = {
                    "type": "interrupt",
                    "message": interrupt_message,
                    "run_id": run_id,
                    "thread_id": thread_id
                }
                yield f"2:{json.dumps([interrupt_event], ensure_ascii=False)}\n"
    
    elif kind == "on_tool_start":
        data = event.get("data", {})
        tool_name = event.get("name") or data.get("name") or data.get("tool_name") or data.get("tool") or ""
        if tool_name and not tool_name.startswith("_"):
            raw_input = data.get("input") or {}
            if isinstance(raw_input, dict):
                raw_input = {k: v for k, v in raw_input.items() if k != "runtime"}
            safe_input = json_safe(raw_input)
            safe_input = mask_sensitive_fields(safe_input)
            tool_info = {
                "type": "tool_start",
                "tool": tool_name,
                "input": safe_input,
                "run_id": event["run_id"],
                "thread_id": thread_id
            }
            yield f"2:{json.dumps([tool_info], ensure_ascii=False)}\n"
            state_update = {
                "type": "state_update",
                "node": "agent",
                "stage": f"tool_{tool_name}_start",
                "last_tool": tool_name,
                "thread_id": thread_id
            }
            yield f"2:{json.dumps([state_update], ensure_ascii=False)}\n"
    
    elif kind == "on_tool_end":
        data = event.get("data", {})
        tool_name = event.get("name") or data.get("name") or data.get("tool_name") or data.get("tool") or ""
        if tool_name and not tool_name.startswith("_"):
            raw_output = data.get("output")
            output_json = None
            output_str = None
            if isinstance(raw_output, (dict, list)):
                output_json = raw_output
                try:
                    output_str = json.dumps(raw_output, ensure_ascii=False)
                except Exception:
                    output_str = str(raw_output)
            elif isinstance(raw_output, str):
                output_str = raw_output
                try:
                    output_json = json.loads(raw_output)
                except Exception:
                    output_json = None
            else:
                output_str = str(raw_output)
            tool_result = {
                "type": "tool_end",
                "tool": tool_name,
                "output": mask_value(output_str or ""),
                "output_json": mask_sensitive_fields(output_json) if output_json else None,
                "run_id": event["run_id"],
                "thread_id": thread_id
            }
            yield f"2:{json.dumps([tool_result], ensure_ascii=False)}\n"
            state_update = {
                "type": "state_update",
                "node": "agent",
                "stage": f"tool_{tool_name}_end",
                "last_tool": tool_name,
                "thread_id": thread_id
            }
            yield f"2:{json.dumps([state_update], ensure_ascii=False)}\n"
            
            if tool_name == "write_todos" and last_todos_fingerprint:
                todos_line = maybe_todos_line(output_json, run_id, thread_id, last_todos_fingerprint)
                if not todos_line:
                    todos_line = maybe_todos_line(data.get("input"), run_id, thread_id, last_todos_fingerprint)
                if todos_line:
                    yield todos_line
    
    elif kind in {"on_chain_start", "on_runnable_start"}:
        name = event.get("name") or event.get("data", {}).get("name") or ""
        stage = node_stage_by_name.get(name)
        if stage:
            stage_line = maybe_stage_line({"stage": stage}, run_id, thread_id, last_stage)
            if stage_line:
                yield stage_line     

    elif kind in {"on_chain_end", "on_agent_end", "on_runnable_end"}:
        data = event.get("data", {})
        if last_todos_fingerprint:
            todos_line = maybe_todos_line(data.get("output"), run_id, thread_id, last_todos_fingerprint)
            if todos_line:
                yield todos_line
        if last_stage:
            stage_line = maybe_stage_line(data.get("output"), run_id, thread_id, last_stage)
            if stage_line:
                yield stage_line

