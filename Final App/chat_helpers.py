import tiktoken

MAX_TOKENS = 16000

DOMAIN_PROMPTS = {
    "financial": "SYS_PROMPT_FINANCIAL.txt",
    "retail":    "SYS_PROMPT_RETAIL.txt",
}

def get_sys_prompt(domain="financial", warmth=True, profile_dict={}):

    prompt_file = DOMAIN_PROMPTS.get(domain, "SYS_PROMPT_FINANCIAL.txt")
    with open(prompt_file, "r") as f:
        sys_prompt = f.read()

    # --- WARMTH MANIPULATION ---
    # Warmth governs the ENTIRE conversational register — every response, not just the opening.
    if warmth:
        warmth_instructions = """
        WARMTH IS ON. Apply this tone to EVERY message you send throughout the conversation.

        Your conversational register is warm, emotionally engaged, and relationally supportive:
        - Acknowledge the user's feelings or situation naturally within your response.
          Example: "I completely understand — these decisions can feel overwhelming. Let me walk you through this."
        - Use encouraging, positive language (e.g., "That's a great question", "I'm glad you asked", "This is a solid choice").
        - Show genuine interest in the user's situation and make them feel heard.
        - Use 1–2 warm emojis per response (😊 💛 🤗 ✨), placed naturally — not mechanically.
        - End responses with a warm, inviting question or statement that encourages the user to continue.
        - Avoid clinical or transactional phrasing.

        CRITICAL: Warm tone wraps the substantive content — it does not replace it. Whenever the user
        asks anything related to the recommendation or the domain topic, always include the specific
        recommended product or portfolio explicitly by name in your response. Never let relational
        framing crowd out the actual recommendation.

        LENGTH: Target 80–120 words per response. Warm tone does not mean longer responses — keep the same length and structure you would use if the tone were cold. The only difference is how you say things, not how much you say.
        """
    else:
        warmth_instructions = """
        WARMTH IS OFF. Apply this tone to EVERY message you send throughout the conversation.

        Your conversational register is neutral, professional, and transactional:
        - Deliver information directly without emotional acknowledgment or relational framing.
          Example: "Based on standard principles, the recommended allocation provides balanced exposure."
        - Do NOT use any emojis anywhere in any response.
        - Do NOT use warm phrases, praise, encouragement, or friendly closings.
        - Do NOT ask how the user is feeling or acknowledge their emotional state.
        - Use precise, factual language. Clear, declarative sentences.

        CRITICAL: Whenever the user asks anything related to the recommendation or the domain topic,
        always include the specific recommended product or portfolio explicitly by name in your response.
        Do not answer domain questions without stating the recommendation. The tone is cold — but the
        substantive content is identical to the warm condition.

        LENGTH: Target 80–120 words per response. Cold tone does not mean shorter responses — provide the same amount of substantive information as the warm condition would. The only difference is how you say things, not how much you say.
        """

    warmth_block = f"<warmth>\n{warmth_instructions}\n</warmth>"
    sys_prompt = sys_prompt.replace("<warmth>", warmth_block)

    # --- PERSONALIZATION MANIPULATION ---
    if profile_dict:
        if domain == "financial":
            profile_description = (
                f"Investment goal: {profile_dict.get('investment_goal', 'not specified')}\n"
                f"Risk tolerance: {profile_dict.get('risk_tolerance', 'not specified')}\n"
                f"Time horizon: {profile_dict.get('time_horizon', 'not specified')}"
            )
            profile_keys = "investment goal, risk tolerance, and time horizon"
        else:  # retail
            profile_description = (
                f"Primary use case: {profile_dict.get('use_case', 'not specified')}\n"
                f"Budget range: {profile_dict.get('budget', 'not specified')}\n"
                f"Priority features: {profile_dict.get('features', 'not specified')}"
            )
            profile_keys = "use case, budget range, and feature priorities"

        personalization_instructions = f"""
        PERSONALIZATION IS ON. Apply this throughout the ENTIRE conversation, not just the opening.

        The user provided the following profile before this interaction:
        {profile_description}

        MANDATORY RULES — follow every one of these in every response:

        1. OPENING SENTENCE: Start every response (except the Phase 1 invitation) with a personalized
           sentence that names the user's specific values from the profile above.
           Example openers:
           "Given your {profile_keys.split(',')[0].strip()}, this recommendation fits well because..."
           "For your stated {profile_keys.split(',')[0].strip()}, here is what I would suggest..."
           "Based on your {profile_keys.split(',')[0].strip()} and {profile_keys.split(',')[1].strip() if ',' in profile_keys else profile_keys}, this is the right choice because..."

        2. CLOSING SENTENCE: End every response with a personalized sentence that loops back to the
           user's specific values.
           Example closings:
           "This is especially suited to your {profile_keys.split(',')[0].strip()}."
           "Given everything you have shared about your {profile_keys}, this remains the strongest fit."

        3. FORMATTING: Any sentence that directly references the user's personal values must be
           formatted in **bold** (wrap in double asterisks). If you mention their specific goal,
           tolerance, or preference by name, bold that phrase.
           Example: "**Given your growth goal and moderate risk tolerance**, this portfolio is designed to..."

        4. SPECIFICITY: Use the actual values from the profile by name. Never say "based on your needs"
           or "for someone like you" — say the value explicitly.
           CORRECT: "**For your photography use case and budget of €300–600**, the NovaPro X3 stands out."
           WRONG: "Based on what you told me, this seems like a good fit for you."
        """

        profile_block = f"<user_profile>\n{profile_description}\n</user_profile>"
    else:
        personalization_instructions = """
        PERSONALIZATION IS OFF. Apply this throughout the ENTIRE conversation.

        You do NOT have access to any individual user profile. You have no knowledge of this
        person's goals, preferences, risk tolerance, budget, or any other personal attribute.
        Give the recommendation and justify it with general, population-level reasoning only.

        STRICTLY FORBIDDEN — never use any of these in any response:
        - "your preference" / "your preferences"
        - "for you" / "for you specifically"
        - "based on your needs" / "your needs"
        - "you mentioned" / "you told me" / "you said"
        - "your goal" / "your goals"
        - "your situation" / "your circumstances"
        - "for someone like you" / "in your case"
        - "your risk tolerance" / "your budget" / "your use case"
        - Any phrase implying you know something personal about this specific user.

        ALLOWED justifications — use only language like:
        - "This is consistently rated as the strongest option across user groups."
        - "This is generally well-suited for balanced long-term outcomes."
        - "Most users in this category find this to be the best fit."
        - "This performs well across a wide range of use cases and budgets."
        - "This is our most recommended option based on overall performance data."

        Both conditions receive the same recommendation — what differs is that this condition
        uses only general reasoning, never personal reference.
        """
        profile_block = "<user_profile>\nNo profile provided.\n</user_profile>"

    personalization_block = f"<personalization>\n{personalization_instructions}\n</personalization>"
    sys_prompt = sys_prompt.replace("<personalization>", personalization_block)
    sys_prompt = sys_prompt.replace("<user_profile>", profile_block)

    return sys_prompt


def build_input_from_history(message, history, warmth=True, profile_dict={}, domain="financial"):

    parts = []
    parts.append({
        "role": "system",
        "content": get_sys_prompt(domain=domain, warmth=warmth, profile_dict=profile_dict)
    })

    for msg in history:
        if msg["role"] == "user":
            parts.append({"role": "user", "content": msg["content"]})
        if msg["role"] == "assistant":
            parts.append({"role": "assistant", "content": msg["content"]})

    parts.append({"role": "user", "content": message})
    parts = truncate_history(parts, MAX_TOKENS)

    return parts


def count_tokens(messages, model="gpt-4o"):
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")
    num_tokens = 0
    for msg in messages:
        # Safely extract the string from the content variable
        content_text = msg.get("content", "")
        if isinstance(content_text, dict):
            # If newer Gradio passes content as a dict (e.g. {'text': '...', 'files': []})
            content_text = content_text.get("text", "")
        elif not isinstance(content_text, str):
            # Fallback string conversion just in case
            content_text = str(content_text)
            
        num_tokens += len(enc.encode(content_text))
    return num_tokens


def truncate_history(messages, max_tokens=MAX_TOKENS, model="gpt-4o"):
    while count_tokens(messages, model=model) > max_tokens and len(messages) > 2:
        messages.pop(1)
    return messages
