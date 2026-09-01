[อ่านภาษาไทย](README.th.md)

# agentpath

Learn how AI agents actually work by building a real one, from a single LLM call
to a full agent harness.

## Who this is for

You can program a little. You have never built anything with a language model,
or you have used one through a framework and never understood what it was doing
underneath. You do not need to know any machine learning. There is no maths in
this course.

## Why this exists

There are many tutorials that show you an agent loop. Almost all of them stop
there. The tools people actually use every day, such as Claude Code and
OpenHands, are not agent loops. They are harnesses, which means an agent loop
surrounded by permission checks, saved sessions, context management, error
recovery and a plugin protocol. Almost nobody teaches you to build that part.

This course goes all the way. You start by sending one HTTP request to a model
and you finish with a harness you could actually use.

Every chapter also has a Thai version, which is rare for material at this depth.

## What you will build

| Part | What it adds | Status |
|------|--------------|--------|
| 1 Foundations | An agent that streams, calls tools, loops until the work is done, and can switch model providers | Available now |
| 2 Real Tools | File reading and editing, running shell commands, searching code, and a small coding agent that works | Available now |
| 3 The Harness | Permissions, saved sessions, context management, token economy, retrieval, error recovery | Available now |
| 4 Advanced | An MCP client, subagents, multi agent patterns, evaluation and model choice | In progress |

## Quickstart

Install uv, which is the Python installer and environment manager this course
uses.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

On Windows use PowerShell instead.

```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Then clone the repository and open the first chapter.

```bash
git clone https://github.com/YOUR-USERNAME/agentpath.git
cd agentpath
```

Now read [lessons/00-setup/README.md](lessons/00-setup/README.md). It walks you
through choosing where your model runs, which can be free and local if you want,
and setting the three environment variables the whole course uses.

## The lessons

| Lesson | What you build |
|--------|----------------|
| [00 setup](lessons/00-setup/) | A working environment and a model you can reach |
| [01 first LLM call](lessons/01-first-llm-call/) | One HTTP request to a model, with nothing hiding the wire |
| [02 conversation loop](lessons/02-conversation-loop/) | A chat that remembers, and the discovery that models remember nothing |
| [03 tool calling](lessons/03-tool-calling/) | The model asks for a function and you decide whether to run it |
| [04 agent loop](lessons/04-agent-loop/) | Your first real agent, looping until the work is done |
| [05 streaming](lessons/05-streaming/) | Answers that appear as they are written, including the hard part where tool arguments arrive in fragments |
| [06 provider abstraction](lessons/06-provider-abstraction/) | One agent loop that works with two completely different APIs |
| [07 file tools](lessons/07-file-tools/) | Reading and editing real files, with one gate deciding what may be touched |
| [08 shell tool](lessons/08-shell-tool/) | Running commands, and asking a person first |
| [09 search tools](lessons/09-search-tools/) | Finding files and text, and why this beats a vector database for code |
| [10 anatomy of a prompt](lessons/10-anatomy-of-a-prompt/) | The three places your words reach the model, including the one everyone forgets |
| [11 mini coding agent](lessons/11-mini-coding-agent/) | Everything wired together into an agent that fixes a real bug |
| [12 permissions](lessons/12-permissions/) | A gate that remembers your answer, so it does not train you to stop reading it |
| [13 sessions](lessons/13-sessions/) | The conversation on disk, which is also the best debugging tool you have |
| [14 context management](lessons/14-context-management/) | Trimming a conversation without stranding a tool result, which is the trap everyone hits |
| [15 token economy](lessons/15-token-economy/) | Why the same conversation costs more every turn, and what actually reduces it |
| [16 retrieval](lessons/16-retrieval/) | Four questions that tell you whether you need RAG at all, and usually you do not |
| [17 errors and retries](lessons/17-errors-and-retries/) | Surviving rate limits, stuck models, and a person who changes their mind |
| [18 the harness](lessons/18-the-harness/) | Everything wired together into a tool you could actually use |

## Using the finished framework

Everything the course builds also ships as a package, so you can install the
finished version and read it as a reference.

```bash
pip install agentpath
```

```bash
export AGENTPATH_BASE_URL=http://localhost:11434/v1
export AGENTPATH_MODEL=qwen3
agentpath chat
```

The command now has three subcommands. `chat` is an interactive session,
`run` does one task and exits, and `resume` carries on from a session you
saved earlier.

## How this repository is laid out

`lessons/` holds one folder per chapter. Each folder is self contained, so you
can open any chapter and run its code without having done the others. The code
is duplicated between chapters on purpose, because a course where chapter four
silently depends on an edit you made in chapter two is a course people abandon.

`src/agentpath/` holds the finished framework, which is the same ideas written
once and properly, with tests.

`ci/` holds the fake model server and the script that runs every chapter check.

`docs/` holds the design document, the implementation plan and the notes on
real provider behaviour.

## Running the checks yourself

Every chapter has a check.py that proves the code you wrote actually works. You
can run all of them at once against a fake model server, which costs nothing and
needs no API key.

```bash
uv pip install -e ".[dev]"
python ci/run_lessons.py
```

This is the same script the project runs in continuous integration, so if it
passes for you it passes for everyone.

## Contributing

Issues and pull requests are welcome. Two rules matter more than the rest.

The course is frozen at 24 chapters. New topic ideas belong in
[docs/v2-ideas.md](docs/v2-ideas.md), not in a new chapter. If you want to add a
chapter you have to argue for removing one.

Prose has a house style. No em dash, no emoji, and no colon in ordinary
sentences. A check in continuous integration enforces the first two.

## License

MIT. See [LICENSE](LICENSE).
