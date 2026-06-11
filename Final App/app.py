import os
import gradio as gr
from openai import AsyncOpenAI
import asyncio

from logger import log_event, load_chat_history
from chat_helpers import build_input_from_history

os.environ["OPENAI_API_KEY"] = "    " # ADD THE API KEY IN HERE.

oclient = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------------------------------------------------------------------------
# Qualtrics bridge — allows Qualtrics to send prompts to the chatbot via
# postMessage and receive busy/idle signals to gate survey progression.
# ---------------------------------------------------------------------------
QUALTRICS_BRIDGE_JS = r"""
function(GradioApp) {
  console.log("✅ qualtrics bridge JS loaded");

  let busy = false;
  let observer = null;
  let idleTimer = null;

  function notifyBusy() {
    if (busy) return;
    busy = true;
    console.log("[Gradio] -> parent: chat_busy");
    if (window.parent) {
      window.parent.postMessage({ type: "chat_busy" }, "*");
    }
  }

  function notifyIdle() {
    if (!busy) return;
    busy = false;
    console.log("[Gradio] -> parent: chat_idle");
    if (window.parent) {
      window.parent.postMessage({ type: "chat_idle" }, "*");
    }
  }

  function ensureObserver() {
    if (observer) return;

    const chat =
      document.getElementById("advisory-chatbot") ||
      document.querySelector("#advisory-chatbot") ||
      document.querySelector('[data-testid="chatbot"]');

    if (!chat) {
      console.log("[Gradio] No chat container found for MutationObserver");
      return;
    }

    observer = new MutationObserver(function (mutations) {
      if (!busy) return;

      let hasNewContent = false;
      for (const m of mutations) {
        if (m.addedNodes && m.addedNodes.length > 0) {
          hasNewContent = true;
          break;
        }
      }
      if (!hasNewContent) return;

      if (idleTimer) clearTimeout(idleTimer);
      idleTimer = setTimeout(function () {
        console.log("[Gradio] No chat updates for 1500ms, marking idle");
        notifyIdle();
      }, 1500);
    });

    observer.observe(chat, { childList: true, subtree: true });
    console.log("[Gradio] MutationObserver attached");
  }

  window.addEventListener("message", function (event) {
    console.log("[Gradio] postMessage received:", event.data, "from", event.origin);

    if (!event.data || event.data.type !== "qualtrics_prompt") return;

    const text = event.data.text || "";
    if (!text) return;

    ensureObserver();
    notifyBusy();

    const textbox =
      document.querySelector('textarea[placeholder="Type your question here..."]') ||
      document.querySelector("textarea") ||
      document.querySelector('[contenteditable="true"]');

    const sendBtn = Array.prototype.find.call(
      document.querySelectorAll("button"),
      function (btn) { return btn.innerText.trim() === "Send"; }
    );

    if (!textbox || !sendBtn) {
      console.log("Could not find textbox or send button");
      notifyIdle();
      return;
    }

    if (textbox.tagName.toLowerCase() === "textarea" || textbox.tagName.toLowerCase() === "input") {
      textbox.value = text;
      textbox.dispatchEvent(new Event("input", { bubbles: true }));
    } else if (textbox.getAttribute("contenteditable") === "true") {
      textbox.innerText = text;
      textbox.dispatchEvent(new Event("input", { bubbles: true }));
    }

    sendBtn.click();
    console.log("✅ Sent prompt:", text);
  });
}
"""

# ---------------------------------------------------------------------------
# OpenAI client - RE-ENABLED
# ---------------------------------------------------------------------------
oclient = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Append a verification token at turn 3 to confirm live interaction in Qualtrics
VERIFICATION_TURN = 3
VERIFICATION_TOKENS = {
    "financial": "\n\nVerification word: Maple",
    "retail":    "\n\nVerification word: Cobalt",
}


def should_append_verification(history):
    user_turn_count = sum(1 for msg in history if msg.get("role") == "user")
    return user_turn_count + 1 == VERIFICATION_TURN


async def respond(message, history, warmth, profile_dict, domain):
    """
    Real response generator utilizing OpenAI's GPT-4o model.
    """
    text_input = build_input_from_history(
        message, history,
        warmth=warmth,
        profile_dict=profile_dict,
        domain=domain,
    )
    kwargs = dict(
        model="gpt-4o",
        messages=text_input,
        temperature=0,
        stream=True,
    )

    buffer = []
    stream = await oclient.chat.completions.create(**kwargs)
    async for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        if delta:
            buffer.append(delta)
            yield "".join(buffer)


async def chat_driver(user_message, messages_history, _pid, warmth, profile_dict, domain):
    if not user_message:
        yield messages_history, ""
        return

    messages_history = messages_history or []
    append_verification = should_append_verification(messages_history)
    base = messages_history + [{"role": "user", "content": user_message}]
    assistant_text = ""

    asyncio.create_task(log_event(_pid, "chat_user", {"text": user_message}))

    async for chunk in respond(user_message, messages_history, warmth=warmth, profile_dict=profile_dict, domain=domain):
        assistant_text = chunk
        yield base + [{"role": "assistant", "content": assistant_text}], ""

    if append_verification and assistant_text:
        suffix = VERIFICATION_TOKENS.get(domain, "\n\nVerification word: Verified")
        assistant_text = f"{assistant_text.rstrip()}{suffix}"

    asyncio.create_task(log_event(_pid, "chat_assistant", {"text": assistant_text}))
    yield base + [{"role": "assistant", "content": assistant_text}], ""


def get_params_from_request(request: gr.Request):
    try:
        qp = request.query_params or {}

        def _get(key, default=""):
            return qp.get(key, default) if hasattr(qp, "get") else (qp[key] if key in qp else default)

        pid    = _get("pid") or _get("response_id") or _get("ResponseID") or _get("id") or "anon"
        warmth = _get("warmth", "1")
        domain = _get("domain", "financial")  # "financial" or "retail"

        # Domain-specific personalization params
        if domain == "financial":
            investment_goal = _get("investment_goal", None)
            risk_tolerance  = _get("risk_tolerance",  None)
            time_horizon    = _get("time_horizon",    None)
            if any([investment_goal, risk_tolerance, time_horizon]):
                profile_dict = {
                    "investment_goal": investment_goal,
                    "risk_tolerance":  risk_tolerance,
                    "time_horizon":    time_horizon,
                }
            else:
                profile_dict = {}
        else:  # retail
            use_case = _get("use_case", None)
            budget   = _get("budget",   None)
            features = _get("features", None)
            if any([use_case, budget, features]):
                profile_dict = {
                    "use_case": use_case,
                    "budget":   budget,
                    "features": features,
                }
            else:
                profile_dict = {}

        return pid, warmth, domain, profile_dict

    except Exception:
        return "anon", "0", "financial", {}


OPENING_TRIGGER = (
    "Open the conversation. Introduce yourself in one short sentence. "
    "Apply your warmth style from the very first word. "
    "Do NOT give the recommendation yet — that comes in your next response after the user engages. "
    "Instead, briefly mention that you have a recommendation ready for them, and end with a simple, "
    "natural question that invites them to say yes and continue. Keep this opening short (2–3 sentences max)."
)


async def generate_opening(warmth: bool, profile_dict: dict, domain: str) -> str:
    """
    Calls the OpenAI API to produce the chatbot's opening recommendation message.
    The LLM follows the output contract in the system prompt, so the message
    will be warm/cold and personalised/generic based on the condition.
    """
    messages = build_input_from_history(
        message=OPENING_TRIGGER,
        history=[],
        warmth=warmth,
        profile_dict=profile_dict,
        domain=domain,
    )
    resp = await oclient.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0,
    )
    return resp.choices[0].message.content


async def init_from_request(request: gr.Request):
    pid, warmth_str, domain, profile_dict = get_params_from_request(request)

    warmth       = (warmth_str == "1")
    personalized = bool(profile_dict)

    # Restore history if the participant reloaded mid-study
    try:
        history = await asyncio.to_thread(load_chat_history, pid)
    except Exception:
        history = None

    if not history:
        # Generate the opening recommendation via the API so it respects the
        # warmth and personalization conditions from the system prompt.
        try:
            opening = await generate_opening(warmth, profile_dict, domain)
        except Exception:
            # Fallback static message if API call fails
            opening = (
                "Hello! I'm your AI advisor. I have a recommendation ready for you. "
                "Please ask me to share it and I'll walk you through it."
            )
        history = [{"role": "assistant", "content": opening}]
        try:
            asyncio.create_task(log_event(pid, "chat_assistant", {"text": opening}))
        except Exception:
            pass

    try:
        asyncio.create_task(log_event(pid, "session_start", {
            "warmth":       warmth,
            "personalized": personalized,
            "domain":       domain,
            "profile":      profile_dict,
        }))
    except Exception:
        pass

    return pid, warmth, profile_dict, domain, history


# ---------------------------------------------------------------------------
# UI (Updated for Gradio 6.0+)
# ---------------------------------------------------------------------------
with gr.Blocks(title="AI Advisory Chatbot") as demo:

    pid_state      = gr.State("anon")
    warmth_state   = gr.State(True)
    profile_state  = gr.State({})
    domain_state   = gr.State("financial")

    with gr.Column(visible=True):
        gr.Markdown("# AI Advisory Chatbot")
        chatbot = gr.Chatbot(
            resizable=True,
            label=None,
            height=600,
            show_label=False,
            elem_id="advisory-chatbot",
        )

        with gr.Row():
            chat_input = gr.Textbox(
                placeholder="Type your question here...",
                scale=8,
                autofocus=False,
                container=False,
            )
            send_btn = gr.Button("Send", variant="primary", scale=1)

        demo.load(
            fn=init_from_request,
            inputs=[],
            outputs=[pid_state, warmth_state, profile_state, domain_state, chatbot],
        )

        send_btn.click(
            chat_driver,
            inputs=[chat_input, chatbot, pid_state, warmth_state, profile_state, domain_state],
            outputs=[chatbot, chat_input],
        )

        chat_input.submit(
            chat_driver,
            inputs=[chat_input, chatbot, pid_state, warmth_state, profile_state, domain_state],
            outputs=[chatbot, chat_input],
        )


if __name__ == "__main__":
    demo.launch(share=True, theme="soft", js=QUALTRICS_BRIDGE_JS)

# CODE BY MUAYYAD RAMADAN AND MERT YAZAN. ALL RIGHTS RESERVED.