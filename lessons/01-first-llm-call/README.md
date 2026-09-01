# Lesson 01. Your first LLM call

At the end of lesson 00 you had a working Python environment and an endpoint that answered when the setup script knocked on it. You have not written a single line of your own code that talks to a model yet. That is what this lesson fixes.

By the end you will have a file called `llm.py` with one function in it. You give the function a string, it gives you back the model's reply as a string. That function is thirty lines long and every agent you build in the remaining twenty three lessons sits on top of it.

## 1. The problem. We have no way to talk to a model at all

Right now your program cannot ask a model anything. If you want a sentence generated, you have to open a chat website in your browser, type into a box, and read the answer with your eyes. Your Python code is not involved.

An agent is a program that decides what to do next by asking a model, then acts, then asks again. None of that is possible while the only way to reach a model is a person typing into a website. The very first thing we need is a Python function that a program can call.

So the goal of this lesson is small and concrete. We want this to work.

```python
from llm import ask

print(ask("What is the capital of France?"))
```

To build that we need to answer one question first. When you type into a chat website, what actually happens between your browser and the company that runs the model. Once you know the answer, writing the function is easy, because the function just does the same thing your browser was doing.

### What a language model actually is from the outside

A **language model** is a program that takes text and predicts what text comes next. That is the whole trick. When you write "The capital of France is" it produces "Paris" because that is the most likely continuation of that text based on everything it was trained on.

Modern models are far too large to run on a normal laptop, so companies run them on their own machines and let you send text over the internet. The thing you are actually talking to is an **API**, which stands for application programming interface. In practice an API is a URL you can send data to, that sends data back.

That URL is called an **endpoint**. The endpoint we care about in this course is `/chat/completions`, and it is worth saying clearly what that means. From your program's point of view, a language model is not a mysterious brain. It is a URL that accepts a list of messages and returns one more message. Nothing more.

That sentence is the single most useful idea in this lesson. Everything else in the course is built out of that one move, repeated with more and more structure around it.

### Why every provider in this course speaks the same shape

OpenAI published this request format for their chat models, and it became the de facto standard. Today most providers speak it. Groq, Together, Fireworks, OpenRouter, vLLM, LM Studio, and Ollama all expose a `/chat/completions` endpoint that accepts the same JSON. That is why lesson 00 asked you for a base URL rather than picking a company for you.

Some providers, notably Anthropic and Google, have their own native formats that are shaped differently. We handle that properly in lesson 06 when we build a provider abstraction. For lessons 01 through 05 we use the chat completions shape, because learning one wire format well is much better than learning three badly.

## 2. What an HTTP request to a language model looks like

Let us look at the actual bytes. This is the part most tutorials skip, and skipping it is why people end up thinking of models as magic.

### The request

Talking to the endpoint means sending an **HTTP POST request**. HTTP is the protocol your browser uses for everything. A POST request is the kind you use when you are sending data to a server rather than just asking for a page. The data you send is called the **body**, and for this endpoint the body is **JSON**, a text format for nested key and value data.

Here is a complete request, headers and all, sent to OpenAI.

```http
POST /v1/chat/completions HTTP/1.1
Host: api.openai.com
Content-Type: application/json
Authorization: Bearer sk-proj-h2Kd8vQ1mZ4rT7xN0pLbW3sYcF6gJa9E
Content-Length: 101

{
  "model": "gpt-4o-mini",
  "messages": [
    {"role": "user", "content": "Say hello in one short sentence."}
  ]
}
```

Now every piece of that, one at a time.

**`POST /v1/chat/completions HTTP/1.1`** is the request line. It says we are sending data, to the path `/v1/chat/completions`, using HTTP version 1.1. The `/v1` part is a version prefix the provider chose so they can change the API later without breaking old programs.

**`Host`** names the server. Combined with the path, this is the full URL `https://api.openai.com/v1/chat/completions`.

**`Content-Type: application/json`** tells the server how to read the body. Without it the server does not know whether those bytes are JSON, a web form, or a file upload, and it will usually reject the request. A **header** is one of these `Name: value` lines that carries information about the request rather than the request's actual content.

**`Authorization: Bearer sk-proj-...`** is how the server knows who you are. The word `Bearer` is a scheme name from the HTTP standard and it means "whoever bears this token gets access". The long string after it is your **API key**, which is a secret password the provider gave you. Anyone who has it can spend your money, which is why it lives in an environment variable and never inside your source code. Section 4 goes into that properly.

**`Content-Length`** is how many bytes the body is. Your HTTP library fills this in for you and you will never set it by hand.

Then a blank line, and then the body. The body has two keys here.

**`model`** names which model should answer. One endpoint serves many models, so the server has no way to guess. A provider may host `gpt-4o-mini`, `gpt-4o`, and a dozen others behind the exact same URL, and they differ enormously in cost and quality. This key is how you choose.

**`messages`** is a list, and it is the important one. It is the entire conversation so far, in order, oldest first. The model reads all of it and writes the next message.

Each entry in `messages` is an object with two required keys.

**`role`** says who wrote that message. There are three roles you will meet in this course. `user` is you, the human or the program acting on the human's behalf. `assistant` is the model. `system` is a special instruction block that sets behaviour and rules, and it goes first when it is present. We do not send a system message in this lesson because we want the minimum possible request, and we add one in lesson 02.

The role matters more than it looks. The model was trained on conversations in this format, so it has learned that text marked `user` is a request to respond to and text marked `assistant` is its own previous speech. If you put everything under one role, quality drops noticeably.

**`content`** is the text of that message. In later lessons content can also be a list of parts so you can send images, but a plain string is the common case and it is what we use here.

That is the whole request. Two keys, one of which is a list of two-key objects. There is nothing else hiding in there.

### The response

Here is the full JSON the server sends back.

```json
{
  "id": "chatcmpl-BgY4kR2mQ1sVn8pTt3Lw9dXqZ0aBc",
  "object": "chat.completion",
  "created": 1756684800,
  "model": "gpt-4o-mini-2024-07-18",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello, it is nice to meet you.",
        "refusal": null
      },
      "logprobs": null,
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 14,
    "completion_tokens": 9,
    "total_tokens": 23
  },
  "system_fingerprint": "fp_9c2ea6d1f4"
}
```

Field by field.

**`id`** is a unique identifier for this one call. You do not need it to get your answer, but it is the thing you quote to a provider's support team when something goes wrong, and it is what you log if you want to trace a bad answer back later.

**`object`** names the shape of this JSON. It says `chat.completion` for a normal reply. It says `chat.completion.chunk` for the streaming pieces we will meet in lesson 05. It exists so a program can tell which shape it received without guessing.

**`created`** is the time the reply was made, as a Unix timestamp, meaning the number of seconds since the first of January 1970. The value `1756684800` is a moment in September 2025.

**`model`** is the exact model that answered. Notice it is more specific than what we asked for. We sent `gpt-4o-mini` and got back `gpt-4o-mini-2024-07-18`. Provider aliases point at a dated snapshot, and this field tells you which snapshot you actually got. When answers change quality overnight without you changing any code, this field is where you look.

**`choices`** is a list, and the fact that it is a list surprises everyone the first time. Why would one question have several answers. Because the API lets you ask for several independent completions of the same prompt by sending an extra key called `n`. If you send `"n": 3` you get three entries back, and some workflows use that to generate options and pick the best.

We never send `n`, so the default of one applies, so the list always has exactly one entry, so our code reads `choices[0]`. It is worth knowing why that index is there rather than treating it as noise you have to type.

**`index`** is that choice's position in the list. With one choice it is always `0`.

**`message`** is the actual reply, and look closely at its shape. It has `role` and `content`, exactly the same two keys as the messages we sent. This symmetry is not an accident and it is the reason the whole conversation pattern works. The reply you get back can be appended, unchanged, to the `messages` list you send next time. Lesson 02 is built entirely on this fact.

Here `role` is `assistant`, because the model wrote it, and `content` is the text we want.

**`refusal`** is `null` on a normal answer and holds an explanation string when the model declines to answer. `null` is the JSON word for nothing, and Python turns it into `None`.

**`logprobs`** is `null` unless you asked for probability data about each token chosen. We never do in this course.

**`finish_reason`** tells you why the model stopped writing, and it is far more important than it looks. The common values are these.

- `stop` means the model finished its thought naturally. This is the good case.
- `length` means it hit the maximum number of tokens allowed and got cut off mid sentence. If you ever get a truncated answer, this field is how you prove it was truncation rather than the model being terse.
- `tool_calls` means the model wants to call a function instead of writing text. That value is the entire subject of lesson 03, and it is the moment a chatbot turns into an agent.
- `content_filter` means the provider's safety system stopped the reply.

Our function in this lesson ignores `finish_reason`, which is fine for one hello, and stops being fine the moment we build the agent loop. Remember it is there.

**`usage`** counts the work done. A **token** is the unit models read and write, roughly three quarters of an English word, so "hello" is one token and "unbelievable" might be three. `prompt_tokens` counts what you sent, `completion_tokens` counts what came back, and `total_tokens` is the sum. You are billed per token, and models have a hard limit on how many tokens fit in one request, so this field is both your bill and your budget. Lesson 09 is about managing it.

**`system_fingerprint`** identifies the backend configuration that served you. It changes when the provider updates their serving stack. Most people never look at it.

Now compare the two documents. You sent a list of messages. You got back one message, in the same shape, plus bookkeeping. That is the entire protocol.

## 3. Why we use httpx directly instead of an official SDK

Every provider ships an **SDK**, a software development kit, which is a library that wraps their API in ready made functions. OpenAI's is `openai`, and with it the code for this lesson would be about four lines.

We are not going to use one, and the reason is the point of this chapter.

An SDK's job is to hide the HTTP request. That is a genuinely good thing when you are shipping a product and a bad thing when you are trying to understand what a language model is. If you learn `client.chat.completions.create(...)` without ever seeing the JSON underneath, then the model stays a magic box, and every problem you hit later becomes unexplainable. Why does the model forget things. What is a system prompt really. How does a tool call arrive. Every one of those questions has an obvious answer once you have seen the wire format, and no answer at all if you have not.

This course has a rule. No magic. You should be able to see every layer, all the way down, and be able to rebuild it. Later lessons add streaming, tool calls, retries, and multiple providers, and each one is a change to this same request that you will be able to see and reason about.

So we use `httpx`, which is a general purpose HTTP library for Python. It knows nothing about language models. It sends the request you hand it and gives you the response. That neutrality is exactly what we want, because it means nothing between you and the API is doing anything you did not write.

To be very clear, because this is a real question people worry about. Using the official SDK in your own projects afterwards is a completely reasonable choice, and often the right one. SDKs handle retries, connection pooling, timeouts, and rare edge cases in the response format that you would otherwise have to handle yourself. The argument here is only about learning order. Understand the raw request first, then let a library do it for you if you want. That way when the library misbehaves you can still read the traffic and see why.

We chose `httpx` over the older `requests` library for one forward looking reason. `httpx` supports both normal blocking calls and `async` calls with almost identical code, and it handles streaming responses cleanly, which we need in lesson 05. Starting with it means we never have to switch libraries mid course.

## 4. Why the code reads three environment variables instead of holding a url

Look at the first three lines inside our function.

```python
base_url = os.environ["AGENTPATH_BASE_URL"].rstrip("/")
api_key = os.environ.get("AGENTPATH_API_KEY", "")
model = os.environ["AGENTPATH_MODEL"]
```

An **environment variable** is a named value that lives in your operating system's shell rather than in your file. Your program reads it at runtime through `os.environ`, which behaves like a dictionary of strings.

There are three separate reasons this code does not simply contain a hardcoded URL, and they are all worth understanding.

### Reason one. The API key must never be in the source

If you write your key into `llm.py`, that key gets committed to git, pushed to GitHub, and scraped by bots within minutes. This is not a hypothetical. There are bots doing nothing but watching public commits for strings that look like API keys, and people have woken up to thousands of dollars of usage. An environment variable lives in your shell, not in your repository, so there is nothing to leak.

### Reason two. This course must run against any provider

This is a public course and readers have wildly different situations. Some have an OpenAI key. Some are in a country where that is difficult and use a local model. Some have a company gateway. If the URL were baked into the file, only one group could follow along, and the rest would be editing source code before every lesson.

These three combinations all work with the same unmodified `llm.py`.

```bash
# A hosted provider that requires a key
export AGENTPATH_BASE_URL=https://api.openai.com/v1
export AGENTPATH_API_KEY=sk-proj-your-real-key-here
export AGENTPATH_MODEL=gpt-4o-mini

# Ollama running on your own machine, no key needed at all
export AGENTPATH_BASE_URL=http://localhost:11434/v1
export AGENTPATH_MODEL=llama3.2

# Another hosted provider, same code, different three values
export AGENTPATH_BASE_URL=https://api.groq.com/openai/v1
export AGENTPATH_API_KEY=gsk-your-real-key-here
export AGENTPATH_MODEL=llama-3.3-70b-versatile
```

On Windows PowerShell the same settings look like this.

```powershell
$env:AGENTPATH_BASE_URL = "https://api.openai.com/v1"
$env:AGENTPATH_API_KEY  = "sk-proj-your-real-key-here"
$env:AGENTPATH_MODEL    = "gpt-4o-mini"
```

Notice that the Ollama block has no key line at all. Section 5 explains the two lines of code that make that work.

### Reason three. The tests need to point somewhere else entirely

The continuous integration system that checks this course cannot call a real paid API on every push. It runs a small fake server instead, and it points the lessons at it by setting exactly these three variables. You can see that happening in `ci/run_lessons.py`.

```python
environment["AGENTPATH_BASE_URL"] = f"{base_url}/v1"
environment["AGENTPATH_MODEL"] = "mock"
environment["AGENTPATH_API_KEY"] = "mock-key"
```

The lesson code is not aware that it is being tested and contains no test-only branch. Being able to redirect a program from the outside, without touching it, is the practical payoff of configuration by environment variable, and it is a habit worth forming now.

### Why three variables and not one

We could have used one variable holding the full URL. We split it into three because they change independently. You swap `AGENTPATH_MODEL` constantly while keeping the same provider. You set `AGENTPATH_API_KEY` once and then leave it alone. And the base URL is the only piece the provider actually controls. Keeping the path `/chat/completions` in the code, rather than in the variable, also means you cannot accidentally point the function at an endpoint that returns a different shape of JSON than the code knows how to read.

## 5. Writing llm.py line by line

Here is the complete file. Read it once, then we will go through every line and say where it came from.

```python
"""One function that sends text to a model and returns the text it sends back.

Everything else in this course is built on top of this. There is no library
between you and the API here on purpose. You should be able to see that a
language model is an HTTP endpoint that takes a list of messages and returns
one more message.
"""
import os

import httpx


def ask(prompt):
    """Send one message and return the assistant reply as a string."""
    base_url = os.environ["AGENTPATH_BASE_URL"].rstrip("/")
    api_key = os.environ.get("AGENTPATH_API_KEY", "")
    model = os.environ["AGENTPATH_MODEL"]

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    response = httpx.post(
        f"{base_url}/chat/completions",
        json={"model": model, "messages": [{"role": "user", "content": prompt}]},
        headers=headers,
        timeout=120,
    )
    response.raise_for_status()
    body = response.json()
    return body["choices"][0]["message"]["content"]


if __name__ == "__main__":
    print(ask("Say hello in one short sentence."))
```

Thirty odd lines, and one third of it is explanation. Now the walkthrough.

### The imports

```python
import os

import httpx
```

`os` is in the Python standard library and gives us `os.environ`. `httpx` is the third party library you installed in lesson 00. The blank line between them follows the normal Python convention of separating standard library imports from third party ones, which makes it obvious at a glance what your project depends on from outside.

### The function signature

```python
def ask(prompt):
    """Send one message and return the assistant reply as a string."""
```

One argument, a string, and it returns a string. No classes, no client object to construct, no configuration to pass around. That is deliberate. A function this plain can be read in full in ten seconds, and every later lesson grows it in a way you can diff against this version.

### Reading the configuration

```python
    base_url = os.environ["AGENTPATH_BASE_URL"].rstrip("/")
    api_key = os.environ.get("AGENTPATH_API_KEY", "")
    model = os.environ["AGENTPATH_MODEL"]
```

Notice that two of these use square brackets and one uses `.get`. That difference is intentional and carries meaning.

`os.environ["AGENTPATH_BASE_URL"]` raises `KeyError` if the variable is missing. That is what we want, because there is no sensible default for a URL and a program with no endpoint cannot do anything useful. Failing immediately with a named variable in the error message is far kinder than failing later with something obscure. The same applies to `AGENTPATH_MODEL`.

`os.environ.get("AGENTPATH_API_KEY", "")` returns an empty string when the variable is missing instead of raising. That is also what we want, because a missing key is a completely normal, supported situation. A local model does not need one.

### What rstrip does and why the base url needs it

```python
    base_url = os.environ["AGENTPATH_BASE_URL"].rstrip("/")
```

`rstrip("/")` removes any trailing slash characters from the right hand end of the string. It changes `"https://api.openai.com/v1/"` into `"https://api.openai.com/v1"` and leaves `"https://api.openai.com/v1"` untouched.

Why bother. Because further down we build the URL like this.

```python
f"{base_url}/chat/completions"
```

If somebody sets their variable with a trailing slash, which people do constantly because provider documentation is inconsistent about it, the result would be this.

```text
https://api.openai.com/v1//chat/completions
```

That double slash is a different path as far as the server is concerned. Some servers normalise it and forgive you. Many return a 404 not found, and a few return a confusing 401. The learner then stares at a correct looking URL in their shell and cannot see the problem, because the extra slash is invisible when you skim.

One method call removes an entire category of support question. This is the general shape of good input handling. Accept both forms that reasonable people will type, and normalise once, at the edge, immediately after reading the value.

### Building the headers, and the line that makes local models work

```python
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
```

We start with the one header that is always required. `Content-Type` set to `application/json` tells the server to parse the body as JSON. Leave it out and most servers reject the request outright.

Then the conditional part. In Python an empty string is falsy, so `if api_key` is false exactly when the variable was missing or set to nothing. In that case we never add the `Authorization` header at all.

This tiny `if` is what lets one file work against both a paid cloud API and a model running on your own laptop, so it is worth being precise about why.

Ollama and similar local servers accept requests with no authentication, because the server is running on your own machine and there is nobody to authenticate. But the important part is what happens if you send an `Authorization` header anyway. Several local and self hosted servers do not merely ignore an unexpected header. Some validate the format of the bearer token and reject a malformed one, and sending the literal text `Bearer ` with an empty token after it is malformed. You would get a puzzling 401 unauthorized from a server that does not even have accounts.

Adding the header only when there is something to put in it avoids the whole question. The rule to take away is that an absent header and an empty header are not the same thing, and when a value is optional you should omit the header rather than send it blank.

### Sending the request

```python
    response = httpx.post(
        f"{base_url}/chat/completions",
        json={"model": model, "messages": [{"role": "user", "content": prompt}]},
        headers=headers,
        timeout=120,
    )
```

This one call produces exactly the HTTP request printed in section 2. Compare the two if you have any doubt.

The first argument is the full URL. `httpx.post` means the HTTP method is POST.

The `json=` argument is the interesting one. You hand `httpx` an ordinary Python dictionary and it does two jobs for you. It serialises the dictionary to a JSON string, and it sets `Content-Type` to `application/json` automatically. We set that header ourselves anyway, both because being explicit teaches the reader what is required and because our `headers` dictionary would otherwise be the only header the request carries in the local model case.

Inside `json=` you can see the request body from section 2 rebuilt in Python. `model` comes from the environment. `messages` is a list holding exactly one dictionary, with `role` set to `user` because the human is talking, and `content` set to whatever string the caller passed in.

Note that the list has one element, always. That single fact is the limitation this entire lesson ends on, and it is what lesson 02 removes.

`headers=headers` passes the dictionary we just built.

### The timeout, and why it is not optional

```python
        timeout=120,
```

The timeout is how many seconds `httpx` will wait before giving up and raising an error.

`httpx` has a default timeout of five seconds. That is a sensible default for ordinary web APIs and a bad one for language models. A model generating a long answer routinely takes twenty, forty, sometimes ninety seconds, because it produces the reply one token at a time and only sends it when the whole thing is done. With the default you would see random failures on exactly the requests that were working hardest.

So we raise it to 120 seconds. And the reason we set a number at all, rather than disabling the timeout, is the opposite failure. If the network drops or the server hangs, a request with no timeout waits forever, and your program simply stops with no error and no output. That is much worse to debug than a clear timeout error after two minutes. A generous limit that still exists is the right answer for both problems.

### Checking the status

```python
    response.raise_for_status()
```

Section 7 is entirely about this line, because it deserves the space.

### Reading the reply out of the response

```python
    body = response.json()
    return body["choices"][0]["message"]["content"]
```

`response.json()` parses the JSON text the server sent into Python objects. JSON objects become dictionaries, JSON arrays become lists, `null` becomes `None`. After this line `body` is the exact structure printed in section 2, only now made of Python values.

The last line walks down into it, and every step now has a reason you already know.

- `body["choices"]` is the list of completions. It is a list because the API supports asking for several with `n`.
- `[0]` takes the first one. We never send `n`, so there is exactly one, and index zero is it.
- `["message"]` is the reply object with `role` and `content`, the same shape as the messages we sent.
- `["content"]` is the text itself.

We drop everything else. The token counts, the finish reason, the model snapshot, all discarded, because this lesson's function promises a string and nothing more. Every one of those fields comes back in a later lesson when we actually need it, and `finish_reason` in particular returns in lesson 03.

### The bottom of the file

```python
if __name__ == "__main__":
    print(ask("Say hello in one short sentence."))
```

Python sets the variable `__name__` to the string `"__main__"` when a file is run directly, and to the module's name when the file is imported by another file. So this block runs when you type `python llm.py`, and does not run when another file does `from llm import ask`.

That matters here because `check.py` imports `ask` from this file. Without the guard, importing `llm` would fire off a real API call as a side effect of the import, which costs money and makes the program's behaviour depend on the order of your import statements. This guard is standard Python practice, and this is a good example of why it exists.

## 6. Running it and reading the reply

Set your three environment variables, move into the lesson folder, and run the file.

```bash
cd lessons/01-first-llm-call
python llm.py
```

You will see something like this.

```text
Hello, it is nice to meet you.
```

The exact wording will differ every time, and that is expected rather than a bug. Models sample from a probability distribution, so the same prompt gives different words on different runs. Any short greeting means it worked.

If you want to prove the reply really is coming over the network, unplug your wifi and run it again. You will get a connection error rather than a greeting.

### Running the check script

Every lesson in this course ships a `check.py` that proves the lesson's code works. Here is the whole of this one.

```python
"""Check that lesson 01 works."""
import sys

from llm import ask


def main():
    reply = ask("Say hello.")
    if not isinstance(reply, str) or not reply.strip():
        print(f"FAIL ask returned {reply!r}")
        sys.exit(1)
    print(f"OK the model replied with {reply.strip()[:60]}")


if __name__ == "__main__":
    main()
```

It calls `ask` with a fixed prompt and then asserts two things about the result. `isinstance(reply, str)` checks that you got a string back and not, for example, a dictionary because somebody returned `body["choices"][0]["message"]` by mistake. `reply.strip()` removes surrounding whitespace, and an empty result after stripping means the model returned nothing useful, which a naive check for truthiness would miss because a string of spaces is truthy in Python.

On failure it prints the value using `!r`, which is the `repr` format. That shows quotes and escape characters, so an empty string prints as `''` rather than as a confusing blank space in your terminal. Then `sys.exit(1)` ends the program with a non zero exit code, which is how the continuous integration system learns that something broke.

On success it prints the first sixty characters of the reply, so you see actual model output and not just a green word.

Run it.

```bash
python check.py
```

```text
OK the model replied with Hello, it is nice to meet you.
```

If you are running against the course's mock server instead of a real provider, the output is fixed and looks like this.

```text
OK the model replied with Hello from the mock server.
```

Either output means the lesson is complete.

### When it does not work

A few failures are common enough to name.

If you see `KeyError: 'AGENTPATH_BASE_URL'`, the environment variable is not set in the shell you are actually running in. Environment variables set with `export` apply only to that terminal window, so a new tab starts empty.

If you see a 401 unauthorized, your key is wrong, expired, or has a stray space or quote character in it.

If you see a 404 not found, the base URL is wrong. Check that it ends in `/v1` if your provider expects that, and confirm you did not include `/chat/completions` in the variable, because the code adds that part itself.

If you see a 400 bad request mentioning the model, the value of `AGENTPATH_MODEL` is not a model that provider serves. Model names are exact strings and a version suffix matters.

Section 7 explains why you get to see these clear messages at all.

## 7. What raise_for_status does and why this function would be dangerous without it

```python
    response.raise_for_status()
```

Every HTTP response carries a **status code**, a three digit number saying how it went. Codes in the 200 range mean success. Codes in the 400 range mean your request was wrong in some way, with 401 meaning unauthorized and 404 meaning not found and 429 meaning you are sending too many requests. Codes in the 500 range mean the server itself broke.

Here is the crucial thing to understand. As far as `httpx` is concerned, a 401 is a perfectly successful HTTP transaction. You asked, the server answered, bytes arrived. The library does not raise an exception, because from the network's point of view nothing failed. `httpx.post` returns you a response object exactly as it does for a 200, and it is your job to look at the code.

`raise_for_status()` is that look. It checks the status code, does nothing at all if the code is a success, and raises `httpx.HTTPStatusError` otherwise.

### What actually goes wrong without it

Consider what a failed request contains. When your key is wrong, OpenAI returns a 401 with this body.

```json
{
  "error": {
    "message": "Incorrect API key provided: sk-proj-h2K***9E. You can find your API key at https://platform.openai.com/account/api-keys.",
    "type": "invalid_request_error",
    "param": null,
    "code": "invalid_api_key"
  }
}
```

That is a genuinely helpful message. It tells you precisely what is wrong and where to fix it.

Now delete `raise_for_status()` from the file and imagine the run. The function does not check the code, so it goes straight on to `response.json()`, which succeeds, because that error body is perfectly valid JSON. Then it evaluates `body["choices"]`, and there is no `choices` key in that dictionary, because this is an error document rather than a completion. Python raises this.

```text
Traceback (most recent call last):
  File "llm.py", line 34, in <module>
    print(ask("Say hello in one short sentence."))
          ~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "llm.py", line 30, in ask
    return body["choices"][0]["message"]["content"]
           ~~~~^^^^^^^^^^^
KeyError: 'choices'
```

Look at what that tells a beginner. Nothing true. It points at the last line of the function, which is correct code. It says a key is missing, which suggests the response format is different from what you expected, sending you off to read API documentation that is not wrong. It never mentions authentication, or the status code, or the excellent error message the server sent, which your program received and then threw away.

The real fault, a bad API key, is invisible. That is what makes the version without this line dangerous rather than merely incomplete. It does not fail silently, it fails loudly with a misleading story, and a misleading error costs far more time than a blunt one.

Now here is the same run with the line present.

```text
Traceback (most recent call last):
  File "llm.py", line 35, in <module>
    print(ask("Say hello in one short sentence."))
          ~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "llm.py", line 29, in ask
    response.raise_for_status()
    ~~~~~~~~~~~~~~~~~~~~~~~~~^^
httpx.HTTPStatusError: Client error '401 Unauthorized' for url 'https://api.openai.com/v1/chat/completions'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401
```

The status code is named. The word Unauthorized appears. The URL that failed is printed. You know within one second that this is a credentials problem and not a code problem.

### The general principle

Fail at the boundary, not three steps later. `raise_for_status()` sits exactly where the outside world enters your program and stops anything unexpected from travelling further in. Every line after it is allowed to assume it is holding a real completion, which is why the last line can be a bare chain of subscripts with no defensive checks around it.

That is the trade being made. One line of checking at the edge buys simplicity everywhere downstream. When you get to lesson 04 and the agent loop is calling this function dozens of times inside a `while` loop, a wrong error message would be buried under many iterations, and this line is what keeps it findable.

A 500 from the server behaves the same way, and so does a 429 when you are rate limited. All of them stop here with their real name attached, rather than turning into a `KeyError` about `choices`. In lesson 12 we come back and turn the 429 case into an automatic retry, which is only possible because we can tell 429 apart from every other failure.

## 8. What you cannot do yet

You have a working line to a language model. Now find its limit, because the limit is the reason there is a lesson 02.

Try this.

```python
from llm import ask

print(ask("My name is Ada."))
print(ask("What is my name?"))
```

The output is roughly this.

```text
Nice to meet you, Ada. How can I help you today?
I do not have access to your name. If you tell me, I will use it.
```

It forgot, and it forgot instantly, between two lines of your own program.

This is not a small model being weak and it is not a bug in your code. It is the direct consequence of the request format you read in section 2. Look at what the second call actually sent.

```json
{
  "model": "gpt-4o-mini",
  "messages": [
    {"role": "user", "content": "What is my name?"}
  ]
}
```

There is no trace of Ada anywhere in that document. The server had nothing to remember with.

The important idea, and it is the one that trips up nearly everyone learning this, is that **the API is stateless**. Stateless means the server keeps nothing between calls. It does not know you called it a second ago. It reads the `messages` list you sent, produces one reply, and forgets everything. There is no session on the other end, no conversation stored under your account, nothing.

Which raises the obvious question. Chat websites clearly remember what you said. How.

They do exactly what you are about to do. Every time you press enter, the application sends the entire conversation from the beginning, plus your new message, as one big `messages` list. The memory is not on the server. The memory is a Python list in the client, and the client resends all of it every single time.

That is why `message` in the response has the same `role` and `content` shape as the messages you send. It is designed to be appended straight onto your list and sent back with the next question.

So the shape of lesson 02 is already visible from here. Instead of a function that builds a one element list and throws it away, we keep a list that survives across calls, append the user's message to it, append the model's reply to it, and send the whole thing each time. That single change turns `ask` into a conversation, and it is what makes everything after it possible, because an agent is fundamentally a conversation where some of the turns are tool results rather than human speech.

### What you built in this lesson

- You know that a language model, from a program's point of view, is an HTTP endpoint that takes a list of messages and returns one more message.
- You can read a chat completions request and name every field in it.
- You can read the response and find the reply inside `choices`, and you know why `choices` is a list.
- You have a working `ask` function with no SDK between you and the API.
- You know why the code reads three environment variables, why the base URL gets stripped, why the `Authorization` header is conditional, and why the timeout is 120 seconds rather than absent or default.
- You know what `raise_for_status` protects you from, and can recognise the misleading `KeyError` you would get without it.

Move on to lesson 02, where the model finally remembers what you said.
