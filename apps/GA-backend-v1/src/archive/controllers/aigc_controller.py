"""
AI-Generated Content controller module.
Manages requests for AI-generated content through various models and services.
"""
import os
import json
import requests
import re
from flask import Response, request, jsonify
from accessors.prompt_accessor import Prompt
from controllers.proxy_controller import ProxyController
from requests.exceptions import RequestException
from typing import Dict, Any, Tuple, List, Union, Optional
from utils.md5_utils import extract_reasoning, remove_reasoning
# 定义常量，解决字符串字面值重复问题
DEVELOPMENT_ENV = 'development'
PRODUCTION_ENV = 'Production'

class AIGCController:
    ENV = os.getenv('FLASK_ENV', DEVELOPMENT_ENV).lower()

    # META_PROMPT for Hello Message
    META_PROMPT_HELLO_MESSAGE = """
        ## 目标
        你是一位擅长根据用户提供的JSON格式的人员信息数据生成个性化问候语的助手。请综合输入所有字段信息，按照上下文逻辑，生成简短、通顺且幽默的问候语。

        ## 输入
        ```json
        ${input_json}
        ```

        ## 风格
        - 语言亲切友好，幽默，富有个性
        - 在必要时可适度运用描述性词汇或修饰语，使整体更加生动

        ## 受众
        - 需要根据提供的人员信息生成个性化问候语的用户

        ## 推理/限制条件
        - JSON中包含的所有字段信息均可参考，但仅需提取相关信息生成问候语
        - 保证输出内容不会泄露敏感隐私信息，符合合规及隐私保护要求
        - 逻辑清晰、表述准确，无与JSON内容冲突的增删改信息
        - 需尊重字段含义，避免曲解、夸大或遗漏

        ## 步骤
        1. 收集与解析：先仔细阅读JSON中的内容，包括字段与描述。
        2. 归纳与组合：对收集到的字段信息进行分类、整理与关键点提取，选择适合用于问候的部分。
        3. 生成草稿问候语：将提取出的信息依照一定的逻辑顺序串联起来，形成基础问候语。
        4. 修饰与润色：对草稿进行语言润色，使其表达亲切、条理清晰。
        5. 最终输出：以合适的格式或口吻呈现最终问候语，注意排版与简洁性。

        ## 输入格式
        - JSON格式

        ## 输出格式
        - 自然语言问候语

        ## 示例

        **示例**
        **输入：**
        ```json
        {
        "AdditionalInfo": {
            "Hobby": "Reading",
            "Skill": "Programming"
        },
        "Code": 301,
        "Company": "某科技公司",
        "CreatedAt": "Sun, 28 Jan 2024 14:52:57 GMT",
        "CreatedBy": "Admin",
        "DateOfBirth": "Wed, 14 Aug 1991 00:00:00 GMT",
        "Guid": "ff94abbe-0cc4-44d8-82b4-64f62b237646",
        "Id": 1,
        "Introduction": "专业方向是智能化指挥，在读3年的研究生",
        "Name": "苏云缨",
        "Sex": 0,
        "Title": "国服第一曹操",
        "UpdatedAt": "Mon, 01 Jul 2024 10:45:18 GMT",
        "UpdatedBy": "Admin"
        }
        ```
        **输出：**
        ```
        嘿，苏云缨，作为国服第一曹操，听说你研究生快毕业了，最近学习什么呢？
        ```

        ## 注意事项
        1. 选择性纳入相关字段，避免遗漏重要信息。
        2. 避免对字段内容进行主观扩展或无根据的推测。
        3. 确保问候语具有搞笑风格，符合JSON数据中的个人特点。
        4. 问候语应简洁明了，避免冗余信息, 最多20个字。
        5. 只输出最终问候语，不要有多余的文字。
    """.strip()

    # META_PROMPT for Example One (mode 'new')
    META_PROMPT_NEW = """
    给定<[任务、目标或现有提示]>，生成详细的系统提示以指导语言模型有效地完成任务。

    # 指南

    - 理解任务：掌握主要目标、要求、约束和预期输出。

    - 最小更改：如果提供了现有提示，则仅在其简单的情况下对其进行改进。对于复杂的提示，请增强清晰度并添加缺失元素，而无需更改原始结构。
    - **结论之前的推理**：鼓励在得出结论之前进行推理步骤。注意！如果用户提供的示例在推理之后发生，请反转顺序！切勿以结论开头！
    - 推理顺序：调出提示和结论部分的推理部分（按名称指定特定字段）。对于每个，确定执行此操作的顺序，以及是否需要反转。
    - 结论、分类或结果应**始终**出现在最后。
    - 示例：如果有帮助，请包含高质量的示例，使用占位符 [括号中] 表示复杂元素。
    - 可能需要包含哪些类型的示例、包含多少示例以及这些示例是否足够复杂，是否需要使用占位符。
    - 清晰简洁：使用清晰、具体的语言。避免不必要的说明或乏味的陈述。
    - 格式化：使用 markdown 功能以提高可读性。除非特别要求，否则请勿使用 ``` 代码块。
    - 保留用户内容：如果输入任务或提示包含大量指南或示例，请完整保留它们，或尽可能保留。如果它们含糊不清，请考虑将其分解为子步骤。保留用户提供的任何详细信息、指南、示例、变量或占位符。
    - 常量：请在提示中包含常量，因为它们不易受到提示注入的影响。例如指南、规则和示例。
    - 输出格式：详细说明最合适的输出格式。这应包括长度和语法（例如短句、段落、JSON 等）
    - 对于输出明确定义或结构化数据（分类、JSON 等）的任务，倾向于输出 JSON。
    - 除非明确要求，否则 JSON 不应包装在代码块（```)中。

    您输出的最终提示应遵循以下结构。不要包含任何其他评论，只输出完成的系统提示。具体来说，不要在提示的开头或结尾包含任何其他消息。（例如没有“---”）

    [描述任务的简洁说明 - 这应该是提示中的第一行，没有部分标题]

    [根据需要提供其他详细信息。]

    [带有标题或项目符号的可选部分，用于详细步骤。]

    # 步骤 [可选]

    [可选：完成任务所需步骤的详细细分]

    # 输出格式

    [具体指出输出的格式，无论是响应长度、结构等JSON、markdown 等]

    # 示例 [可选]

    [可选：1-3 个定义明确的示例，必要时使用占位符。清楚地标记示例的开始和结束位置，以及输入和输出。必要时使用占位符。]
    [如果示例比预期的实际示例短，请使用 () 进行引用，解释实际示例应该更长/更短/不同。并使用占位符！]

    # 注意事项 [可选]

    [可选：边缘情况、详细信息以及调用或重复特定重要注意事项的区域]
    """.strip()

    META_PROMPT_NEW_ENGLISH = """
    Given a task description or existing prompt, produce a detailed system prompt to guide a language model in completing the task effectively.

    # Guidelines

    - Understand the Task: Grasp the main objective, goals, requirements, constraints, and expected output.
    - Minimal Changes: If an existing prompt is provided, improve it only if it's simple. For complex prompts, enhance clarity and add missing elements without altering the original structure.
    - Reasoning Before Conclusions**: Encourage reasoning steps before any conclusions are reached. 
      ATTENTION! If the user provides examples where the reasoning happens afterward, 
      REVERSE the order! NEVER START EXAMPLES WITH CONCLUSIONS!
        - Reasoning Order: Call out reasoning portions of the prompt and conclusion parts (specific fields by name). For each, determine the ORDER in which this is done, and whether it needs to be reversed.
        - Conclusion, classifications, or results should ALWAYS appear last.
    - Examples: Include high-quality examples if helpful, using placeholders [in brackets] for complex elements.
    - What kinds of examples may need to be included, how many, and whether they are complex enough to benefit from placeholders.
    - Clarity and Conciseness: Use clear, specific language. Avoid unnecessary instructions or bland statements.
    - Formatting: Use markdown features for readability. DO NOT USE ``` CODE BLOCKS UNLESS SPECIFICALLY REQUESTED.
    - Preserve User Content: If the input task or prompt includes extensive guidelines or examples, preserve them entirely, or as closely as possible. If they are vague, consider breaking down into sub-steps. Keep any details, guidelines, examples, variables, or placeholders provided by the user.
    - Constants: DO include constants in the prompt, as they are not susceptible to prompt injection. Such as guides, rubrics, and examples.
    - Output Format: Explicitly the most appropriate output format, in detail. This should include length and syntax (e.g. short sentence, paragraph, JSON, etc.)
        - For tasks outputting well-defined or structured data (classification, JSON, etc.) bias toward outputting a JSON.
        - JSON should never be wrapped in code blocks (```) unless explicitly requested.
    - Output Language: respect task description's original language if possible

    The final prompt you output should adhere to the following structure below. Do not include any additional commentary, only output the completed system prompt. SPECIFICALLY, do not include any additional messages at the start or end of the prompt. (e.g. no "---")

    [Concise instruction describing the task - this should be the first line in the prompt, no section header]

    [Additional details as needed.]

    [Optional sections with headings or bullet points for detailed steps.]

    # Steps [optional]

    [optional: a detailed breakdown of the steps necessary to accomplish the task]

    # Output Format

    [Specifically call out how the output should be formatted, be it response length, structure e.g. JSON, markdown, etc]

    # Examples [optional]

    [Optional: 1-3 well-defined examples with placeholders if necessary. Clearly mark where examples start and end, and what the input and output are. User placeholders as necessary.]
    [If the examples are shorter than what a realistic example is expected to be, make a reference with () explaining how real examples should be longer / shorter / different. AND USE PLACEHOLDERS! ]

    # Notes [optional]

    [optional: edge cases, details, and an area to call or repeat out specific important considerations]
    """.strip()

    # META_PROMPT for Example Two (mode 'edit')
    META_PROMPT_EDIT = """
    给定<[当前提示]>和<[更改描述]>，生成详细的系统提示以指导语言模型有效地完成任务。

    您的最终输出将是完整的更正提示。但是，在此之前，在您的回答一开始，请使用 <reasoning> 标签来分析提示并明确确定以下内容：
    <reasoning>
    - 简单更改：（是/否）更改描述是否明确而简单？（如果是，请跳过其余问题。）
    - 推理：（是/否）当前提示是否使用推理、分析或思路链？
    - 识别：（最多 10 个字）如果是，哪一部分使用推理？
    - 结论：（是/否）思路链是否用于确定结论？
    - 顺序：（之前/之后）思路链位于之前还是之后
    - 结构：（是/否）输入提示是否具有明确定义的结构
    - 示例：（是/否）输入提示是否包含少量示例
    - 代表性：（1-5）如果存在，示例的代表性如何？
    - 复杂性：（1-5）输入提示有多复杂？
    - 任务：（1-5）隐含任务有多复杂？
    - 必要性：（）
    - 特异性：（1-5）提示有多详细和具体？（不要与长度混淆）
    - 优先级：（列表）哪 1-3 个类别是最重要的。
    - 结论：（最多 30 个字）根据之前的评估，给出一个非常简洁、必要的描述，说明应该改变什么以及如何改变。这不必严格遵守列出的类别
    </reasoning>

    # 指南

    - 理解任务：掌握主要目标、要求、约束和预期输出。
    - 最小更改：如果提供了现有提示，则仅在其简单的情况下对其进行改进。对于复杂的提示，请增强清晰度并添加缺失元素，而无需更改原始结构。
    - 结论之前的推理**：鼓励在得出结论之前进行推理步骤。注意！如果用户提供的示例在推理之后发生，请反转顺序！切勿以结论开头！
    - 推理顺序：调出提示和结论部分的推理部分（按名称指定特定字段）。对于每个，确定执行此操作的顺序，以及是否需要反转。
    - 结论、分类或结果应始终出现在最后。
    - 示例：如果有帮助，请包含高质量的示例，使用占位符 [括号中] 表示复杂元素。
    - 可能需要包含哪些类型的示例、包含多少示例以及这些示例是否足够复杂，是否需要使用占位符。
    - 清晰简洁：使用清晰、具体的语言。避免不必要的说明或乏味的陈述。
    - 格式化：使用 markdown 功能以提高可读性。除非特别要求，否则请勿使用 ``` 代码块。
    - 保留用户内容：如果输入任务或提示包含大量指南或示例，请完整保留它们，或尽可能保留。如果它们含糊不清，请考虑将其分解为子步骤。保留用户提供的任何详细信息、指南、示例、变量或占位符。
    - 常量：请在提示中包含常量，因为它们不易受到提示注入的影响。例如指南、规则和示例。
    - 输出格式：详细说明最合适的输出格式。这应包括长度和语法（例如短句、段落、JSON、markdown 等）
    - 对于输出明确定义或结构化数据（分类、JSON 等）的任务，倾向于输出 JSON。
    - 除非明确要求，否则 JSON 不应包装在代码块（```）中。

    您输出的最终提示应遵循以下结构。不要包含任何其他评论，只输出完成的系统提示。具体来说，不要在提示的开头或结尾包含任何其他消息。 （例如没有“---”）

    [描述任务的简洁说明 - 这应该是提示中的第一行，没有部分标题]

    [根据需要添加其他详细信息。]

    [带有标题或项目符号的可选部分，用于详细步骤。]

    # 步骤 [可选]

    [可选：完成任务所需步骤的详细细分]

    # 输出格式

    [具体指出输出的格式，无论是响应长度、结构，例如 JSON、markdown 等]

    # 示例 [可选]

    [可选：1-3 个定义明确的示例，必要时带有占位符。清楚地标记示例的开始和结束位置，以及输入和输出是什么。根据需要使用占位符。]
    [如果示例比预期的实际示例短，请使用 () 进行引用，解释实际示例应该更长/更短/不同。并使用占位符！]

    # 注意事项 [可选]

    [可选：边缘情况，细节，以及一个用来调用或重复特定重要考虑因素的区域]
    [注意：您必须从 <reasoning> 部分开始。您生成的下一个标记应该是 <reasoning>]
    """.strip()

    # META_PROMPT for Example Two (mode 'edit')
    META_PROMPT_EDIT_ENGLISH = """
    Given a current prompt and a change description, produce a detailed system prompt to guide a language model in completing the task effectively.

    Your final output will be the full corrected prompt verbatim. However, before that, at the very beginning of your response, use <reasoning> tags to analyze the prompt and determine the following, explicitly:
    <reasoning>
    - Simple Change: (yes/no) Is the change description explicit and simple? (If so, skip the rest of these questions.)
    - Reasoning: (yes/no) Does the current prompt use reasoning, analysis, or chain of thought?
        - Identify: (max 10 words) if so, which section(s) utilize reasoning?
        - Conclusion: (yes/no) is the chain of thought used to determine a conclusion?
        - Ordering: (before/after) is the chain of though located before or after
    - Structure: (yes/no) does the input prompt have a well defined structure
    - Examples: (yes/no) does the input prompt have few-shot examples
        - Representative: (1-5) if present, how representative are the examples?
    - Complexity: (1-5) how complex is the input prompt?
        - Task: (1-5) how complex is the implied task?
        - Necessity: ()
    - Specificity: (1-5) how detailed and specific is the prompt? (not to be confused with length)
    - Prioritization: (list) what 1-3 categories are the MOST important to address.
    - Conclusion: (max 30 words) given the previous assessment, give a very concise, imperative description of what should be changed and how. this does not have to adhere strictly to only the categories listed
    </reasoning>

    # Guidelines

    - Understand the Task: Grasp the main objective, goals, requirements, constraints, and expected output.
    - Minimal Changes: If an existing prompt is provided, improve it only if it's simple. For complex prompts, enhance clarity and add missing elements without altering the original structure.
    - Reasoning Before Conclusions**: Encourage reasoning steps before any conclusions are reached. 
      ATTENTION! If the user provides examples where the reasoning happens afterward, 
      REVERSE the order! NEVER START EXAMPLES WITH CONCLUSIONS!
        - Reasoning Order: Call out reasoning portions of the prompt and conclusion parts (specific fields by name). For each, determine the ORDER in which this is done, and whether it needs to be reversed.
        - Conclusion, classifications, or results should ALWAYS appear last.
    - Examples: Include high-quality examples if helpful, using placeholders [in brackets] for complex elements.
    - What kinds of examples may need to be included, how many, and whether they are complex enough to benefit from placeholders.
    - Clarity and Conciseness: Use clear, specific language. Avoid unnecessary instructions or bland statements.
    - Formatting: Use markdown features for readability. DO NOT USE ``` CODE BLOCKS UNLESS SPECIFICALLY REQUESTED.
    - Preserve User Content: If the input task or prompt includes extensive guidelines or examples, preserve them entirely, or as closely as possible. If they are vague, consider breaking down into sub-steps. Keep any details, guidelines, examples, variables, or placeholders provided by the user.
    - Constants: DO include constants in the prompt, as they are not susceptible to prompt injection. Such as guides, rubrics, and examples.
    - Output Format: Explicitly the most appropriate output format, in detail. This should include length and syntax (e.g. short sentence, paragraph, JSON, etc.)
        - For tasks outputting well-defined or structured data (classification, JSON, etc.) bias toward outputting a JSON.
        - JSON should never be wrapped in code blocks (```) unless explicitly requested.
    - Output Language: respect original change description's language if possible

    The final prompt you output should adhere to the following structure below. Do not include any additional commentary, only output the completed system prompt. SPECIFICALLY, do not include any additional messages at the start or end of the prompt. (e.g. no "---")

    [Concise instruction describing the task - this should be the first line in the prompt, no section header]

    [Additional details as needed.]

    [Optional sections with headings or bullet points for detailed steps.]

    # Steps [optional]

    [optional: a detailed breakdown of the steps necessary to accomplish the task]

    # Output Format

    [Specifically call out how the output should be formatted, be it response length, structure e.g. JSON, markdown, etc]

    # Examples [optional]

    [Optional: 1-3 well-defined examples with placeholders if necessary. Clearly mark where examples start and end, and what the input and output are. User placeholders as necessary.]
    [If the examples are shorter than what a realistic example is expected to be, make a reference with () explaining how real examples should be longer / shorter / different. AND USE PLACEHOLDERS! ]

    # Notes [optional]

    [optional: edge cases, details, and an area to call or repeat out specific important considerations]
    [NOTE: you must start with a <reasoning> section. the immediate next token you produce should be <reasoning>]
    """.strip()

    @staticmethod
    def get_model_max_tokens(model_name: str) -> int:
        """
        根据模型名称获取对应的max_tokens值

        Args:
            model_name (str): 模型名称

        Returns:
            int: 对应模型的max_tokens值
        """
        # 将模型名称转换为小写以便统一比较
        model_lower = model_name.lower() if model_name else ""
        model_mapping = ProxyController.get_model_mapping()

        # 检查模型是否在映射中，如果是则直接使用配置的max_tokens
        if model_name in model_mapping and "max_tokens" in model_mapping[model_name]:
            return model_mapping[model_name]["max_tokens"]

        # 如果没有在映射中找到或没有配置max_tokens，根据模型名称前缀设置默认值
        if "deepseek" in model_lower:
            return 6000
        elif "glm-4-9b" in model_lower:
            return 6000
        elif "glm-4v" in model_lower or "glm-4V" in model_lower:
            return 1024

        return 1024

    @staticmethod
    def llm_api_stream() -> Response:
        kb_chat_url = os.getenv('KB_CHAT_URL', '')
        if AIGCController.ENV == DEVELOPMENT_ENV:
            return AIGCController._generate_stream_public()
        else:
            return AIGCController._generate_stream_private()

    @staticmethod
    def _generate_stream_public() -> Response:
        data = request.json
        model = data.get("model")
        is_knowledge = data.get("is_knowledge")

        if is_knowledge:
            return ProxyController.proxy_kb_chat()

        else:
            model_mapping = ProxyController.get_model_mapping()
            if model in model_mapping and model_mapping[model].get("type") == "LLM":
                model_upper = model.upper()

                data["max_tokens"] = AIGCController.get_model_max_tokens(model)

                if 'GLM' in model_upper:
                    data["temperature"] = 0.1
                    data["top_p"] = 0.2

            return ProxyController.proxy_llm()

    @staticmethod
    def _generate_stream_private() -> Response:
        # kb_chat_url = os.getenv('KB_CHAT_URL', '')
        # data = request.json
        # messages = data.get("messages")
        # model = data.get("model")
        # is_knowledge = data.get("is_knowledge")
        # query = data.get("query")
        # history = data.get("history")
        # kb_name = data.get("kb_name")

        # if is_knowledge:
        #     return ProxyController.proxy_kb_chat()

        # else:
        #     model_mapping = ProxyController.get_model_mapping()
        #     if model in model_mapping and model_mapping[model].get("type") == "LLM":
        #         model_upper = model.upper()

        #         data["max_tokens"] = AIGCController.get_model_max_tokens(model)

        #         if 'GLM' in model_upper:
        #             data["temperature"] = 0.1
        #             data["top_p"] = 0.2
        #     return ProxyController.proxy_llm()
        return AIGCController._generate_stream_public()

    @staticmethod
    def generate_prompt() -> Response:
        """
        API endpoint to generate or edit prompts based on user input.

        Expects JSON input with:
            - text (str): The user's text input.
            - mode (str): Either 'new' for generating a new prompt or 'edit' for editing an existing prompt.

        Returns:
            JSON response with:
                - original_data (str): The original content from the response.
                - reasoning (str): Parsed reasoning content (only for 'edit' mode).
                - prompt (str): The final prompt content.
        """
        data = request.get_json()

        # Validate input
        if not data:
            return jsonify({"error": "Invalid JSON input."}), 400

        text = data.get('text')
        mode = data.get('mode')
        change_description = data.get('change_description', '')  # Optional field for 'edit' mode
        language = data.get('language', 'zh-cn')

        if not text or not mode:
            return jsonify({"error": "Missing 'text' or 'mode' parameter."}), 400

        if mode not in ['new', 'edit']:
            return jsonify({"error": "Invalid 'mode' parameter. Must be 'new' or 'edit'."}), 400

        if language not in ['zh-cn', 'en-us']:
            return jsonify({"error": "Invalid 'language' parameter. Must be 'zh-cn' or 'en-us'."}), 400

        # 获取模型信息
        model_info, error = AIGCController._get_llm_model()
        if error:
            return error

        model, url, api_key, max_tokens = model_info

        try:
            if mode == 'new':
                # Generate prompt using Example One
                content = AIGCController._generate_new_prompt(text, model, language)
                original_data = content
                reasoning = ""  # No reasoning for 'new' mode
                prompt = content
            else:
                # Generate edited prompt using Example Two
                content = AIGCController._generate_edit_prompt(text, model, change_description, language)
                original_data = content

                # Parse the <reasoning>...</reasoning> section
                reasoning_match = extract_reasoning(content)
                if reasoning_match:
                    reasoning = reasoning_match.group(1).strip()
                    # Remove the reasoning part to get the prompt
                    prompt = remove_reasoning(content)
                else:
                    # If no reasoning tag found, return the entire content as prompt
                    reasoning = ""
                    prompt = content

            # Prepare the response
            response_payload = {
                "original_data": original_data,
                "reasoning": reasoning,
                "prompt": prompt
            }

            return jsonify(response_payload), 200

        except Exception as e:
            # Handle other unexpected errors
            return jsonify({"error": "Internal server error.", "message": str(e)}), 500

    @staticmethod
    def _generate_new_prompt(task_or_prompt: str, model: str, language: str) -> str:
        """
        Generates a new prompt based on Example One using direct payload.

        Args:
            task_or_prompt (str): The task description or existing prompt.
            model (str): The model name to use.
            language (str): The language preference ('zh-cn' or 'en-us').

        Returns:
            str: The generated system prompt.
        """
        content = f"<[任务、目标或现有提示]>：\n {task_or_prompt}" if language == 'zh-cn' else f"<[Task, Goal, or Current Prompt]>:\n {task_or_prompt}"

        # 获取模型信息
        model_info, error = AIGCController._get_llm_model()
        if error:
            raise ValueError(error[0].get_json()["error"])

        model, url, api_key, max_tokens = model_info

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": AIGCController.META_PROMPT_NEW if language == 'zh-cn' else AIGCController.META_PROMPT_NEW_ENGLISH
                },
                {
                    "role": "user",
                    "content": content
                }
            ],
            "stream": False,
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }

        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code != 200:
            raise RequestException(f"API Error: {response.status_code} - {response.text}")

        response_json = response.json()

        # Extract the 'content' from the first choice
        if 'choices' in response_json and len(response_json['choices']) > 0:
            return response_json['choices'][0]['message']['content']
        else:
            raise ValueError("Invalid API response structure.")

    @staticmethod
    def _generate_edit_prompt(task_or_prompt: str, model: str, change_description: str, language: str) -> str:
        """
        Generates an edited prompt based on Example Two using direct payload.

        Args:
            task_or_prompt (str): The current prompt to be edited.

        Returns:
            str: The edited system prompt with reasoning.
        """

        if language == 'zh-cn':
            content = f"<[当前提示]>:\n {task_or_prompt} \n\n<[更改描述]>: {change_description}" if change_description else f"<[当前提示]>:\n {task_or_prompt}"
        else:
            content = f"<[Current Prompt]>:\n {task_or_prompt} \n\n<[Change Description]>: {change_description}" if change_description else f"<[Current Prompt]>:\n {task_or_prompt}"

        # 获取模型信息
        model_info, error = AIGCController._get_llm_model()
        if error:
            raise ValueError(error[0].get_json()["error"])

        model, url, api_key, max_tokens = model_info

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": AIGCController.META_PROMPT_EDIT if language == 'zh-cn' else AIGCController.META_PROMPT_EDIT_ENGLISH
                },
                {
                    "role": "user",
                    "content": content
                }
            ],
            "stream": False,
            "max_tokens": max_tokens,
            "temperature": 0.7
        }

        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code != 200:
            raise RequestException(f"API Error: {response.status_code} - {response.text}")

        response_json = response.json()

        # Extract the 'content' from the first choice
        if 'choices' in response_json and len(response_json['choices']) > 0:
            return response_json['choices'][0]['message']['content']
        else:
            raise ValueError("Invalid API response structure.")

    @staticmethod
    def generate_hello_message() -> Response:
        """
        API endpoint to generate personalized hello messages based on person info.

        Expects JSON input with:
            - person_info (dict): JSON structure containing person information
            - person_image (str, optional): Base64 encoded string of user avatar

        Returns:
            JSON response with:
                - message (str): Generated greeting message
        """
        data = request.get_json()

        # Validate input
        if not data:
            return jsonify({"error": "Invalid JSON input."}), 400

        person_info = data.get('person_info')
        person_image = data.get('person_image')  # Optional field

        if not person_info:
            return jsonify({"error": "Missing 'person_info' parameter."}), 400

        # Create prompt by replacing placeholder in template
        prompt = AIGCController.META_PROMPT_HELLO_MESSAGE.replace(
            "${input_json}",
            json.dumps(person_info, ensure_ascii=False, indent=2)
        )

        # 获取模型信息
        model_info, error = AIGCController._get_llm_model()
        if error:
            return error

        model, url, api_key, max_tokens = model_info

        try:
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "stream": False,
                "max_tokens": max_tokens,
                "temperature": 0.7,  # Adjust for creativity in greetings
            }

            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            }

            response = requests.post(url, headers=headers, json=payload)

            if response.status_code != 200:
                raise RequestException(f"API Error: {response.status_code} - {response.text}")

            response_json = response.json()

            # Extract the 'content' from the first choice
            if 'choices' in response_json and len(response_json['choices']) > 0:
                message = response_json['choices'][0]['message']['content'].strip()
                return jsonify({"message": message}), 200
            else:
                raise ValueError("Invalid API response structure.")

        except (RequestException, ValueError) as e:
            # Handle any unexpected errors
            return jsonify({"error": "Internal server error.", "message": str(e)}), 500

    @staticmethod
    def generate_description() -> Response:
        data = request.get_json()

        if not data:
            return jsonify({"error": "Invalid JSON input."}), 400

        input_json = data.get('input_json')
        prompt_code = data.get('prompt_code', 'aw_whysc')

        result, response = Prompt.get_prompt_by_code(prompt_code)

        if not result:
            return jsonify({"error": response}), 404

        prompt = response.get('Content').replace(
            "${input_json}",
            json.dumps(input_json, ensure_ascii=False, indent=2)
        )

        # 获取模型信息
        model_info, error = AIGCController._get_llm_model()
        if error:
            return error

        model, url, api_key, max_tokens = model_info

        try:
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "stream": False,
                "max_tokens": max_tokens,
                "temperature": 0.7,
            }

            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            }

            response = requests.post(url, headers=headers, json=payload)

            if response.status_code != 200:
                raise RequestException(f"API Error: {response.status_code} - {response.text}")

            response_json = response.json()

            if 'choices' in response_json and len(response_json['choices']) > 0:
                message = response_json['choices'][0]['message']['content'].strip()
                return jsonify({"message": message}), 200
            else:
                raise ValueError("Invalid API response structure.")

        except (RequestException, ValueError) as e:
            return jsonify({"error": "Internal server error.", "message": str(e)}), 500

    @staticmethod
    def _get_llm_model(error_msg: str = "未配置模型") -> Tuple[Tuple[str, str, str, int], Optional[Response]]:
        """
        获取LLM模型信息的通用方法，减少代码冗余

        Args:
            error_msg (str): 错误信息，默认为"未配置模型"

        Returns:
            tuple: (model, url, api_key, max_tokens) 或者 (error_response, None)
        """
        model_mapping = ProxyController.get_model_mapping()

        # 筛选出所有类型为LLM的模型
        llm_models = {k: v for k, v in model_mapping.items() if v.get('type') == 'LLM'}

        # 检查是否有可用的LLM模型
        if not llm_models:
            return None, (jsonify({"error": error_msg}), 500)

        # 使用第一个LLM模型
        default_model = list(llm_models.keys())[0]
        model = default_model

        # 使用模型对应的URL、API KEY和max_tokens
        url = llm_models.get(model, {}).get("url")
        api_key = llm_models.get(model, {}).get("api_key")
        max_tokens = llm_models.get(model, {}).get("max_tokens")

        return (model, url, api_key, max_tokens), None

