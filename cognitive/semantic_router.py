"""
================================================================================
FILE: cognitive/semantic_router.py
ROLE: The Semantic Traffic Cop
================================================================================
Responsible for parsing raw user input, managing the zero-latency JSON intent 
cache, and executing LLM-based command splitting. 

It safely separates complex "and/then" compound sentences into individual tasks, 
and strictly routes them to the correct Skill Controllers. All persistent data 
saving is pushed to background OS threads to protect the main UI loop.
================================================================================
"""


import os
import json
import re
import asyncio

class SemanticRouter:
    def __init__(self, llm_service):
        self.llm = llm_service
        self.intent_cache_file = "intent_cache.json"
        self.intent_cache = {}

    async def initialize(self):
        """Loads the cache in the background to prevent UI stutter on boot."""
        def _load_cache():
            if os.path.exists(self.intent_cache_file):
                try:
                    with open(self.intent_cache_file, 'r') as f:
                        return json.load(f)
                except Exception: pass
            return {}
            
        self.intent_cache = await asyncio.to_thread(_load_cache)

    async def split_commands(self, query):
        """Splits 'and/then' commands into an array of actionable queries."""
        query_l = query.lower()
        if " and " not in query_l and " then " not in query_l:
            return [query]
            
        print("[ System ] Analyzing potential command chain...")
        
        from config.prompts import get_splitter_prompt
        split_prompt = get_splitter_prompt(query)
        
        try:
            raw = await self.llm.generate(split_prompt, agent_role="researcher", routing="groq")
            clean = raw.replace('```json', '').replace('```', '').strip()
            try:
                parsed = json.loads(clean)
            except json.JSONDecodeError:
                parsed = re.findall(r'"([^"]+)"', clean)
            
            if isinstance(parsed, list) and len(parsed) > 0:
                print(f"[ System ] Chain Established: {parsed}")
                return parsed
        except Exception as e:
            print(f"[ Splitter Error ]: {e}. Defaulting to single execution.")
            
        return [query]

    async def route_query(self, query):
        """Determines the correct skill intent using Groq JSON enforcement."""
        query_l = query.lower().strip()
        
        # 1. Zero-latency memory lookup
        if query_l in self.intent_cache:
            return self.intent_cache[query_l]

        from config.prompts import get_router_prompt, AGENT_TOOLS
        prompt = get_router_prompt(query_l)
        
        try:
            response = await self.llm.generate(prompt, agent_role="researcher", routing="groq")
            clean_json = response.replace('```json', '').replace('```', '').strip()
            
            try:
                parsed_data = json.loads(clean_json)
                selected_tool = parsed_data.get("intent", "general_chat").lower()
            except json.JSONDecodeError:
                match = re.search(r'"intent":\s*"([^"]+)"', clean_json, re.IGNORECASE)
                selected_tool = match.group(1).lower() if match else "general_chat"

            valid_tools = [tool["name"] for tool in AGENT_TOOLS]
            
            if selected_tool in valid_tools:
                self.intent_cache[query_l] = selected_tool
                
                # Eject file writing to a background OS thread!
                def _save_cache():
                    try:
                        with open(self.intent_cache_file, 'w') as f:
                            json.dump(self.intent_cache, f, indent=4)
                    except Exception as e: print(f"[ Cache Write Error ]: {e}")
                        
                await asyncio.to_thread(_save_cache)
                return selected_tool
                
            return "general_chat"
            
        except Exception as e:
            print(f"[ Agent Routing Error ]: {e}")
            return "general_chat"