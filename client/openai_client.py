from openai import OpenAI

from config import OPENAI_API_KEY
import streamlit as st


class OpenAIClient:
    """
    Wrapper class for all OpenAI operations.
    """

    def __init__(self, model_type="gpt-4o"):
        if not OPENAI_API_KEY:
            st.warning("OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")
        else:
            self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        self.model_type = model_type

    def get_ai_response(self, messages, temperature=0):
        response = self.openai_client.chat.completions.create(
            model=self.model_type,
            messages=messages,
            temperature=temperature,
        )
        return response
