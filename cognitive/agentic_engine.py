"""
================================================================================
FILE: cognitive/agentic_engine.py
ROLE: The RAG & Tool Execution Engine
================================================================================
The heavy-lifting data retrieval hub. 

This engine is triggered when the LLM requires external context. It searches 
local document vectors, extracts Notion/Calendar agendas, parses custom action 
tags (like <TIMER>), and scrapes real-time web data via DuckDuckGo. It 
synthesizes all this context into a final payload for the Brain to speak.
================================================================================
"""


import asyncio
from ddgs import DDGS
from config.prompts import get_general_chat_prompt, get_fallback_chat_prompt

class AgenticEngine:
    def __init__(self, llm_service, vector_db, memory_graph, timer_skill):
        self.llm = llm_service
        self.vector_db = vector_db
        self.memory = memory_graph
        self.timer_skill = timer_skill

    async def process_chat(self, raw_query, conversation_history):
        print("[ System ] Scanning all neural memory layers...")
        loop = asyncio.get_running_loop()
        
        # 1. PARALLEL CONTEXT GATHERING
        doc_task = loop.run_in_executor(None, lambda: self.vector_db.search_documents(raw_query, top_k=2))
        kg_task = loop.run_in_executor(None, lambda: self.memory.retrieve_context(raw_query))
        vec_task = loop.run_in_executor(None, lambda: self.vector_db.search_past_conversations(raw_query))
        
        doc_data, kg_data, vec_data = await asyncio.gather(doc_task, kg_task, vec_task)
        
        context_block = ""
        if doc_data: context_block += f"LOCAL DOCUMENT LIBRARY:\n{doc_data}\n\n"
        if kg_data: context_block += f"PERMANENT FACTUAL KNOWLEDGE:\n{kg_data}\n\n"
        if vec_data: context_block += f"PAST CONVERSATIONAL MEMORIES:\n{vec_data}\n\n"

        transcript = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history])
        if not transcript: transcript = "No prior conversation in this immediate session."

        # 2. FIRST GENERATION PASS
        unified_prompt = get_general_chat_prompt(self, raw_query, context_block, transcript)
        response = await self.llm.generate(unified_prompt, agent_role="butler", routing="groq")
        response_clean = response.strip(' "\'\n')

        # 3. TAG PARSING & RAG EXECUTION
        return await self._handle_tags(response_clean, raw_query)

    async def _handle_tags(self, response_clean, raw_query):
        loop = asyncio.get_running_loop()
        context_block2 = ""
        
        if response_clean.startswith("<TIMER:"):
            try:
                parts = response_clean.replace("<TIMER:", "").replace(">", "").split("|")
                mins = float(parts[0].strip())
                task_name = parts[1].strip() if len(parts) > 1 else "Focus Session"
                return await self.timer_skill.execute_timer_protocol(mins, task_name)
            except Exception as e:
                print(f"[ Engine Error ] Failed to parse timer tag: {e}")
                return await self.timer_skill.execute_timer_protocol(25, "Focus Session")

        elif response_clean.startswith("<STOP_TIMER>"):
            return await self.timer_skill.stop_timer_protocol()

        elif response_clean.startswith("<WEB:"):
            search_intent = response_clean.replace("<WEB:", "").replace(">", "").strip()
            print(f"[ Agentic RAG: Scraping Global Network for '{search_intent}'... ]")
            
            def fast_snippet_search():
                try:
                    with DDGS() as ddgs:
                        results = list(ddgs.text(search_intent, max_results=3))
                        if not results: return "No recent data found."
                        return "\n".join([f"[{r.get('title')}] {r.get('body')}" for r in results])
                except Exception as e: return f"Search engine offline: {e}"

            scraped_data = await loop.run_in_executor(None, fast_snippet_search)
            context_block2 = f"REAL-TIME WEB DATA:\n{scraped_data}\n\n"
            
        elif response_clean.startswith("<AGENDA>"):
            print("[ Agentic RAG: Pulling Active Directives & Calendar... ]")
            def fetch_full_agenda():
                from skills.notion_tool import NotionTool
                from skills.gcalendar_tool import GCalTool
                query_l = raw_query.lower()
                days_ahead = 1 if "tomorrow" in query_l else 0
                span_days = 7 if "coming up" in query_l or "week" in query_l else 1
                day_title = "UPCOMING 7 DAYS" if span_days > 1 else "TOMORROW" if days_ahead == 1 else "TODAY"
                
                tasks = NotionTool().fetch_tasks()
                cal = GCalTool().fetch_agenda(days_ahead=days_ahead, span_days=span_days)
                
                t_str = ", ".join([t.name for t in tasks if t.priority in ["High", "Medium"]]) or "No urgent tasks."
                c_str = ", ".join([f"{e['name']} at {e['time']}" for e in cal]) or "No meetings."
                return f"URGENT TASKS: {t_str}\nCALENDAR ({day_title}): {c_str}"

            agenda_data = await loop.run_in_executor(None, fetch_full_agenda)
            context_block2 = f"USER AGENDA & REMINDERS:\n{agenda_data}\n\n"
            
        else:
            return response_clean

        # 4. SECOND LLM PASS (Only triggers if Web or Agenda RAG was fired)
        enriched_prompt = get_fallback_chat_prompt(self, raw_query, context_block2)
        msg = await self.llm.generate(enriched_prompt, agent_role="butler", routing="groq")
        return msg