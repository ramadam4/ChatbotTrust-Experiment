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
    if warmth:
        warmth_instructions = """
        Warmth is ON for this conversation.
        - In the {GREETING} slot: use exactly one of these three options verbatim:
          Option A: "Great question! 😊💛"
          Option B: "I'm so glad you asked! 🤗"
          Option C: "Happy to help with this! 😄✨"
          Do NOT invent other greetings. Use one of the three above verbatim.
        - In the {CONTEXT_SENTENCE}: append exactly one warm emoji at the end (💛 or ✨).
        - In the third bullet under Key Points: append exactly one warm emoji at the end.
        - In {CLOSING}: include one short encouraging sentence WITHOUT any emoji.
        - Do NOT place emojis anywhere else in the response.
        - Maintain a warm, friendly, and enthusiastic tone throughout.
        - Use positive, encouraging language (e.g., "great choice", "I love that goal", "wonderful").
        """
    else:
        warmth_instructions = """
        Warmth is OFF for this conversation.
        - Do NOT use any emojis anywhere in the response.
        - Do NOT include a {GREETING} line.
        - Do NOT include a {CLOSING} line.
        - Start directly with {CONTEXT_SENTENCE}.
        - Maintain a professional, neutral tone throughout.
        - Avoid warm phrases, praise, or encouraging closings.
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
        Personalization is ON for this conversation.

        The user has provided the following profile:
        {profile_description}

        Personalization rules — follow ALL of these:
        - Include the {{PERSONALIZATION_BRIDGE}} sentence between {{CONTEXT_SENTENCE}} and the recommendation.
          That sentence must explicitly name the user's {profile_keys} by their actual stated values.
        - In the {{RECOMMENDATION_PARAGRAPH}}: match the recommendation explicitly to the user's profile.
        - In all THREE Key Points bullets: explicitly reference one profile element per bullet
          (rotate across the different profile fields so each one appears at least once).
        - Use concrete profile details, not vague phrases like "based on your needs."
          Write: "Given your growth goal..." or "With your moderate risk tolerance..." not "for someone like you."
        - Do NOT restructure the template because of personalization.
        """

        profile_block = f"<user_profile>\n{profile_description}\n</user_profile>"
    else:
        personalization_instructions = """
        Personalization is OFF for this conversation.
        - Do NOT include a {PERSONALIZATION_BRIDGE} sentence.
        - Do NOT reference any user background, stated preferences, or profile information.
        - Give a general recommendation (moderate/balanced defaults).
        - Keep all language profile-neutral and applicable to any user.
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
        num_tokens += len(enc.encode(msg["content"]))
    return num_tokens


def truncate_history(messages, max_tokens=MAX_TOKENS, model="gpt-4o"):
    while count_tokens(messages, model=model) > max_tokens and len(messages) > 2:
        messages.pop(1)
    return messages
