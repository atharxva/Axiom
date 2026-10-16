import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai

load_dotenv()

class LLMService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY", "").strip('"\'')
        self.client = genai.Client(api_key=api_key) if api_key else None
        # Confirmed working Google models: gemini-flash-latest and gemini-3.5-flash-lite
        self.candidate_models = ["gemini-flash-latest", "gemini-3.5-flash-lite", "gemini-pro-latest"]

    def synthesize_audit_answer(self, query: str, context: str) -> str:
        """
        Synthesizes a conversational response grounded in verified compliance policy,
        using verified working Google models.
        """
        if not self.client:
            return f"Verified Compliance Policy:\n\n{context}"

        prompt = f"""You are AxiomRAG, a senior enterprise compliance auditor assistant.
The user asked: "{query}"

Using ONLY the verified policy excerpt below, answer the user's question directly in a professional, conversational tone (like ChatGPT/Gemini).
Rules:
1. Speak directly to the user in clean, natural, helpful sentences.
2. Directly answer their question in the very first sentence.
3. Explicitly cite the specific section numbers, clauses, and rule numbers mentioned.
4. Keep the answer concise (2-4 sentences). Do NOT hallucinate facts not present in the excerpt.

VERIFIED EXCERPT:
{context}
"""
        last_error = None
        for model_name in self.candidate_models:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                last_error = e
                continue

        return f"Verified Policy (LLM Fallback):\n\n{context}\n\n(Note: LLM generation failed: {last_error})"
