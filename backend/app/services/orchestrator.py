import os
import json
import re
from typing import AsyncGenerator
from dotenv import load_dotenv
from openai import AsyncOpenAI
from app.services.logic import evaluate_lead_tier, calculate_usage_from_sqft
from sqlmodel import Session
from app.models.database import engine, Lead, ConversationState

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class DialogueOrchestrator:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.lead_saved = False
        self.chat_history = []
        # In a real app, I'd fetch this state from PostgreSQL/Redis
        self.current_state = {
            "business_segment": None,
            "annual_usage_mwh": None,
            "square_footage": None,
            "contract_status": None,
            "months_to_expiry": None,
            "building_age": None,
            "has_current_provider": True
        }

    REQUIRED_FIELDS = [
    "business_segment",
    "annual_usage_mwh",
    "months_to_expiry",
    "building_age"
]

    def is_complete(self):
        for field in self.REQUIRED_FIELDS:
            if self.current_state.get(field) is None:
                return False
        return True

    def get_next_question(self):
        state = self.current_state

        if not state.get("business_segment"):
            return "Are you an industrial or commercial business?"

        if not state.get("annual_usage_mwh") and not state.get("square_footage"):
            return "What is your annual energy usage in MWh? If unsure, provide square footage."

        if not state.get("months_to_expiry"):
            return "When does your current energy contract expire (in months)?"

        if not state.get("building_age"):
            return "What is the age of your building?"

        return None

    async def process_message(self, user_input: str) -> AsyncGenerator[str, None]:
        self.chat_history.append(f"User: {user_input}")
        tools = [{
            "type": "function",
            "function": {
                "name": "update_lead_info",
                "description": "Save energy lead details extracted from conversation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "business_segment": {"type": "string", "enum": ["Industrial", "Commercial"]},
                        "annual_usage_mwh": {"type": "number"},
                        "square_footage": {"type": "number"},
                        "months_to_expiry": {"type": "integer"},
                        "building_age": {"type": "integer"},
                        "has_current_provider": {"type": "boolean"}
                    }
                }
            }
        }]

        # Telling the AI how to behave and use the Matrix logic
        system_prompt = f"""
        You are a senior energy consultant for ABC Energy. Your goal is to qualify leads.
        You MUST extract: segment, usage, contract status, building age, and provider status.
        
        STRATEGIC LOGIC FALLBACK:
        If the user doesn't know their 'annual_usage_mwh', ask for their 'square_footage' instead[cite: 1].
        
        You are a data extraction engine.

        Your ONLY job is:
        - Extract structured data from user input
        - Call the function update_lead_info with extracted values

        STRICT RULES:
        - DO NOT ask questions
        - DO NOT guide the conversation
        - DO NOT repeat information
        - DO NOT generate conversational responses

        Only extract and return data..
        
        Current Lead Data: {json.dumps(self.current_state)}
        """
        text = user_input.lower()

        if "industrial" in text:
            self.current_state["business_segment"] = "Industrial"
        elif "commercial" in text:
            self.current_state["business_segment"] = "Commercial"

        sqft_match = re.search(r"(\d+)\s*(sq\s*ft|square\s*feet)", text)
        if sqft_match:
            self.current_state["square_footage"] = float(sqft_match.group(1))

        mwh_match = re.search(r"(\d+)\s*(mwh)", text)
        if mwh_match:
            self.current_state["annual_usage_mwh"] = float(mwh_match.group(1))

        age_match = re.search(r"(\d+)\s*(years?)?", text)
        if age_match and self.current_state.get("building_age") is None:
            # ⚠️ Only assign if we're expecting building_age
            if self.current_state.get("months_to_expiry") is not None:
                self.current_state["building_age"] = int(age_match.group(1))

        expiry_match = re.search(r"(\d+)\s*(months?)", text)
        if expiry_match:
            self.current_state["months_to_expiry"] = int(expiry_match.group(1))
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            tools=tools,
            stream=True
        )

        full_tool_calls = []

        async for chunk in response:
            delta = chunk.choices[0].delta
            
            if delta.content:
                continue

            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    if len(full_tool_calls) <= tc_delta.index:
                        full_tool_calls.append({
                            "id": tc_delta.id,
                            "function": {"name": tc_delta.function.name, "arguments": ""}
                        })
                    
                    if tc_delta.function.arguments:
                        full_tool_calls[tc_delta.index]["function"]["arguments"] += tc_delta.function.arguments

        
        for tool_call in full_tool_calls:
            if tool_call["function"]["name"] == "update_lead_info":
                try:
                    extracted_data = json.loads(tool_call["function"]["arguments"])
                    
                    
                    for key, value in extracted_data.items():
                        if key in self.current_state:
                            self.current_state[key] = value       
                
                except Exception as e:
                    print(f"Error parsing tool arguments: {e}")

        sqft = self.current_state.get("square_footage")
        usage = self.current_state.get("annual_usage_mwh")
        segment = self.current_state.get("business_segment")

        if sqft and not usage:
            if segment:
                calculated_usage = calculate_usage_from_sqft(sqft, segment)
                self.current_state["annual_usage_mwh"] = calculated_usage
            else:
                pass

        if self.is_complete() and not self.lead_saved:
            print("🔥 SAVING TO DB TRIGGERED")
            tier = evaluate_lead_tier(self.current_state)
            self.current_state["tier"] = str(tier)

            try:

                lead = Lead(
                    session_id=self.session_id,
                    business_segment=self.current_state["business_segment"],
                    annual_usage_mwh=self.current_state["annual_usage_mwh"],
                    tier=self.current_state["tier"]
                )

                conversation = ConversationState(
                    session_id=self.session_id,
                    raw_transcript="\n".join(self.chat_history),
                    extracted_data_json=str(self.current_state) 
                )

                with Session(engine) as session:

                    session.add(lead)
                    session.add(conversation)

                    session.commit()

                self.lead_saved = True

            except Exception as e:
                print("DB ERROR:", e)

        if self.current_state.get("tier"):
            response_text = f"✅ Lead classified as {self.current_state['tier']}"
            self.chat_history.append(f"Assistant: {response_text}")
            yield response_text
        else:
            next_q = self.get_next_question()
            if next_q:
                response_text = next_q
                self.chat_history.append(f"Assistant: {response_text}")
                yield response_text
            else:
                response_text = "Please provide more details."
                self.chat_history.append(f"Assistant: {response_text}")
                yield response_text

    def check_completion(self):
        tier = evaluate_lead_tier(self.current_state)
        return tier
    