"""
对话记录采集器。

为四种对话类型（model / deepagent / agent / travel_planner）采集一轮对话，
并**按时序**拆分为多条消息存储：用户问题、模型思考、工具调用、模型回复
交替出现时，按事件实际发生顺序逐条记录，每条消息携带事件时间戳，
按时间排序即可还原一轮对话的真实时序。

每条消息作为独立的一行写入数据库（一行一条消息），避免单条 JSON 列过大。

一轮对话落库后的消息示例（每条一行）::

    {"system": "...", "time": "..."}
    {"user": "...", "display_content": "...", "files": [], "time": "..."}
    {"reasoning": "第一段思考", "time": "..."}
    {"tool_calls": [{"tool_call_id", "tool", "input", "output", "status"}], "time": "..."}
    {"reasoning": "第二段思考", "time": "..."}
    {"tool_calls": [...], "time": "..."}
    {"response": "模型回复", "time": "..."}
    {"todos": [{"content", "status"}], "time": "..."}

两种喂数据入口：
- feed_line()：解析 process_event 产出的标签行（0: 回复 / 1: 思考 / 2: 结构化事件），
  供 deepagent / agent / travel_planner 使用；
- feed_chunk()：直接喂裸 chunk 的 content / reasoning，供 model 类型使用。

分段规则：连续的同类片段（思考或回复）合并为一条消息；一旦类型切换
（如思考 -> 工具、工具 -> 思考）即开启新的一条消息，从而保留时序。

注意：
- 本模块顶层只依赖 stdlib + flask，admin_server / accessor 在落库时懒加载，
  避免 admin_server -> ai_chat_controller -> collector 的循环导入；
- finalize() 幂等，且内部全部 try/except，落库失败绝不影响流式输出。
"""
import json
import logging
import os
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from openai import OpenAI

logger = logging.getLogger(__name__)
LOCAL_TZ = ZoneInfo("Asia/Shanghai")

# 时间戳格式（微秒精度，保证同一轮内不同消息可按字符串/时间排序区分先后）
_TIME_FMT = '%Y-%m-%d %H:%M:%S.%f'

# ---------- 截断兜底常量 ----------
# messages 列为 MySQL JSON 类型：单个 JSON 文档的大小上限受 max_allowed_packet 约束
# （MySQL 8 默认 64MB），容量远大于常规对话内容，理论上无需在 10 万字符处截断。
# 但一次落库会把本轮多条消息拼进同一条 INSERT 报文，若单条消息逼近 64MB 会整体
# 触发 max_allowed_packet。这里约定单条消息序列化后的字节预算 MAX_MESSAGE_BYTES = 20MB：
#   1) 远小于默认 max_allowed_packet，为同轮多条消息的插入报文留足余量；
#   2) 让大模型回复 / 工具输出等正常偏大的内容能完整入库，而不是像旧的 50KB 兜底那样整条丢弃。
# 各字段字符上限按 utf8mb4 最坏 4 字节/字符折算，并预留约 2 成 JSON 结构/转义开销，
# 使单条字符串字段的理论最坏字节数落在字节预算内。accessor 落库兜底使用同一 MAX_MESSAGE_BYTES。
MAX_MESSAGE_BYTES = 1024 * 1024 * 20                    # 单条消息 JSON 序列化后的字节预算
_MAX_BODY_CHARS = MAX_MESSAGE_BYTES * 8 // 10 // 4  # 单份文本在最坏编码下能安全容纳的字符数

MAX_CONTENT_LEN = _MAX_BODY_CHARS                   # 单条回复消息 response 字段
MAX_THINKING_LEN = _MAX_BODY_CHARS                  # 单条思考消息 reasoning 字段
# user 消息会把同一文本同时写入 user 与 display_content 两个字段，故预算减半
MAX_USER_QUESTION_LEN = _MAX_BODY_CHARS // 2
# 一条 tool_calls 消息内含多项工具，input/output 每项各占一份文本预算，故再折半
MAX_TOOL_IO_LEN = _MAX_BODY_CHARS // 2
MAX_TOOL_CALLS = 500          # 单轮工具调用总条数上限

# 消息类型常量
_SEG_REASONING = 'reasoning'
_SEG_RESPONSE = 'response'
_SEG_TOOLS = 'tools'
_SEG_TODOS = 'todos'
_SEG_SYSTEM = 'system'

# 模块级 Flask app 缓存（懒加载，避免循环导入）
_flask_app = None
_flask_app_load_failed = False


def _get_flask_app():
    """懒加载 Flask app 实例（admin_server 中创建并已 db.init_app）。"""
    global _flask_app, _flask_app_load_failed
    if _flask_app is not None:
        return _flask_app
    if _flask_app_load_failed:
        return None
    try:
        from admin_server import app as flask_app
        _flask_app = flask_app
        return _flask_app
    except Exception as e:
        _flask_app_load_failed = True
        logger.warning(f"加载 Flask app 失败，对话记录将无法落库: {e}")
        return None


def extract_system_prompt(messages) -> str:
    """从前端消息列表中提取系统提示词（第一条 role=system 的消息）。"""
    try:
        if not messages:
            return ''
        for msg in messages:
            if not isinstance(msg, dict) or msg.get('role') != 'system':
                continue
            content = msg.get('content', '')
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts = []
                for part in content:
                    if isinstance(part, dict):
                        text = part.get('text') or part.get('content') or ''
                        if isinstance(text, str) and text:
                            parts.append(text)
                if parts:
                    return '\n'.join(parts)
            elif content is not None:
                return str(content)
    except Exception as e:
        logger.debug(f"extract_system_prompt 失败: {e}")
    return ''


# deepagent 对话会把文件路径提示句追加到 user content 末尾，
# 记录对话/生成摘要时需剔除，只保留用户原始输入。
_FILE_INFO_SUFFIX_RE = re.compile(
    r'\n\n上传的文件 .*? 位于 .*? 文件夹中，请在该文件夹下寻找对应文件。\s*$'
)


def extract_last_user_question(messages) -> str:
    """从前端消息列表中提取本轮用户问题（倒序找第一条 role=user 的消息）。

    content 为 str 直接返回；为 list（多模态分块）时拼接其中的文本部分。
    """
    try:
        if not messages:
            return ''
        for msg in reversed(messages):
            if not isinstance(msg, dict) or msg.get('role') != 'user':
                continue
            content = msg.get('content', '')
            if isinstance(content, str):
                return _FILE_INFO_SUFFIX_RE.sub('', content)
            if isinstance(content, list):
                parts = []
                for part in content:
                    if isinstance(part, dict):
                        text = part.get('text') or part.get('content') or ''
                        if isinstance(text, str) and text:
                            parts.append(text)
                if parts:
                    return '\n'.join(parts)
            elif content is not None:
                return str(content)
    except Exception as e:
        logger.debug(f"extract_last_user_question 失败: {e}")
    return ''

def extract_last_user_images(messages) -> list:
    """从前端消息列表中提取本轮用户上传的图片（倒序找第一条 role=user 的消息）。
    """
    try:
        if not messages:
            return []
        for msg in reversed(messages):
            if not isinstance(msg, dict) or msg.get('role') != 'user':
                continue
            images = []
            content = msg.get('content', [])
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict):
                        image_url = part.get('image_url') or {}
                        if image_url:
                            images.append(image_url)
            return images
    except Exception as e:
        logger.debug(f"extract_last_user_images 失败: {e}")
    return []


def _truncate_str(value, max_len: int) -> str:
    """安全截断字符串。"""
    try:
        if value is None:
            return ''
        if not isinstance(value, str):
            value = json.dumps(value, ensure_ascii=False, default=str)
        if len(value) > max_len:
            return value[:max_len] + '...(truncated)'
        return value
    except Exception:
        return str(value)[:max_len]


# 解析 tool_end output 中的 Python repr 格式
_TOOL_OUTPUT_RE = re.compile(r"(\w+)=('(?:[^'\\]|\\.)*')")


def _parse_tool_output(raw_output):
    """解析形如 ``content='...' name='...' tool_call_id='...'`` 的工具输出。

    返回 (clean_output, tool_call_id, status)。
    无法解析时返回 (raw_output, None, success)。
    """
    if not isinstance(raw_output, str) or not raw_output.strip():
        return raw_output, None, 'success'
    matches = _TOOL_OUTPUT_RE.findall(raw_output)
    if not matches:
        return raw_output, None, 'success'
    parsed = {}
    for key, value_str in matches:
        value = value_str[1:-1]  # 去掉外层引号
        value = value.replace("\\'", "'").replace('\\"', '"')
        parsed[key] = value
    clean_output = parsed.get('content', raw_output)
    tool_call_id = parsed.get('tool_call_id', None)
    status = parsed.get('status', 'success')
    return clean_output, tool_call_id, status


def _now_str() -> str:
    return datetime.now(LOCAL_TZ).strftime(_TIME_FMT)


class ChatRecordCollector:
    """单轮流式对话的记录采集器（按时序分段）。

    用法::

        collector = ChatRecordCollector(
            chat_type='deepagent',
            user_id=user_uuid,
            user_name=user_name,
            session_thread_id=thread_id,
            agent_id=agent_uuid,
            user_question=extract_last_user_question(messages),
            llm_config=llm_config
        )

        # 标签行入口（deepagent/agent/travel_planner）
        collector.feed_line(output)

        # 或裸 chunk 入口（model 类型）
        collector.feed_chunk(content=chunk.content, reasoning=reasoning)

        # 流结束时（建议放 finally）
        collector.finalize()
    """

    def __init__(self, chat_type: str, user_id: str = '', user_name: str  = '', session_thread_id: str = '',
                 agent_id: str = '', turn_id: str = '', user_question: str = '', user_images: list = None, llm_config: dict = None):
        self.chat_type = chat_type or ''
        self.user_id = user_id or ''
        self.user_name = user_name or ''
        self.session_thread_id = session_thread_id or ''
        self.agent_id = agent_id or ''
        self.turn_id = turn_id or ''
        self.user_question = user_question or ''
        self.user_images = user_images or []
        self.llm_model = llm_config.get('model', '') if llm_config else ''
        self.llm_api_key = llm_config.get('api_key', '')  if llm_config else ''
        self.llm_base_url = llm_config.get('base_url', '')  if llm_config else ''
        self.system_prompt = ''

        # 时序分段状态
        self._segments = []           # 已完成的分段消息（按时序排列）
        self._open_type = None        # 当前打开的分段类型: reasoning / response / tools / todos / None
        self._cur_text = []           # 当前 reasoning/response 分段的文本累积
        self._cur_tools = []          # 当前 tools 分段的工具调用列表
        self._cur_todos = []          # 当前 todos 分段的 todo 列表
        self._seg_start_time = None   # 当前分段首次产生内容的时间

        # 工具配对索引（整轮有效，跨分段也能补全 output）
        self._pending_by_run = {}     # run_id -> 工具条目
        self._fifo_by_tool = {}       # tool 名 -> 未完成条目队列（run_id 配不上时兜底）
        self._tool_count = 0          # 本轮工具调用总数（用于上限保护）

        self._start_time = datetime.now(LOCAL_TZ)
        self._finalized = False

    # ------------------------------------------------------------------
    # 分段管理
    # ------------------------------------------------------------------
    def _ensure_segment(self, seg_type: str):
        """确保当前打开的分段类型为 seg_type；类型切换时先落盘上一段。"""
        if self._open_type == seg_type:
            return
        self._flush_segment()
        self._open_type = seg_type
        self._seg_start_time = datetime.now(LOCAL_TZ)
        self._cur_text = []
        self._cur_tools = []
        self._cur_todos = []

    def _flush_segment(self):
        """把当前打开的分段落盘为一条时序消息。"""
        if self._open_type is None:
            return
        time_str = (self._seg_start_time.strftime(_TIME_FMT)
                    if self._seg_start_time else _now_str())
        if self._open_type == _SEG_REASONING:
            text = ''.join(self._cur_text)
            if text:
                self._segments.append({
                    'reasoning': _truncate_str(text, MAX_THINKING_LEN),
                    'time': time_str,
                })
        elif self._open_type == _SEG_RESPONSE:
            text = ''.join(self._cur_text)
            if text:
                self._segments.append({
                    'response': _truncate_str(text, MAX_CONTENT_LEN),
                    'kb_citations': self._get_kb_citations() if self.chat_type=="kb_chat" else [],
                    'time': time_str,
                })
        elif self._open_type == _SEG_TOOLS:
            if self._cur_tools:
                self._segments.append({
                    'tool_calls': self._cur_tools,
                    'time': time_str,
                })
        elif self._open_type == _SEG_TODOS:
            if self._cur_todos:
                self._segments.append({
                    'todos': self._cur_todos,
                    'time': time_str,
                })
        self._open_type = None
        self._cur_text = []
        self._cur_tools = []
        self._cur_todos = []

    def _add_text(self, seg_type: str, text: str):
        if not text:
            return
        self._ensure_segment(seg_type)
        self._cur_text.append(text)

    # ------------------------------------------------------------------
    # 数据喂入
    # ------------------------------------------------------------------
    def set_system_prompt(self, text: str):
        """设置本轮系统提示词。"""
        if text:
            self.system_prompt = text

    def set_user_question(self, question: str):
        """补充/覆盖本轮用户问题。"""
        if question:
            self.user_question = question

    def feed_chunk(self, content: str = '', reasoning: str = ''):
        """裸 chunk 入口（model 类型）：按序累积思考与回复。"""
        try:
            if reasoning:
                self._add_text(_SEG_REASONING, reasoning)
            if content:
                self._add_text(_SEG_RESPONSE, content)
        except Exception as e:
            logger.debug(f"feed_chunk 失败: {e}")

    def feed_line(self, line: str):
        """标签行入口（deepagent/agent/travel_planner）：

        - ``0:"文本"`` 累积模型回复
        - ``1:"文本"`` 累积思考内容
        - ``2:[{...}]`` 解析结构化事件，处理 tool_start / tool_end / todos
        """
        try:
            if not line or len(line) < 3 or line[1] != ':':
                return
            tag = line[0]
            payload = line[2:].rstrip('\r\n')

            if tag == '0':
                text = json.loads(payload)
                if isinstance(text, str):
                    self._add_text(_SEG_RESPONSE, text)
            elif tag == '1':
                text = json.loads(payload)
                if isinstance(text, str):
                    self._add_text(_SEG_REASONING, text)
            elif tag == '2':
                events = json.loads(payload)
                if isinstance(events, list):
                    for evt in events:
                        if not isinstance(evt, dict):
                            continue
                        evt_type = evt.get('type')
                        if evt_type == 'tool_start':
                            self._on_tool_start(evt)
                        elif evt_type == 'tool_end':
                            self._on_tool_end(evt)
                        elif evt_type == 'todos':
                            self._on_todos(evt)
        except Exception as e:
            logger.debug(f"feed_line 解析失败（忽略）: {e}")

    # ------------------------------------------------------------------
    # 工具调用配对
    # ------------------------------------------------------------------
    def _on_tool_start(self, evt: dict):
        if self._tool_count >= MAX_TOOL_CALLS:
            return
        self._ensure_segment(_SEG_TOOLS)
        tool_name = evt.get('tool') or ''
        run_id = evt.get('run_id') or ''
        item = {
            'tool_call_id': run_id,
            'tool': tool_name,
            'input': _truncate_str(evt.get('input'), MAX_TOOL_IO_LEN),
            'output': None,
            'status': 'pending',
        }
        self._cur_tools.append(item)
        self._tool_count += 1
        if run_id:
            self._pending_by_run[run_id] = item
        self._fifo_by_tool.setdefault(tool_name, []).append(item)

    def _on_tool_end(self, evt: dict):
        tool_name = evt.get('tool') or ''
        run_id = evt.get('run_id') or ''
        raw_output = _truncate_str(evt.get('output'), MAX_TOOL_IO_LEN)
        clean_output, tool_call_id, status = _parse_tool_output(raw_output)

        item = None
        if run_id:
            item = self._pending_by_run.pop(run_id, None)
        if item is None:
            # run_id 配不上时，按同名工具 FIFO 找第一个未完成的
            for it in self._fifo_by_tool.get(tool_name, []):
                if it.get('output') is None:
                    item = it
                    break
        if item is None:
            # 孤儿 tool_end：无对应 start，单独记一条
            if self._tool_count < MAX_TOOL_CALLS:
                self._ensure_segment(_SEG_TOOLS)
                self._cur_tools.append({
                    'tool_call_id': tool_call_id or '',
                    'tool': tool_name,
                    'input': None,
                    'output': clean_output,
                    'status': status,
                })
                self._tool_count += 1
            return

        # 命中的条目可能位于已落盘的分段中，通过引用原地补全 output
        item['output'] = clean_output
        item['status'] = status
        if tool_call_id:
            item['tool_call_id'] = tool_call_id
        queue = self._fifo_by_tool.get(tool_name)
        if queue and item in queue:
            queue.remove(item)

    def _on_todos(self, evt: dict):
        """处理 todos 事件，生成独立的 todos 消息。"""
        todos = evt.get('todos')
        if not isinstance(todos, list) or not todos:
            return
        self._ensure_segment(_SEG_TODOS)
        self._cur_todos = todos

    # ------------------------------------------------------------------
    # 收尾落库
    # ------------------------------------------------------------------
    def _get_upload_files(self):
        """读取 upload_records.json 中当前 turn_id 对应的文件列表。"""
        if not self.session_thread_id or not self.turn_id:
            return []
        try:
            from src.utils.config_manager import config_manager
            base_dir = config_manager.get_file_container_path()
            json_path = os.path.join(base_dir, str(self.session_thread_id), "upload_records.json")
            if not os.path.exists(json_path):
                return []
            with open(json_path, 'r', encoding='utf-8') as jf:
                records = json.load(jf)
            return records.get(str(self.turn_id), [])
        except Exception:
            return []

    def _get_kb_citations(self):
        """读取 kb_citations.json 中当前 turn_id 对应的检索结果列表。"""
        if not self.session_thread_id or not self.turn_id:
            return []
        try:
            from src.utils.config_manager import config_manager
            base_dir = config_manager.get_file_container_path()
            json_path = os.path.join(base_dir, str(self.session_thread_id), "kb_citations.json")
            if not os.path.exists(json_path):
                return []
            with open(json_path, 'r', encoding='utf-8') as jf:
                records = json.load(jf)
            return records.get(str(self.turn_id), [])
        except Exception:
            return []

    def finalize(self):
        """按时序组装本轮消息列表并落库。幂等，绝不抛异常。"""
        if self._finalized:
            return
        self._finalized = True
        try:
            # 落盘最后一个未关闭的分段
            self._flush_segment()

            messages = []
            if self.system_prompt:
                messages.append({
                    'system': self.system_prompt,
                    'time': (self._start_time - timedelta(seconds=1)).strftime(_TIME_FMT),
                })
            if self.user_question:
                user_text = _truncate_str(self.user_question, MAX_USER_QUESTION_LEN)
                messages.append({
                    'user': user_text,
                    'display_content': user_text,
                    'files': self._get_upload_files(),
                    'images': self.user_images,
                    'time': self._start_time.strftime(_TIME_FMT),
                })
            messages.extend(self._segments)

            # 全空轮次不写库
            if not messages:
                return

            self._persist(messages)

            # 总结会话首个问题并写入摘要表（每个 session 只写一次）
            # self._summarize_first_question()
        except Exception as e:
            logger.warning(f"对话记录 finalize 失败（不影响流式输出）: {e}")

    def _persist(self, messages: list):
        """自带 Flask app context 地写库（流式生成器消费时外层 context 可能已退出）。"""
        try:
            from flask import has_app_context
            if has_app_context():
                self._do_write(messages)
                return
        except Exception as e:
            logger.debug(f"has_app_context 检查失败: {e}")

        flask_app = _get_flask_app()
        if flask_app is None:
            logger.warning("Flask app 不可用，跳过对话记录落库")
            return
        try:
            with flask_app.app_context():
                self._do_write(messages)
        except Exception as e:
            logger.warning(f"对话记录落库失败（不影响流式输出）: {e}")

    def _do_write(self, messages: list):
        try:
            from src.accessors.ai_chat_record_accessor import AIChatRecord
            ok, result = AIChatRecord.insert_messages(
                chat_type=self.chat_type,
                user_id=self.user_id,
                session_thread_id=self.session_thread_id,
                agent_id=self.agent_id,
                turn_id=self.turn_id,
                message_items=messages,
                operator=self.user_name
            )
            if not ok:
                logger.warning(f"对话记录写入失败: {result}")
        except Exception as e:
            logger.warning(f"对话记录写入异常（不影响流式输出）: {e}")

    # ------------------------------------------------------------------
    # 会话摘要
    # ------------------------------------------------------------------
    def summarize_first_question(self):
        """总结会话首个问题并写入摘要表。幂等，绝不抛异常。"""
        if not self.session_thread_id or not self.user_question:
            return
        if not (self.llm_model and self.llm_api_key and self.llm_base_url):
            return

        try:
            from flask import has_app_context
            if has_app_context():
                self._do_summarize()
                return
        except Exception as e:
            logger.debug(f"has_app_context 检查失败: {e}")

        flask_app = _get_flask_app()
        if flask_app is None:
            return
        try:
            with flask_app.app_context():
                self._do_summarize()
        except Exception as e:
            logger.warning(f"会话摘要失败（不影响流式输出）: {e}")

    def _do_summarize(self):
        """在 app context 下执行：查重 -> 大模型总结 -> 写入摘要表。"""
        try:
            from src.accessors.ai_chat_session_summary_accessor import AIChatSessionSummary

            # 已存在摘要：只刷新更新时间/更新人，不重新生成
            exists, _ = AIChatSessionSummary.get_by_session_thread_id(self.session_thread_id)
            if exists:
                ok, result = AIChatSessionSummary.touch_summary(
                    session_thread_id=self.session_thread_id,
                    update_time=self._start_time,
                    operator=self.user_name or 'system',
                )
                if not ok:
                    logger.warning(f"刷新会话摘要更新时间失败: {result}")
                return

            try:
                client = OpenAI(api_key=self.llm_api_key, base_url=self.llm_base_url)
                response = client.chat.completions.create(
                    model=self.llm_model,
                    max_tokens=512,
                    temperature=0.1,
                    messages=[
                        {
                            "role": "system",
                            "content": "你是一个对话摘要助手。请用一句简洁的话概括用户输入的问题或内容，"
                                       "只输出一句话的概括结果，不要带任何标点符号，不要输出任何解释。如果用户输入的内容本身就很简洁，则直接输出去掉标点符号的用户输入的内容即可。",
                        },
                        {"role": "user", "content": self.user_question},
                    ],
                )
                summary = (response.choices[0].message.content or 'no title').strip()
            except Exception as e:
                summary = self.user_question[:50]

            if not summary:
                return

            ok, result = AIChatSessionSummary.insert_summary(
                session_thread_id=self.session_thread_id,
                summary=summary,
                operator=self.user_name or 'system',
            )
            if ok:
                logger.info(f"会话摘要已保存: session={self.session_thread_id}, summary={summary}")
            else:
                logger.warning(f"会话摘要写入失败: {result}")
        except Exception as e:
            logger.warning(f"会话摘要异常（不影响流式输出）: {e}")
