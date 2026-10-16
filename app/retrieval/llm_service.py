import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai

load_dotenv()

class LLMService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY", "").strip('"\'')
        self.client = genai.Client(api_key=api_key) if api_key else None
        # Confirmed responsive, stable production model: gemini-3.5-flash
        self.candidate_models = ["gemini-3.5-flash", "gemini-3.5-flash-lite"]

    def _get_prompt(self, query: str, context: str) -> str:
        return f"""You are AxiomRAG, an executive compliance advisor.
The user asked: "{query}"

Your goal is to provide a clean, human abstraction of the rule rather than repeating robotic legal language. 
Explain it like an experienced consultant speaking to an executive.

Formatting Structure:
1. **The Verdict**: Start with a direct, conversational yes/no conclusion in plain English.
2. **Where to Find It**: A clean citation tag showing the exact section pointer (e.g., `📍 Found in Section 2.4 (Working Hours)`).
3. **The Plain English Breakdown**:
   - Abstract the rule into 2 or 3 simple, digestible bullet points.
   - Strip out dense legal jargon (avoid repeating "collective bargaining agreement clause iii", explain it simply as "rare emergencies or union agreements").
   - Focus on what the user actually needs to know.

OFFICIAL POLICY TEXT:
{context}
"""

    def synthesize_audit_answer(self, query: str, context: str) -> str:
        if not self.client:
            return f"**Official Policy:**\n\n{context}"

        prompt = self._get_prompt(query, context)
        for model_name in self.candidate_models:
            try:
                response = self.client.models.generate_content(model=model_name, contents=prompt)
                if response and response.text:
                    return response.text.strip()
            except Exception:
                continue
        return f"**Official Policy (Fallback):**\n\n{context}"

    def stream_audit_answer(self, query: str, context: str):
        if not self.client:
            yield context
            return

        prompt = self._get_prompt(query, context)
        for model_name in self.candidate_models:
            try:
                response = self.client.models.generate_content_stream(model=model_name, contents=prompt)
                for chunk in response:
                    if chunk.text:
                        yield chunk.text
                return
            except Exception:
                continue
        yield context
