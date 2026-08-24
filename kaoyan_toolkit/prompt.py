"""提示词模板：西综考点分析与错题复盘。"""

SUBJECT_ANALYSIS_PROMPT = """你是资深西医综合(306)考研辅导老师。请基于下面这段真题/复习资料，做考点分析。

要求输出（JSON 格式，不要多余文字）：
{{
  "subjects": [
    {{"name": "科目名", "coverage": "该科目在本资料中的占比估计(%)",
     "key_points": ["高频考点1", "高频考点2", "..."],
     "difficulty_hint": "该科目常见难点"}}
  ],
  "overall": "对这段资料的总体点评(50字内)",
  "suggested_priority": ["按优先级排列的复习科目", "..."]
}}

要求：key_points 至少 3 个、最多 8 个；不要输出空字符串；coverage 用数字或 "xx%"。

资料内容：
---
{text}
"""

WRONG_QUESTION_PROMPT = """你是西医综合(306)考研辅导老师。下面是一道做错的题（含选项和解析），请做复盘。

要求输出（JSON 格式，不要多余文字，每个字段都要有实际内容，不要空字符串）：
{{
  "knowledge_point": "本题考察的核心知识点",
  "mistake_reason": "做错的根本原因（知识盲区/审题失误/理解偏差等）",
  "knowledge_map": "该知识点的完整脉络（200字内）",
  "similar_prediction": "同类题可能的出题方向/变形",
  "review_action": "建议的复习动作（具体可执行）"
}}

错题内容：
---
{text}
"""

PLAN_PROMPT = """根据下面的科目优先级和可用时间，生成一份考研复习周计划。

输入信息：
考试日期：{exam_date}
每天可用时长：{daily_hours} 小时
科目优先级：{priority}

要求输出（JSON 格式）：
{{
  "weeks": [
    {{"week": 1, "focus": "本周主攻科目", "daily_plan": ["周一: ...", "周二: ..."],
      "milestone": "本周结束应达到的效果"}}
  ],
  "total_weeks": "总周数",
  "tips": ["效率建议1", "效率建议2"]
}}

输出 JSON，不要多余文字。
"""
