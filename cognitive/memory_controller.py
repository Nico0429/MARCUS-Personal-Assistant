import json
import re
import asyncio
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
import networkx as nx
from networkx.algorithms import community

from event_engine import bus
from voice import say, global_face

class MemoryController:
    def __init__(self, memory_graph, vector_db, llm_service, interrupt_event):
        self.memory = memory_graph
        self.vector_db = vector_db
        self.llm = llm_service
        self.interrupt_event = interrupt_event

    async def consolidate_memory(self, transcript):
        """Background task: Reads the short-term buffer and extracts permanent facts."""
        print("[ Initiating Background Memory Consolidation... ]")
        
        prompt = (
            f"Review this recent conversation transcript:\n"
            f"-------------------\n{transcript}\n-------------------\n"
            f"Extract permanent, highly relevant knowledge to build the User's personal graph. Focus ONLY on three categories:\n"
            f"1. PERSONAL & NETWORK: The User's family, relationships, locations, and core preferences.\n"
            f"2. PROJECTS & ACADEMICS: The User's university modules, tech stacks, or project architectures (e.g., [\"Honours Project\", \"uses\", \"YOLOv9\"]).\n"
            f"3. SYSTEM DIRECTIVES: Explicit rules the user gives you about how to behave or format responses (e.g., [\"Marcus\", \"must address user as\", \"Sir\"]).\n\n"
            f"DO NOT extract general world trivia, random internet facts, or casual conversational filler.\n"
            f"If there is no data fitting those three categories, return an empty array: []\n"
            f"Otherwise, return STRICTLY a JSON array of lists. Example: [[\"User\", \"studies\", \"Multivariate Math\"], [\"Marcus\", \"response style\", \"Concise\"]]\n"
            f"CRITICAL RULE: Output ONLY the raw JSON array."
        )
        
        raw_extraction = await self.llm.generate(prompt, agent_role="researcher", routing="cloud")
        clean_text = raw_extraction.replace('```json', '').replace('```', '').strip()
        
        try:
            triples_list = json.loads(clean_text)
        except json.JSONDecodeError:
            pattern = r'\[\s*"?\'?([^,\]]+?)"?\'?\s*,\s*"?\'?([^,\]]+?)"?\'?\s*,\s*"?\'?([^,\]]+?)"?\'?\s*\]'
            matches = re.findall(pattern, clean_text)
            triples_list = [[m[0].strip(' "\''), m[1].strip(' "\''), m[2].strip(' "\'')] for m in matches]

        if triples_list and isinstance(triples_list, list) and len(triples_list) > 0:
            if isinstance(triples_list[0], list) and len(triples_list[0]) == 3:
                self.memory.remember(triples_list)
                await bus.emit("refresh_brain_graph", None)
                print(f"[ Consolidation Complete: {len(triples_list)} new neural connections mapped. ]")
        else:
            print("[ Consolidation Complete: No permanent facts detected in recent interaction. ]")

    async def build_ontology(self):
        """Analyzes raw mathematical clusters, invents semantic macro-categories, and restructures the brain."""
        print("\n[ System ] Initiating Semantic Ontology Mapping...")
        try:
            communities = list(community.greedy_modularity_communities(self.memory.graph))
            new_triples = []
            
            for comp in communities:
                if len(comp) > 5:
                    nodes_list = list(comp)
                    prompt = (
                        f"Analyze these related concepts: {nodes_list[:20]}.\n"
                        f"What is the single, broad thematic category that encompasses all of them? \n"
                        f"Reply with ONLY the exact category name. Nothing else."
                    )
                    
                    macro_name = await self.llm.generate(prompt, agent_role="researcher", routing="cloud")
                    macro_name = macro_name.strip(' "\'').title()
                    
                    if macro_name and len(macro_name) < 40:
                        sorted_nodes = sorted(list(comp), key=lambda n: self.memory.graph.degree(n), reverse=True)
                        for sub_hub in sorted_nodes[:4]:
                            if macro_name.lower() != str(sub_hub).lower():
                                new_triples.append([macro_name, "encompasses", sub_hub])
                                
            if new_triples:
                print(f"[ System ] Ontology Engine mapped {len(new_triples)} new hierarchical connections.")
                self.memory.remember(new_triples)
                await bus.emit("refresh_brain_graph", None)
            else:
                print("[ System ] Graph is already optimally structured.")
                
        except Exception as e:
            print(f"[ Ontology Error ]: {e}")

    async def handle_memory_add(self, query_l):
        if "optimize memory" in query_l or "build ontology" in query_l or "structure memory" in query_l:
            print("[ Engaging Ontology Engine... ]")
            msg = "Initiating deep semantic restructuring of the matrix, Sir. This may take a moment."
            await say(msg)
            asyncio.create_task(self.build_ontology())
            return False

        print("[ Building Interconnected Knowledge Graph... ]")
        prompt = (
            f"Extract the factual relationships from this statement: '{query_l}'.\n"
            "Return the data STRICTLY as a valid JSON array of lists. \n"
            "CRITICAL RULES:\n"
            "1. You MUST enclose every single entity and relationship in DOUBLE QUOTES.\n"
            "2. Do NOT link objective facts to the user unless explicitly referenced.\n"
            "3. If the user refers to themselves, ALWAYS use \"User\".\n"
            "4. Output ONLY the raw JSON array. Nothing else."
        )
        
        raw_extraction = await self.llm.generate(prompt, agent_role="researcher", routing="cloud")
        try:
            clean_text = raw_extraction.replace('```json', '').replace('```', '').strip()
            try:
                triples_list = json.loads(clean_text)
            except json.JSONDecodeError:
                pattern = r'\[\s*"?\'?([^,\]]+?)"?\'?\s*,\s*"?\'?([^,\]]+?)"?\'?\s*,\s*"?\'?([^,\]]+?)"?\'?\s*\]'
                matches = re.findall(pattern, clean_text)
                triples_list = [[m[0].strip(' "\''), m[1].strip(' "\''), m[2].strip(' "\'')] for m in matches]

            if triples_list and isinstance(triples_list, list) and len(triples_list[0]) == 3:
                self.memory.remember(triples_list)
                await bus.emit("refresh_brain_graph", None)
                msg = f"Logged to memory, Sir. Extracted {len(triples_list)} neural connections."
            else:
                msg = "Sir, I couldn't clearly parse the relationship to store it."
        except Exception as e:
            print(f"[ Memory Error ]: {e}")
            msg = "Sir, the extraction matrix failed to format correctly."

        print(f"Marcus: {msg}")
        await say(msg)
        return False

    async def handle_memory_prune(self, query_l):
        print("[ Initiating Neural Pruning... ]")
        prompt = (
            f"The user wants to delete a memory based on this command: '{query_l}'.\n"
            "Extract the core subject or entity the user wants to forget. \n"
            "Return ONLY the subject name as a single short string, nothing else."
        )
        target = await self.llm.generate(prompt, agent_role="researcher", routing="cloud")
        target = target.strip(' "\'')
        
        if target:
            removed_count = self.memory.prune_target(target)
            if removed_count > 0:
                await bus.emit("refresh_brain_graph", None)
                msg = f"Done, Sir. I have surgically removed {removed_count} nodes related to '{target}' from my neural matrix."
            else:
                msg = f"Sir, I could not find any active nodes relating to '{target}' in my current matrix."
        else:
            msg = "Sir, I couldn't isolate the specific memory you wanted me to erase."
            
        print(f"Marcus: {msg}")
        await say(msg)
        return False

    