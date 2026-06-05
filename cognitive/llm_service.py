import os
import asyncio

class LLMService:
    def __init__(self, local_model_name, personas):
        self.local_model = local_model_name
        self.agents = personas

    async def generate(self, user_prompt, agent_role="butler", routing="local"):
        """Intelligent routing with strict error catches (No forced local fallbacks)."""
        system_instruction = self.agents.get(agent_role, self.agents.get("butler", ""))
        loop = asyncio.get_running_loop()

        try:
            # ==========================================
            # ROUTE 1: GOOGLE CLOUD (Gemini)
            # ==========================================
            if routing == "cloud":
                try:
                    from google import genai
                    from google.genai import types
                    
                    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
                    response = await loop.run_in_executor(None, lambda: client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=user_prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=0.1,
                        ),
                    ))
                    return response.text.strip()
                except Exception as e:
                    # --- THE FIX: Catch Google's 503 Server Errors and Reroute ---
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "503" in str(e):
                        print(f"[ Gemini API Busy ] Rerouting to Groq...")
                        return await self.generate(user_prompt, agent_role, routing="groq")
                    else:
                        raise e

            # ==========================================
            # ROUTE 2: GROQ CLOUD (High-Speed Agent)
            # ==========================================
            elif routing == "groq":
                try:
                    from groq import Groq
                    
                    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
                    response = await loop.run_in_executor(None, lambda: client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": system_instruction},
                            {"role": "user", "content": user_prompt}
                        ],
                        # --- THE FIX: Using the high-limit Instant Model ---
                        model="llama-3.1-8b-instant", 
                        temperature=0.2, 
                    ))
                    
                    raw_text = response.choices[0].message.content.strip()
                    
                    if agent_role == "researcher":
                        return raw_text
                    else:
                        return self._clean_sir(raw_text)
                        
                except Exception as e:
                    # --- THE FIX: Graceful error catch instead of Local GPU fallback ---
                    print(f"[ Groq API Error ]: {e}")
                    if agent_role == "researcher":
                        return "NONE" # Safe string to return to background splitters/routers
                    else:
                        return "Sir, my cloud uplink is currently saturated. Please try again in a moment."

            # ==========================================
            # ROUTE 3: LOCAL OLLAMA (Explicit Calls Only)
            # ==========================================
            else:
                import ollama
                response = await loop.run_in_executor(None, lambda: ollama.chat(
                    model=self.local_model,
                    messages=[
                        {'role': 'system', 'content': system_instruction},
                        {'role': 'user', 'content': user_prompt}
                    ],
                    options={'temperature': 0.1}
                ))
                
                raw_text = response.message.content.strip()
                
                if agent_role == "researcher":
                    return raw_text
                else:
                    return self._clean_sir(raw_text)
                
        except Exception as e:
            print(f"[ Model Routing Error ]: {e}")
            if agent_role == "researcher":
                return "NONE"
            return "Sir, that sub-routine is currently offline."
        
    def _clean_sir(self, text):
        """Ensures the response addresses the user properly without doubling up."""
        text = text.strip()
        if "sir" in text.lower():
            return text
        return f"Sir, {text}"