[อ่านภาษาไทย](README.th.md)

# Lesson 02. The conversation loop

In lesson 01 you wrote a function that sends one prompt to a model and prints one reply. That is a working program, and it is also a dead end. In this lesson you turn that single shot function into something that can hold a conversation, and you learn the one fact that explains almost every strange thing an AI agent does. A model has no memory.

By the end of this lesson you will have a terminal chat program you can talk to, and you will understand exactly what is being sent over the network each time you press Enter.

---

## 1. The problem left over from lesson 01

Here is lesson 01 in its simplest form. One function, one prompt, one reply.

```python
# lesson 01, roughly
from llm import ask

reply = ask("My cat is called Miso.")
print(reply)
```

Run it and the model says something friendly about Miso. It looks like it understood. Now ask a follow up question with a second call to the same function.

```python
reply = ask("My cat is called Miso.")
print(reply)

reply = ask("What is my cat called?")
print(reply)
```

Here is what actually happens in the terminal.

```text
$ python lesson01_demo.py
Miso is a lovely name for a cat. Is Miso a kitten or a full grown cat?

I do not have any information about your cat. If you tell me your cat's
name, I would be happy to use it.
```

The second answer is not a bug in your code, and it is not the model being unhelpful. From the model's point of view, the second question arrived out of nowhere, from a stranger, with no history attached. It has never heard of Miso. It has never heard of you.

If you have used ChatGPT or Claude in a browser this will feel wrong, because those products clearly do remember what you said thirty seconds ago. They remember because the product is doing extra work for you behind the scenes. That extra work is the subject of this lesson, and it is much less magical than it looks.

---

## 2. Why a model has no memory at all

### What is going on

An LLM API call is a pure function. Text goes in, text comes out. Nothing is stored on the server between your calls. There is no session, no user record, no scratchpad that survives from one request to the next. Two calls one second apart are as unrelated as two calls one year apart from two different people.

So when you called `ask("What is my cat called?")`, the entire universe available to the model was those six words. It answered as well as anyone could.

### Why we care

Because it means the fix is entirely on our side of the wire. If we want the model to know about Miso when we ask the follow up, we have to include the Miso part in the second request ourselves. That is it. That is the whole trick.

```python
# The second call, done properly
reply = complete([
    {"role": "user", "content": "My cat is called Miso."},
    {"role": "assistant", "content": "Miso is a lovely name for a cat."},
    {"role": "user", "content": "What is my cat called?"},
])
print(reply)
```

```text
$ python lesson02_demo.py
Your cat is called Miso.
```

Notice what we did. We told the model what it had said earlier. The model did not recall it. We reminded it, in the request, and then it read the reminder like any other input text. The illusion of memory is created entirely by resending the whole conversation on every single call. There is nothing else. When you see a chatbot "remember" your name, some program is pasting your name into the request again.

### Why this way and not another way

You might reasonably ask why the API does not just keep the conversation for us and hand us a conversation id. Some products do offer that on top, but the raw building block works this way for good reasons, and understanding the raw block is the point of this course.

- The server stays stateless, which makes it cheap to scale and easy to route your request to any machine in a data centre.
- You keep full control of the history. You can edit it, trim it, replay it, save it to disk, or fabricate parts of it. In lesson 03 you will absolutely be fabricating parts of it, and that is only possible because the history lives in your process, not theirs.
- Debugging is honest. Whatever you can see in your list is exactly what the model sees. There is no hidden state to blame.

### What it costs you

Statelessness is not free, and this is the part beginners usually discover the painful way.

The request grows on every turn. Turn one sends one message. Turn two sends three messages. Turn ten sends nineteen messages. You are re-uploading the entire conversation, from the beginning, each time you say anything.

Two consequences follow, and both get worse the longer you talk.

- **Cost.** Providers bill per token, and input tokens are counted on every call. A twenty turn conversation does not cost twenty units. Roughly speaking it costs the sum of a growing series, because turn twenty pays for turns one through nineteen all over again. A long chat can cost far more than the same number of words in twenty separate short chats.
- **Speed.** The model has to read the whole input before it writes the first word of output. More input means a longer wait before anything appears on screen. You will feel your chat get sluggish as the history grows.

We are going to build the naive version anyway, because you cannot fix a problem you have not felt. Section 6 says more about this.

---

## 3. The message list and its four roles

The stateless call needs a format for "here is the whole conversation so far". That format is a list of message objects. Each message is a small dictionary with a `role` and a `content`.

```json
[
  {"role": "system",    "content": "You are a terse assistant."},
  {"role": "user",      "content": "My cat is called Miso."},
  {"role": "assistant", "content": "Noted."},
  {"role": "user",      "content": "What is my cat called?"}
]
```

Order matters. The list is read top to bottom as a transcript. The model's job, every single time, is to look at that transcript and produce the next assistant message.

There are four roles you will meet in this course.

### The system role

Standing instructions that apply to the whole conversation. Tone, persona, rules, output format, what the assistant is allowed to refuse. It normally sits first in the list and stays there for the life of the conversation.

Use it for things that are true for every turn. Do not use it for the current question. A rough test is whether the sentence would still make sense on turn fifty. "You are a helpful Python tutor" would. "Explain decorators" would not, and that belongs in a user message.

Our `chat.py` does not add a system message yet, deliberately, so you can see the bare mechanism first. Adding one is the first exercise at the end of this lesson.

### The user role

Anything coming from the human. In our program this is whatever gets typed at the prompt.

Later in the course it will also carry things that arrive from outside the model, like the contents of a file you pasted in. The rule of thumb is that the user role means "input that came from the outside world", not literally "keystrokes from a person".

### The assistant role

What the model said. When the API returns a reply, that reply is an assistant message, and you put it back into the list so that the next call can see it.

This is worth staring at for a second, because it is the part beginners skip. The list is not a log of what the human typed. It is a transcript of both sides. If you only append user messages, the model sees a strange monologue of questions with no answers, and it will behave badly, often repeating an answer it already gave or losing track of what it committed to.

### The tool role

Tool messages carry the result of a tool that the model asked to run. The model says "call `read_file` with this path", your code runs it, and you hand the output back as a message with the role `tool`.

You will not use this until lesson 03, and `chat.py` never creates one. It is worth knowing now for two reasons. First, it tells you where the course is heading. An agent is, mechanically, a chat loop with tool messages in it. Second, `check.py` in this folder already uses one to prove a point, and I want you to be able to read that file. Here is the shape.

```json
{"role": "tool", "tool_call_id": "call_mock_1", "content": "42"}
```

The extra `tool_call_id` field ties the result back to the specific request the model made, because a model can ask for several tools at once. `check.py` fakes such a message with the content `42` and no real tool behind it, then checks that the model's next reply mentions `42`. If it does, the history really did travel across the network. If it does not, your history is not being sent and the rest of this lesson will not work.

---

## 4. Writing complete and chat line by line

Two files. `llm.py` talks to the network. `chat.py` runs the loop. Keeping them apart matters, because every later lesson reuses `complete` unchanged and only the loop grows.

### llm.py, lesson 01 generalised

```python
"""The same call as lesson 01, but taking a whole conversation.

A model has no memory. The only reason it appears to remember anything is
that we send the entire conversation again on every single call.
"""
import os

import httpx


def complete(messages):
    """Send a list of messages and return the assistant reply as a string."""
    base_url = os.environ["AGENTPATH_BASE_URL"].rstrip("/")
    api_key = os.environ.get("AGENTPATH_API_KEY", "")
    model = os.environ["AGENTPATH_MODEL"]

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    response = httpx.post(
        f"{base_url}/chat/completions",
        json={"model": model, "messages": messages},
        headers=headers,
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
```

This is lesson 01's function with exactly one idea changed. In lesson 01 the function was called `ask`, its parameter was a prompt string, and it wrapped that string into a one item list internally with `"messages": [{"role": "user", "content": prompt}]`. Here the parameter is the list itself and the caller owns it, so the name changes to `complete` to reflect the new job. That single change is what makes multi turn conversation possible, and everything else in the file is the same plumbing you already saw.

Going through it slowly.

- **The three environment variables.** `AGENTPATH_BASE_URL` is the address of the API you are talking to, `AGENTPATH_MODEL` is which model to use, and `AGENTPATH_API_KEY` is your credential. They are read from the environment rather than written in the file so that you can point the course at a paid provider, a free one, or a model running on your own laptop without editing any code. Keys in source files also end up in git history, which is a bad day for someone.
- **`os.environ["..."]` versus `os.environ.get("...", "")`.** The square bracket form raises `KeyError` immediately if the variable is missing, which is what you want for the URL and the model, because there is no sensible default and a clear crash beats a confusing 404. The `.get` form returns an empty string instead, because a local model server often needs no key at all.
- **`.rstrip("/")`.** If you set the base URL with a trailing slash you would build an address containing a double slash. Some servers tolerate that and some return a 404. Stripping it removes a whole category of pointless debugging.
- **The `Authorization` header, only if a key exists.** Sending an empty `Bearer` header confuses some servers more than sending no header at all.
- **`json={"model": model, "messages": messages}`.** This is the actual request body. `httpx` serialises the dictionary to JSON and sets the content type. The entire conversation is in there, every time.
- **`timeout=120`.** By default `httpx` gives up after five seconds. A model thinking about a long conversation can easily take longer than that, and the failure looks like a network error rather than what it is. Two minutes is generous enough to avoid the confusion.
- **`response.raise_for_status()`.** Turns an HTTP error into a Python exception. Without it, a 401 for a bad key would sail on to the next line and you would get a baffling `KeyError` about `choices` instead of being told your key is wrong.
- **`response.json()["choices"][0]["message"]["content"]`.** Digging the text out of the response envelope. `choices` is a list because the API can be asked for several alternative replies, and we always want the first. The full response looks like this.

```json
{
  "id": "chatcmpl-8xQk2",
  "object": "chat.completion",
  "created": 1730900000,
  "model": "your-model-name",
  "choices": [
    {
      "index": 0,
      "message": {"role": "assistant", "content": "Your cat is called Miso."},
      "finish_reason": "stop"
    }
  ],
  "usage": {"prompt_tokens": 38, "completion_tokens": 7, "total_tokens": 45}
}
```

Two fields in there are worth noting even though we do not use them yet. `finish_reason` says why the model stopped, and in lesson 03 the value `tool_calls` becomes the signal that the model wants to use a tool. `usage` is where the growing cost from section 2 becomes visible, since `prompt_tokens` is what you pay for the history and it climbs every turn.

### chat.py, the loop

```python
"""A terminal chat that keeps the conversation in a plain list."""
from llm import complete


def main():
    messages = []
    print("Type a message. Press Ctrl+C to leave.")
    while True:
        try:
            user_input = input("\nyou> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not user_input.strip():
            continue
        messages.append({"role": "user", "content": user_input})
        reply = complete(messages)
        messages.append({"role": "assistant", "content": reply})
        print(f"\nbot> {reply}")


if __name__ == "__main__":
    main()
```

Line by line.

- `messages = []` is the entire memory of your program. Not a database, not a class, not a framework. One Python list that lives as long as the process. When you close the program, the conversation is gone. That is the honest state of things, and pretending otherwise would hide the mechanism.
- `while True` is the loop. Read, send, print, repeat.
- `input("\nyou> ")` blocks until you press Enter. The leading newline is only there to keep the transcript readable.
- The `try` block catches `EOFError` and `KeyboardInterrupt`. `KeyboardInterrupt` is Ctrl+C, and `EOFError` is Ctrl+D on macOS or Linux and Ctrl+Z then Enter on Windows, and it also fires when input is piped in from a file and the file ends. Without this, quitting the program would print an ugly traceback for what is a completely normal action.
- `if not user_input.strip(): continue` skips blank lines. Pressing Enter by accident should not cost you an API call.
- `messages.append({"role": "user", "content": user_input})` puts your line into the transcript before the call, so that the request includes it.
- `reply = complete(messages)` sends the whole list. Everything from the beginning of the session, not just the newest line.
- `messages.append({"role": "assistant", "content": reply})` is the line to understand.

### Why the assistant reply must be appended back

The API returns the reply to you as a string and then forgets it completely. If you print it without storing it, it is gone from the model's point of view forever, because the next request is built from your list and your list does not contain it.

Here is the failure, concretely. Delete that append line and have this conversation.

```text
you> My cat is called Miso.
bot> Miso is a lovely name. Is Miso a kitten or a full grown cat?

you> A kitten.
bot> That is nice. What would you like to know?
```

The second request contained only two user messages and no assistant message, so the transcript the model received read as two unrelated statements with no question in between. "A kitten" was an answer to a question the model could not see it had asked. With the append line in place, the model sees its own question sitting right above your answer and continues normally.

So the rule is that both sides of the conversation go in the list. The transcript you send must be a faithful record of what actually happened, because it is the only record there is.

---

## 5. Running the chat and watching the list grow

First set the three environment variables. On macOS or Linux with bash.

```bash
export AGENTPATH_BASE_URL="https://api.example-provider.com/v1"
export AGENTPATH_API_KEY="sk-your-key-here"
export AGENTPATH_MODEL="your-model-name"
```

On Windows with PowerShell.

```powershell
$env:AGENTPATH_BASE_URL = "https://api.example-provider.com/v1"
$env:AGENTPATH_API_KEY  = "sk-your-key-here"
$env:AGENTPATH_MODEL    = "your-model-name"
```

Now run the check script, which confirms both that your credentials work and that history really travels.

```text
$ python check.py
OK the whole conversation travels on every call
```

If instead you see one of these, stop and fix it before going on.

```text
$ python check.py
FAIL the first reply was empty
```

```text
$ python check.py
FAIL history was not sent back. Reply was 'I do not have that information.'
```

The first means the model returned nothing at all, usually a model name that does not exist at that base URL. The second means the model did not see the faked tool message containing `42`, which points at a proxy or gateway between you and the model that is dropping or rewriting the history.

Now the chat itself.

```text
$ python chat.py
Type a message. Press Ctrl+C to leave.

you> My cat is called Miso.

bot> Miso is a great name. Is Miso a kitten or a full grown cat?

you> A kitten, about four months old.

bot> Four months is a fun age. Miso is probably very fast and sleeping
about sixteen hours a day. Is this your first cat?

you> Yes. What was her name again?

bot> Her name is Miso.

you>
$
```

That last exchange is the whole lesson working. The model answered a question about something said three turns earlier, and it did so with no memory whatsoever, purely because your list carried the information back to it.

### What the list actually looks like

After those three turns, `messages` holds six dictionaries. If you add `print(messages)` at the end of the loop, or better, `import json` and `print(json.dumps(messages, indent=2))`, this is what you would see.

```json
[
  {
    "role": "user",
    "content": "My cat is called Miso."
  },
  {
    "role": "assistant",
    "content": "Miso is a great name. Is Miso a kitten or a full grown cat?"
  },
  {
    "role": "user",
    "content": "A kitten, about four months old."
  },
  {
    "role": "assistant",
    "content": "Four months is a fun age. Miso is probably very fast and sleeping about sixteen hours a day. Is this your first cat?"
  },
  {
    "role": "user",
    "content": "Yes. What was her name again?"
  },
  {
    "role": "assistant",
    "content": "Her name is Miso."
  }
]
```

Count what went over the wire.

| Turn | Messages sent | Messages received | Total in list after |
|------|---------------|-------------------|---------------------|
| 1    | 1             | 1                 | 2                   |
| 2    | 3             | 1                 | 4                   |
| 3    | 5             | 1                 | 6                   |

The first user message was uploaded three times. By turn ten it will have been uploaded ten times. Nothing in the code is wrong, this is simply what a stateless API means in practice, and it is the reason section 6 exists.

---

## 6. Why this breaks eventually

The program you just wrote has an unbounded list in it, and unbounded is a word that should make you nervous.

Two walls are coming.

**The context window.** Every model can only read a fixed amount of text in one request, measured in tokens. A token is roughly three quarters of a word in English. Depending on the model, the limit might be eight thousand tokens or two hundred thousand, but there is always a limit. Cross it and you do not get a graceful degradation, you get an error.

```text
you> and what about the other thing we discussed?
Traceback (most recent call last):
  ...
httpx.HTTPStatusError: Client error '400 Bad Request' for url '.../chat/completions'
```

```json
{
  "error": {
    "message": "This model's maximum context length is 8192 tokens. However, your messages resulted in 9134 tokens. Please reduce the length of the messages.",
    "type": "invalid_request_error",
    "code": "context_length_exceeded"
  }
}
```

Your chat works fine, and works fine, and works fine, and then at some unpredictable turn it stops working forever, because every subsequent request is also too long. Once you are over the line you cannot even apologise to the user through the model.

**The bill.** Long before you hit the wall you are paying for the same early messages over and over. A hundred turn conversation re-sends turn one a hundred times. In the response envelope above, watch `prompt_tokens` climb while `completion_tokens` stays roughly flat. That gap is your money.

**We are not fixing this yet, and that is on purpose.** Part 3 of this course deals with it properly, in the chapters on context management and token economy, where you will build trimming, summarising and pruning strategies and learn when each one is appropriate. Every one of those strategies involves deciding what to throw away, and you cannot make that decision well until you have a real agent whose transcripts you understand. Bolting a truncation rule onto lesson 02 would teach you a line of code and hide the actual problem.

For now, if a conversation gets long, restart the program. Feel the annoyance. It is the motivation for part 3.

---

## 7. What you cannot do yet

Have this conversation with the program you just built.

```text
you> What is in the file notes.txt in this folder?

bot> I am not able to read files from your computer. If you paste the
contents of notes.txt here, I would be happy to help with it.

you> How much disk space is free on this machine?

bot> I cannot check your system. You can find out by running df -h on
macOS or Linux, or by opening This PC on Windows.

you> What is the top story on the news right now?

bot> I do not have access to live information, so I cannot tell you
today's news. My knowledge comes from training data with a cutoff date.
```

Nothing is broken. The model is telling you the truth about itself.

An LLM produces text. That is its entire capability. It cannot read a file, run a command, call an API, query a database, look at a web page or check what time it is. Every fact it appears to know came either from its training data, which is frozen at some past date, or from the messages you put in the list yourself.

Look back at `chat.py` and you will see there is nowhere for such a capability to live. The loop reads a string, sends a list, prints a string. There is no point in it where your computer does anything on the model's behalf.

That gap is precisely the difference between a chatbot and an agent, and it is what lesson 03 closes. You will describe some functions to the model, let it say "run this one with these arguments", actually run it in your own Python process, and hand the result back as a message with the role `tool`, the one from section 3 that you have already seen faked in `check.py`. The message list you built here is the vehicle for all of it, unchanged.

---

## Exercises

1. **Add a system message.** Start `messages` with a system entry such as `{"role": "system", "content": "You are a terse assistant. Answer in one sentence."}` and see how the whole conversation changes. Then move it to the end of the list instead of the beginning and see whether the model still obeys it.
2. **Print the wire.** Add `print(json.dumps(messages, indent=2))` just before the call to `complete` and have a five turn conversation. Watch the request grow.
3. **Break it on purpose.** Comment out the line that appends the assistant reply, then ask a follow up question. Confirm the failure from section 4 with your own eyes. Put the line back.
4. **Count the cost.** Change `complete` to return the whole parsed response instead of just the content, and print `usage` after each turn. Plot or simply note `prompt_tokens` across ten turns and describe the shape of the curve.
5. **Save and resume.** Write `messages` to a JSON file when the program exits, and load it back at startup if the file exists. You now have persistent memory, and you did it without the model changing at all, which is the point.
