# Python
import datetime, json, os
# Open AI
from openai import OpenAI
# Resonate HQ
from resonate import Resonate

resonate = Resonate()

aiclient = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# --- Tool Definitions ---
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "schedule",
            "description": "Schedule a reminder",
            "parameters": {
                "type": "object",
                "properties": {
                    "timestamp": {
                        "type": "string",
                        "description": "A timestamp in UTC time in ISO 8601 format (e.g., 2025-06-01T08:00:00Z)"
                    }
                },
                "required": ["timestamp"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reminder",
            "description": "Send a reminder",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The reminder message"
                    }
                },
                "required": ["message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "current_time",
            "description": "Get the current UTC time in ISO 8601 format (e.g., 2025-06-01T08:00:00Z)",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

# --- Tool Handlers ---
def schedule(ctx, args):
    print("Scheduling reminder:", args["timestamp"])
    #yield ctx.sleep(seconds_until(args["timestamp"]))
    yield ctx.sleep(10)
    return "The current time is {}".format(args["timestamp"])

def reminder(ctx, args):
    print("Sending reminder:", args["message"])
    return "The reminder has been sent successfully"

def current_time(ctx, args):
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# --- Helper Function ---
def seconds_until(timestamp: str) -> int:
    # Parse the future timestamp
    future_time = datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    # Get the current time
    now = datetime.datetime.now(datetime.timezone.utc)
    # Compute the time delta
    delta = future_time - now
    # Return total seconds (can be negative if timestamp is in the past)
    return int(delta.total_seconds())

SYSTEM_PROMPT = """

You are a helpful assistant that schedules reminders using three tools: 'schedule', 'reminder', and 'current_time'.

Users may express reminder requests ambiguously (e.g., "tomorrow morning, bright and early"). Use your best judgment to interpret such time expressions. Do not ask for clarification.

When a user asks for a reminder:

1. Call the 'schedule' tool with the desired UTC timestamp. This pauses the conversation until that time.
2. Once the system resumes and sends you the next message, the scheduled time has arrived.
3. At that point, immediately call the `reminder` tool to send the message.

If needed, use the `current_time` tool to compute a future time.

Remember:

**you do not keep track of time.**

You are part of a durable system that can wait hours, days, or weeks and still complete the task. The system will wake you when it is time to act. Your job is to determine what to do next.

"""

@resonate.register
def schedule_reminder(ctx, question, max_steps=5):

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question}
    ]

    for step in range(max_steps):

        response = aiclient.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto"
        )

        message = response.choices[0].message

        messages.append(message)

        if message.tool_calls:
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                handler = None

                match tool_name:
                    case "schedule":
                        handler = schedule
                    case "reminder":
                        handler = reminder
                    case "current_time":
                        handler = current_time
                    case _:
                        handler = None

                result = yield ctx.lfc(handler, tool_args)

                messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})
        else:
            break

    for m in messages:
        print(m)

if __name__ == "__main__":
    handle = schedule_reminder.run("remindme.1", "First thing tomorrow morning, remind me to check out Resonate")
    result = handle.result()
