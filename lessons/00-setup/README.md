[อ่านภาษาไทย](README.th.md)

# Lesson 00. Setup

This is the lesson where most people quit. Not because it is hard, but because
setup is the part of any course where nothing works yet and there is no reward
for pushing through. So this chapter is long on purpose. It explains every
command instead of throwing it at you, it tells you what each thing is for, and
section 8 collects every error we have seen a learner hit, with the exact text
those errors print.

Nothing here requires you to know anything about AI. If you can open a terminal
and you have written a little code in some language, you are the target reader.
Take your time. When this lesson ends you will have a machine that can talk to a
language model, and every one of the next 23 lessons will just work.

---

## 1. What you will have at the end of this lesson

Concretely, five things.

- **A modern Python.** Version 3.10 or newer, installed in a way that does not
  fight with any other Python already on your machine.
- **A virtual environment for this course.** A private folder of packages that
  belongs to this project alone, so installing something here can never break
  another project on your computer.
- **One package installed, `httpx`.** That is the entire dependency list for the
  early lessons. `httpx` sends HTTP requests. A language model, from your code's
  point of view, is an HTTP endpoint, so an HTTP client is genuinely all you
  need.
- **A model you can reach.** Either running on your own machine, or hosted by
  somebody else. You will pick one of three options in section 4, and the course
  works with all three.
- **Three environment variables set**, named `AGENTPATH_BASE_URL`,
  `AGENTPATH_API_KEY` and `AGENTPATH_MODEL`, and a green run of `check.py` that
  proves all of the above is true.

That last one is the real deliverable. `check.py` is a script in this folder
whose only job is to answer the question "is this machine ready". When it prints
`You are ready for lesson 01.` you are done, and you never have to think about
setup again.

What you will **not** have yet is an agent, or a single line of agent code. That
starts in lesson 01. This lesson is plumbing.

---

## 2. What an AI agent actually is

A large language model is a program that takes some text and predicts what text
should come next. That is the whole trick. When you send it a conversation, a
list of messages where each message has a role such as user or assistant, it
sends back one more message. It does not remember your last conversation, it
does not run anything, and it cannot look anything up. It reads text and writes
text, once, and then it is finished. Everything else you have heard about these
systems is built on top of that single ability.

An agent is what you get when you put a loop around that. You give the model a
list of functions it is allowed to ask for, such as "read this file" or "add
these two numbers", described in plain words plus the shape of their arguments.
When the model's reply is ordinary text, you print it and stop. When the reply
instead says "please run `add` with a equals 2 and b equals 3", your own code
runs that function, takes the answer, appends it to the conversation as another
message, and sends the whole thing back to the model. Then you go around again.
That is it. An agent is a while loop, a list of messages, and a switch statement
that calls your functions. There is no hidden intelligence in the loop itself.
The model chooses, your code acts, and the result of acting becomes the next
thing the model reads. By lesson 04 you will have written that loop yourself in
about sixty lines, and it will stop feeling mystical.

---

## 3. Installing Python with uv

### What uv is

`uv` is a single executable that does four jobs that used to need four different
tools. It downloads and installs Python versions for you, it creates virtual
environments, it installs packages, and it runs scripts inside the right
environment. It is one file, it needs no Python of its own to bootstrap, and the
same commands work identically on Windows, macOS and Linux.

### Why uv and not pip

`pip` is fine at installing packages and does nothing else. It cannot install
Python itself, which means your very first problem is a problem `pip` cannot
help with. Worse, `pip` operates on whichever Python happens to be first on your
`PATH`, and on Windows in particular it is extremely common to end up with a
`python` command and a `pip` command that point at two different installations.
You then install a package, watch it succeed, run your script, and get
`ModuleNotFoundError` for the thing you just installed. That failure has ended
more beginner projects than any concept in this course. `uv` sidesteps it because
`uv pip install` always targets the environment `uv` itself created, and
`uv run` always uses that same environment.

### Why uv and not conda

`conda` can install Python versions, so it solves the bootstrap problem, but it
is a heavy install, its dependency solving is slow, it introduces a second
package universe alongside the normal Python one, and its default channels carry
licensing terms that some workplaces care about. Conda earns its weight when you
need compiled scientific libraries. This course installs exactly one pure Python
package. Paying the conda tax for that is a bad trade.

To be blunt about the honest downside, `uv` is younger than both of them. If you
already have a working `pip` or `conda` setup and you know it works, you may keep
it. Nothing in this course depends on `uv` beyond this section. The rest of the
lessons only need a Python 3.10 or newer that has `httpx` in it.

### Installing uv on Windows

Open PowerShell and run this.

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

`irm` downloads the install script and `iex` executes it. The
`-ExecutionPolicy ByPass` part exists because Windows refuses to run downloaded
scripts by default, and it applies only to that one command, not to your machine
permanently.

If you would rather not pipe a script into your shell, and that is a reasonable
preference, use the Windows package manager instead.

```powershell
winget install --id=astral-sh.uv -e
```

Close and reopen your terminal after installing, so that the new `PATH` is
picked up.

### Installing uv on macOS

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or with Homebrew if you already use it.

```bash
brew install uv
```

### Installing uv on Linux

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

The script installs into your home directory and does not need `sudo`. It will
tell you if you need to restart your shell.

### Confirming it worked

```bash
uv --version
```

Real output from the machine this lesson was written on.

```text
uv 0.11.7 (9d177269e 2026-04-15 x86_64-pc-windows-msvc)
```

Your version number and platform string will be different. That is fine. Any
output of that shape means `uv` is installed and on your `PATH`. If you instead
see "command not found" or "is not recognized as the name of a cmdlet", close
the terminal, open a new one, and try again. Installers change `PATH`, and a
terminal window only reads `PATH` when it starts.

### Getting a Python and a virtual environment

From the root of the `agentpath` folder you cloned, run these two commands.

```bash
uv python install 3.12
uv venv --python 3.12
```

The first downloads a Python 3.12 that belongs to `uv` and does not disturb any
Python you already have. The second creates a folder named `.venv` inside the
project, which is the virtual environment. A virtual environment is just a
directory holding its own copy of Python and its own `site-packages`, so that
packages installed for this course cannot collide with packages installed for
anything else.

Why 3.12 specifically. The project declares `requires-python = ">=3.10"` in
`pyproject.toml`, and `check.py` refuses to continue below 3.10, because the
course uses the modern type annotation syntax where an optional value is written
`list[dict] | None` rather than with `typing.Optional`. That spelling is a syntax
error on 3.9 and earlier. Anything from 3.10 upward works. 3.12 is a good, widely
available middle choice.

Now activate the environment. Activation edits your current shell so that
`python` means the project's Python.

PowerShell on Windows.

```powershell
.venv\Scripts\Activate.ps1
```

Command Prompt on Windows.

```cmd
.venv\Scripts\activate.bat
```

bash or zsh on macOS and Linux.

```bash
source .venv/bin/activate
```

You will know it worked because your prompt gains a `(agentpath)` or `(.venv)`
prefix.

If activation annoys you, you can skip it entirely for the whole course by
prefixing commands with `uv run`, which finds `.venv` on its own. Both styles are
shown below.

### Installing the one package you need

```bash
uv pip install httpx
```

`httpx` is a modern HTTP client for Python. The course uses it instead of the
standard library's `urllib` because it has a friendlier API and because it
handles streaming responses, which lesson 05 needs.

If you also want to run the project's own tests and the offline mock server
described in section 4, install the whole project in editable mode instead.

```bash
uv pip install -e ".[dev]"
```

Editable mode means the package directory is linked rather than copied, so
edits you make to the source take effect immediately without reinstalling.

---

## 4. Choosing where your model will run

### What you are actually choosing

Every lesson in this course sends an HTTP POST to an address that ends in
`/chat/completions`, carrying a JSON body with a model name and a list of
messages. That request shape was introduced by OpenAI and has since been adopted
by nearly everyone, which is lucky for us, because it means one piece of code can
talk to many different providers. What you are choosing right now is simply which
machine answers that request. Your own computer, somebody's free service, or
somebody's paid service.

There are three honest options. The course works with all three, and you can
switch later by changing environment variables and nothing else. That portability
is the entire reason the course is built this way.

### Option A. Ollama on your own machine

Ollama is a program that downloads open weight models and serves them from your
own computer over HTTP. Install it from the Ollama website, then pull a model and
start the server.

```bash
ollama pull qwen3:8b
ollama serve
```

Ollama exposes an OpenAI compatible endpoint, so the base url you will use is the
local address shown in section 6.

It is free forever, with no signup, no card and no rate limit. Your prompts
never leave your machine, which matters if you plan to point lesson 07's file
tools at real work. It runs offline, so you can do the whole course on a plane.

It is slower, though, often much slower. On a laptop with no discrete GPU, an 8b
model may produce a couple of words per second, which makes the multi step agent
loops of lessons 04 and onward tedious to watch. It uses a lot of disk and
memory, roughly 5 GB on disk for an 8 billion parameter model at common
quantization, and a similar amount of RAM or VRAM while it runs. And the models
you can realistically run at home are meaningfully weaker at following
instructions than the large hosted ones, which is exactly the problem section 5
is about.

### Option B. A free tier cloud service such as Groq or OpenRouter

Groq and OpenRouter both host open weight models and both offer a free tier.
You sign up, create an API key, and point the course at their address.

It is fast, often dramatically faster than local hardware, and it costs nothing.
You get access to larger models than your laptop can hold, which means tool
calling in lesson 03 is far more likely to work on the first try. Setup is two
minutes.

You need an account, which usually means handing over an email address and
sometimes a phone number. Free tiers are rate limited, both per minute and per
day, so a runaway agent loop in lesson 04 can burn your daily quota in a couple
of minutes and leave you locked out until tomorrow. Which models are free
changes over time, so the exact model id you use may need updating. And your
prompts travel to somebody else's servers, which you should weigh before you
point the file reading tools of the later lessons at anything private.

### Option C. A paid API such as OpenAI or Anthropic

These are the commercial services. You add a payment method and pay per token,
where a token is roughly three quarters of an English word, counted across both
what you send and what comes back.

These are the strongest models available and by far the most reliable at tool
calling, which means the lessons behave the way the text says they will. There
are no free tier surprises, latency is low, and uptime is somebody's job.

It costs money. For this course the amount is small, because the lessons send
short prompts, but it is not zero and it is your money. Before you start, go
into the provider's billing settings and set a hard monthly spend limit. Lesson
04 introduces a loop that calls the model repeatedly, and a bug in your own loop
code is the classic way a beginner discovers billing.

One wrinkle worth knowing early. Lessons 00 through 05 speak the OpenAI
compatible request shape described above. OpenAI serves that shape natively.
Anthropic's own API uses a different message format, which this course adds
properly in lesson 06 when we build a provider abstraction. Anthropic does
publish an OpenAI compatible layer, so an Anthropic key can work in lesson 00,
but confirm the current base url in their documentation before you rely on it.
If you want the least friction for your first pass, pick an option that is
natively OpenAI compatible and revisit Anthropic at lesson 06.

### Which to choose

If you are unsure, choose option B. It gets you to a working lesson 03 fastest
and it costs nothing. Move to option A later if privacy or offline use matters to
you, and to option C if you want the smoothest possible ride.

### The offline fallback for testing plumbing only

This repository ships a fake model server used by the project's own tests. It
answers the same request shape with canned replies, needs no key and no network.

```bash
python -m agentpath.testing.mock_server --port 8765
```

It is genuinely useful for proving that your Python, your environment variables
and your code are correct when you suspect the problem is not the model. It is
not a substitute for a real model, because it does not think, it only pretends
convincingly enough to satisfy a test. Use it to debug, not to learn.

---

## 5. Models that can actually call tools

### What tool calling is

Tool calling, also called function calling, is the mechanism from section 2 in
its concrete form. You send the model a list of function descriptions alongside
your messages. Instead of replying with prose, the model may reply with a
structured object naming one of those functions and giving JSON arguments for
it. Your code sees that object, runs the real function, and sends the result
back. Lesson 03 is where you build this, and lesson 04 wraps it in a loop.

The important part is that this is a trained behaviour, not a universal one. The
model has to have been taught to emit that structured object, reliably, in the
exact format the API expects. Plenty of models were not.

### Why small models break lesson 03

Small models, meaning roughly anything below 7 or 8 billion parameters, tend to
fail at this in a specific and confusing way. Asked to call a function, they will
often write a sentence about calling the function, or print something that looks
like JSON inside a paragraph of prose, or call a function that does not exist,
or invent argument names. Your code then receives ordinary text where it expected
a structured call, and lesson 03's check fails.

Read this next sentence carefully, because it is the single most common reason
people abandon a course like this one. **If that happens to you, it is not your
fault and your code is probably correct.** You have hit a limitation of the model,
not a bug in your work. The fix is to change models, not to rewrite your code for
three hours.

### What to use instead

For a local setup with Ollama, use a model at 8 billion parameters or above from
a family that is trained for tool use. `qwen3` and `llama3.1` at the `8b` tag or
larger are both good starting points.

```bash
ollama pull qwen3:8b
```

Ollama records which capabilities each model advertises, and you can read them
directly.

```bash
ollama show qwen3:8b
```

Look for `tools` in the capabilities it lists. A model that does not list `tools`
will not work for lesson 03, no matter how you prompt it.

For a hosted setup, the model list on your provider's dashboard will usually mark
which models support tool or function calling. Pick one that does.

When in doubt, use a hosted model for your first pass through the course. Get
every lesson working once against something strong, so that you know what correct
looks like. Then, if you want, switch `AGENTPATH_MODEL` to a local model and see
where it struggles. Debugging your own code and debugging a weak model at the
same time is a miserable experience, and it is entirely avoidable by doing them
in that order.

---

## 6. The three environment variables

### What an environment variable is

An environment variable is a named piece of text that your operating system hands
to every program you start. Programs read them to find out how they should
behave. Python reads them through `os.environ`, which behaves like a dictionary
of strings.

This course uses exactly three to reach a model. Three more turn up later and
each is introduced where it is needed. `AGENTPATH_AUTO_APPROVE` in lesson 08
for runs with nobody at the keyboard, `AGENTPATH_WORKSPACE` in lesson 08 for
the folder the agent may touch, and `AGENTPATH_HOME` in lesson 13 for where
sessions are saved.

- `AGENTPATH_BASE_URL` is the address of your model service, up to but not
  including `/chat/completions`. In practice it usually ends in `/v1`.
- `AGENTPATH_API_KEY` is your secret key for that service. Leave it unset for a
  local Ollama, which does not check keys. `check.py` only adds an
  `Authorization` header when this variable is non-empty.
- `AGENTPATH_MODEL` is the exact model id string the service expects, such as
  `qwen3:8b` locally, or an id you copy from your provider's model list.

### Why this project refuses to let you hardcode a url or a key

There are two reasons, and they are independent. Both matter.

The practical reason is that the same lesson code has to run against more than
one server. This repository's continuous integration runs `ci/run_lessons.py`,
which starts the fake server from section 4, sets `AGENTPATH_BASE_URL` to that
fake server's address, sets `AGENTPATH_MODEL` to `mock`, turns on
`AGENTPATH_AUTO_APPROVE` so no tool waits for a person, and then executes every
`check.py` in the repository unchanged, the two tracks included. That is how the course proves on every commit that
all 24 lessons still work, on Windows and Linux, without spending a cent or
holding a single credential. If the url were baked into the source, that would be
impossible, and the course would quietly rot. Configuration through the
environment is what makes one piece of code point at a real model when you run it
and at a fake model when a machine runs it.

The security reason is that secrets written into source files escape. They get
committed, and once a key is in git history, deleting the line does not remove
it. Public repositories are scraped continuously for exactly this, and a leaked
key on a paid account is somebody else's bill charged to you. Keeping the key in
your environment means it lives in your shell session or your profile, not in a
file that `git add .` can sweep up. This is not a rule invented for teaching. It
is the normal professional practice.

### Setting the variables in PowerShell on Windows

For the current window only.

```powershell
$env:AGENTPATH_BASE_URL = "http://127.0.0.1:11434/v1"
$env:AGENTPATH_MODEL = "qwen3:8b"
```

To make them survive a reboot, add the same lines to your PowerShell profile.

```powershell
notepad $PROFILE
```

If the file does not exist yet, PowerShell will offer to create it.

### Setting the variables in Command Prompt on Windows

For the current window only.

```cmd
set AGENTPATH_BASE_URL=http://127.0.0.1:11434/v1
set AGENTPATH_MODEL=qwen3:8b
```

To persist them for future windows, use `setx`. Note that `setx` affects new
windows only, so the window you type it in will still not see the value.

```cmd
setx AGENTPATH_BASE_URL "http://127.0.0.1:11434/v1"
setx AGENTPATH_MODEL "qwen3:8b"
```

Do not put quotes inside the value with `set`. Command Prompt would treat them as
part of the text, and your base url would end up with literal quote characters in
it, producing a confusing connection error.

### Setting the variables in bash or zsh on macOS and Linux

For the current shell only.

```bash
export AGENTPATH_BASE_URL="http://127.0.0.1:11434/v1"
export AGENTPATH_MODEL="qwen3:8b"
```

To persist, append the same `export` lines to `~/.bashrc` for bash or `~/.zshrc`
for zsh, then either restart the terminal or reload the file.

```bash
source ~/.zshrc
```

You can also set variables for one command only, which is handy for trying a
different model without disturbing your setup.

```bash
AGENTPATH_MODEL=llama3.1:8b python check.py
```

### Example values for each hosting option

Ollama on your own machine. No key is required, so leave `AGENTPATH_API_KEY`
unset.

```bash
export AGENTPATH_BASE_URL="http://127.0.0.1:11434/v1"
export AGENTPATH_MODEL="qwen3:8b"
```

Groq on the free tier. Create a key in the Groq console and copy the exact model
id from their model list, because ids are retired and replaced over time.

```bash
export AGENTPATH_BASE_URL="https://api.groq.com/openai/v1"
export AGENTPATH_API_KEY="the key you created in the Groq console"
export AGENTPATH_MODEL="llama-3.1-8b-instant"
```

OpenRouter on the free tier. OpenRouter model ids carry the vendor as a prefix,
so they look like the example below. Copy yours from their model list.

```bash
export AGENTPATH_BASE_URL="https://openrouter.ai/api/v1"
export AGENTPATH_API_KEY="the key you created in the OpenRouter dashboard"
export AGENTPATH_MODEL="meta-llama/llama-3.1-8b-instruct"
```

OpenAI as a paid API. Take the model id from the model list on your account,
since the available ids change over time and vary by account.

```bash
export AGENTPATH_BASE_URL="https://api.openai.com/v1"
export AGENTPATH_API_KEY="the key you created in the OpenAI dashboard"
export AGENTPATH_MODEL="the chat model id your account lists"
```

The repository's own fake server, for checking your plumbing offline. Start it in
one terminal, then set these in another.

```bash
export AGENTPATH_BASE_URL="http://127.0.0.1:8765/v1"
export AGENTPATH_API_KEY="mock-key"
export AGENTPATH_MODEL="mock"
```

Two rules that will save you time. First, the base url ends where
`/chat/completions` begins, so it should not itself contain `/chat/completions`.
Second, paste your key with no surrounding quotes, spaces or newlines. A trailing
space in a key produces a 401, and a trailing space is invisible.

---

## 7. Running check.py and reading what it tells you

### What check.py does

`check.py` in this folder is about sixty lines and does five things in order. It
verifies your Python is 3.10 or newer. It imports `httpx` to confirm the one
dependency is installed. It reads `AGENTPATH_BASE_URL` and `AGENTPATH_MODEL` and
fails if either is missing. It then builds a request, adding an
`Authorization: Bearer` header only when `AGENTPATH_API_KEY` is non-empty, and
POSTs a single message saying `Say ready.` to `{base_url}/chat/completions` with
a sixty second timeout. Finally it checks that the HTTP status code was 200.

Notice what it does not do. It does not read the model's answer and it does not
judge it. That is deliberate. This script's job is to test the wire, not the
model. Judging the reply would mix two failures together, and when everything is
new, you want the failures separated. Lesson 01 is where you first look at what
the model actually said.

### Running it

```bash
cd lessons/00-setup
python check.py
```

If you skipped virtual environment activation, use this instead, from the project
root.

```bash
uv run python lessons/00-setup/check.py
```

### The output you are hoping for

This is a real run against the repository's fake server, copied verbatim.

```text
OK Python 3.11
OK httpx is installed
OK AGENTPATH_BASE_URL is http://127.0.0.1:8765/v1
OK AGENTPATH_MODEL is mock
OK the endpoint answered

You are ready for lesson 01.
```

Against a real provider the middle two lines will show your own url and model
instead. Everything else looks the same.

Reading it line by line.

- `OK Python 3.11` means your interpreter is new enough. The number is your
  version, so `3.12` or `3.13` here is equally fine.
- `OK httpx is installed` means the import succeeded, which also proves you are
  running the Python that has your packages in it. This line catches the classic
  `python` and `pip` mismatch described in section 3.
- `OK AGENTPATH_BASE_URL is ...` echoes the url back at you. Read it. Most setup
  failures are visible right here, as a typo, a stray quote, or a missing `/v1`.
- `OK AGENTPATH_MODEL is ...` echoes the model id. Same advice, read it rather
  than skim it.
- `OK the endpoint answered` means a real HTTP 200 came back from a real server.
  Your network path, your key and your model id are all correct.

Every failure prints a single line starting with `FAIL`, then exits with status
1. The script stops at the first problem, so fix them one at a time from the top.

### Trying it against the fake server first

If you want to separate "my Python setup is broken" from "my model setup is
broken", run against the fake server before you run against a real provider. In
one terminal, from the project root, start the server.

```bash
python -m agentpath.testing.mock_server --port 8765
```

In a second terminal, run the check against it.

```bash
cd lessons/00-setup
AGENTPATH_BASE_URL=http://127.0.0.1:8765/v1 AGENTPATH_MODEL=mock python check.py
```

That is exactly the run whose output is shown above. If it passes, your Python,
your environment and the lesson code are all fine, and any remaining problem is
between you and your model provider.

---

## 8. Troubleshooting

Every output below is a real run, not an illustration.

### When the connection is refused

```text
OK Python 3.11
OK httpx is installed
OK AGENTPATH_BASE_URL is http://127.0.0.1:9999/v1
OK AGENTPATH_MODEL is mock
FAIL could not reach http://127.0.0.1:9999/v1. [WinError 10061] No connection could be made because the target machine actively refused it
```

On macOS and Linux the wording is `Connection refused` instead of the Windows
error number, but the meaning is identical. Nothing is listening at that address
and port. The request never reached a server, so this is never a key problem or a
model problem.

Work through these in order.

1. If you are using Ollama, is it actually running. Start it with `ollama serve`
   and leave that terminal open, or check that the Ollama application is running
   in your system tray.
2. Is the port right. Ollama listens on 11434 by default. The course's fake
   server listens on whatever you passed to `--port`.
3. Is the host right. Use `127.0.0.1` rather than `localhost` if you get
   intermittent failures, since `localhost` can resolve to an IPv6 address that
   the server is not listening on.
4. For a hosted provider, this error usually means a network problem, a
   corporate proxy, or a VPN. Confirm you can reach the provider's site in a
   browser from the same machine.

### When you get a 401 unauthorized answer

```text
OK Python 3.11
OK httpx is installed
OK AGENTPATH_BASE_URL is https://api.groq.com/openai/v1
OK AGENTPATH_MODEL is llama-3.1-8b-instant
FAIL https://api.groq.com/openai/v1 answered 401. {"error":{"message":"Invalid API Key","type":"invalid_request_error","code":"invalid_api_key"}}
```

The server was reached, which is good news, and it rejected your credentials. The
body text differs by provider but the number 401 always means the same thing.

1. Is `AGENTPATH_API_KEY` set at all in the window you are running from. Print it
   back with `echo $env:AGENTPATH_API_KEY` in PowerShell or
   `echo $AGENTPATH_API_KEY` in bash. If you used `setx`, remember it only
   affects windows opened afterwards.
2. Check for a trailing space or newline from copy and paste. Retype the last
   character of the key by hand if you are unsure.
3. Make sure the key belongs to the same provider as the base url. A Groq key
   sent to OpenRouter produces exactly this error.
4. Confirm the key still exists and has not been revoked or expired in the
   provider's dashboard.

### When you get a 404 not found answer

```text
OK Python 3.11
OK httpx is installed
OK AGENTPATH_BASE_URL is http://127.0.0.1:11434
OK AGENTPATH_MODEL is mock
FAIL http://127.0.0.1:11434 answered 404. 404 page not found
```

A server answered, but there is nothing at the path we asked for. In practice
this almost always means the base url is wrong in one of two opposite ways.

The common cause is a missing `/v1`. The script appends `/chat/completions` to
whatever you gave it, so with the url above it asked for
`http://127.0.0.1:11434/chat/completions`, which does not exist. The Ollama
compatible endpoint lives under `/v1`, so the url should end with `/v1`.

The opposite cause is an extra path segment. If you pasted the full endpoint from
a provider's documentation, your base url may already contain
`/chat/completions`, and the script then asks for
`.../chat/completions/chat/completions`. Trim it back so it ends at `/v1`.

Set it correctly and the same run succeeds.

```text
OK AGENTPATH_BASE_URL is http://127.0.0.1:8765/v1
OK AGENTPATH_MODEL is mock
OK the endpoint answered
```

A third possibility, less common, is that your provider does not use `/v1` at
all. Copy the base url from their documentation exactly, then delete
`/chat/completions` from the end if it is there.

### When the model is not found

```text
OK Python 3.11
OK httpx is installed
OK AGENTPATH_BASE_URL is http://127.0.0.1:11434/v1
OK AGENTPATH_MODEL is qwen3:8b
FAIL http://127.0.0.1:11434/v1 answered 404. {"error":{"message":"model 'qwen3:8b' not found","type":"not_found_error","param":null,"code":null}}
```

This one is also a 404, which is why it is worth showing next to the previous
case. Read the body, not just the number. Here the server was reached, the path
was right, and the thing it could not find was the model.

For a local Ollama, you have not pulled that model yet, or the tag is spelled
differently. List what you actually have.

```bash
ollama list
```

Then pull the one you want and use its exact name including the tag after the
colon.

```bash
ollama pull qwen3:8b
```

For a hosted provider, the model id is wrong, retired, or not enabled for your
account. Copy the id from the provider's model list rather than from a blog post
or from this README, since hosted model ids change over time. Some providers
return 403 or 400 rather than 404 for a model your account cannot use, so treat
any error that names your model as this same problem.

### When httpx is not installed

```text
OK Python 3.11
FAIL httpx is not installed. Run uv pip install httpx
```

Do what it says, but do it in the environment you are running from. If the
install reports success and this error persists, you are running a different
Python from the one you installed into. Prove it.

```bash
python -c "import sys; print(sys.executable)"
```

If that path does not point inside your project's `.venv`, either activate the
environment as shown in section 3, or run everything through `uv run` instead.

### When an environment variable is not set

```text
OK Python 3.11
OK httpx is installed
FAIL AGENTPATH_BASE_URL is not set
```

The variable is missing from this specific terminal window. Environment variables
set with `$env:` in PowerShell, `set` in Command Prompt, or `export` in bash and
zsh live only in that window and vanish when it closes. Editors with a built in
terminal often start it before you set anything, so a fresh terminal is the first
thing to try. To make the values permanent, use the persistence instructions in
section 6.

### When the request hangs and then times out

`check.py` waits sixty seconds. A local model answering a first request often
has to load several gigabytes of weights from disk into memory, which on a slow
drive can take most of that budget. Run the check a second time. If the second
run is quick, nothing is wrong. If it times out repeatedly, your machine is
probably too small for that model, so try a smaller one for now and read section
5 again about what that costs you in lesson 03.

### When nothing above matches

Reduce the problem. Point at the fake server from section 7. If the check passes
there, your Python and your code are fine and the issue is with your provider or
your credentials. If it fails there too, the issue is on your machine, in your
Python or your environment variables, and the specific `FAIL` line tells you
which.

---

When `check.py` prints `You are ready for lesson 01.`, move on to
`lessons/01-first-llm-call`, where you will write the one small function that
sends your first message to a model and reads its reply.
