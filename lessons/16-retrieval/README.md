[อ่านภาษาไทย](README.th.md)

# Lesson 16. Retrieval, and when not to use it

Lesson 09 promised this chapter. It made the case that a coding agent should
grep rather than embed, and then it said, fairly, that the argument was about
code and did not generalise. It pointed here for the general version.

This is the general version.

Files in this folder.

```text
lessons/16-retrieval/
  retrieval.py    new. the whole retrieval tool, a hundred and twenty seven lines
  tools.py        lesson 15's tools, plus nine lines at the bottom that register it
  agent.py        unchanged from lesson 15
  providers.py    unchanged from lesson 15
  permissions.py  unchanged from lesson 12
  session.py      unchanged from lesson 13
  context.py      unchanged from lesson 14
  usage.py        unchanged from lesson 15
  prompt.py       unchanged from lesson 10
  check.py        five assertions, and one of them is a limitation on purpose
  README.md       this file
```

Seven of the ten Python files are byte for byte what they were in an earlier
lesson. One new file, and nine lines appended to `tools.py`. That is the entire
footprint of adding retrieval to a harness, which is itself part of the argument
this chapter makes.

## 1. The question everyone asks

Should my agent use RAG.

The honest answer, most of the time, is no. Not because retrieval augmented
generation is a bad technique, and not because the people who built it were
wrong. It is a good technique that solved a real problem, and section 7 says so
plainly. The answer is no most of the time because most of the time one of three
simpler things fits better, and the person asking has not checked.

That is the actual failure. Nobody sits down, evaluates a vector database
against a plain text search, and picks the vector database in error. What happens
instead is that "retrieval" and "vector database" have become the same word in
most people's heads, so the first three options are never considered at all. The
question "how do I get my documents in front of the model" arrives already
answered.

So this chapter does two things.

The first is a decision procedure. Four questions, asked in order, and you stop
at the first yes. It takes about two minutes to run and it is the most valuable
part of the chapter. Section 2 is that.

The second is a working retrieval tool, built small, so that you can see there
is no magic in it. Sections 3 to 8 build and defend `search_notes`, which reads
a folder of documents, scores every paragraph against a question, and returns
the best few with the file and line they came from. It works. It is genuinely
useful. And the scoring inside it is about twenty lines of arithmetic that you
will understand completely by the end of section 4.

That second half matters more than it looks. A technique you have not
implemented is a technique you cannot judge, and "retrieval" being an unopened
box is exactly why the four questions get skipped. Once you have written the
scoring yourself, seen it work, and seen precisely where it fails, the phrase
loses its authority and becomes what it always was, which is a way of picking
some paragraphs out of some files.

This chapter is not a case against embeddings. Section 7 is an honest account of
the one thing that our version cannot do and that embeddings do well, and it is
a real gap, not a token concession. The case is against reaching for anything
before you have asked whether you need it.

## 2. Four questions in order, and stop at the first yes

Here is the procedure. Read it once now, then read the four sections that
explain each answer.

| Question | If yes |
| --- | --- |
| Is the data small enough to put in the context window | Put it there. Build nothing. |
| Does the data have structure, and do you know what you are asking | Write a query. SQL, or an API call. |
| Is it text the agent can navigate for itself | Give it glob and grep. That is lesson 09. |
| None of the above | Now vector search earns its place. |

The order is not decorative. Each question is cheaper to answer yes to than the
one below it, in build time, in running cost, in the number of ways it can go
wrong at three in the morning. And the questions are exclusive in practice, which
is why you stop at the first yes rather than collecting opinions from all four.

The most common mistake in this entire subject is jumping to the fourth answer
when one of the first three was available. Every consequence of that mistake is
paid later and by somebody else. Say that back to yourself before you read on,
because the rest of this section is just four elaborations of it.

### Question one. Is the data small enough to put in the context window

If it is, put it in the context window and build nothing at all.

This sounds too obvious to be worth a heading, and it is the most frequently
skipped step in the list. The reason is that the answer has changed and people's
instincts have not. Retrieval augmented generation was designed when a large
context window was four thousand tokens. Four thousand tokens is about three
thousand words, which is six pages. Under that constraint almost nothing fits,
so retrieval was not an optimisation, it was the only way.

Models today routinely take a hundred thousand tokens or more, and several take
a million. A hundred thousand tokens is roughly seventy five thousand words,
which is a three hundred page book. Your product documentation is probably
smaller than that. Your API reference is probably smaller than that. Your
company handbook, your style guide, your entire support macro library, the
schema of your database with comments, almost certainly.

Measure yours before assuming. Here is the whole measurement.

```bash
cat docs/*.md | wc -c
```

```text
  138204
```

Divide by four for a rough token count, which lands near thirty five thousand.
That fits, with room left over, in every model you are likely to be using. So
the correct architecture is to read the files and put them in the system prompt.

Now count what that saves you. No chunking strategy and no argument about chunk
size. No embedding model, and no second provider to hold an API key for. No
vector store to run, back up, or upgrade. No index build step in your deploy. No
staleness, because there is nothing to go stale. No retrieval quality problem,
because nothing was selected, so nothing was left out by mistake. And no class
of bug where the answer was in your documents and the system did not fetch it,
which is the single most maddening failure mode of a retrieval system precisely
because it is silent.

Lesson 15 gives the extra reason to prefer this. Content that does not change
between requests is cacheable, and a prompt cache makes resending a large stable
block extremely cheap. Documentation is the ideal cacheable block. Stable
content first, changing content last, and thirty five thousand tokens of
handbook sitting at the front of every request costs a fraction of its face
value.

The honest caveat is that this stops working, and it stops in two ways rather
than one. The obvious one is that the data grows past the window. The less
obvious one is that models get measurably worse at using a very long context
long before they refuse it. A fact buried in the middle of eighty thousand
tokens is found less reliably than the same fact in eight thousand. So "it fits"
is not quite the test. "It fits with room to spare, and the model is still
finding things in it" is the test, and you check the second half by trying it.

But try it. It costs an afternoon, it either works or it does not, and if it
works you have finished.

### Question two. Does the data have structure, and do you know what you are asking

If the answer is yes, write a query. This is the question that goes wrong most
expensively, so it gets the most space.

Structure means the data already knows what its own parts are. A database table
knows which column is the customer and which is the amount. A JSON API knows
which field is the date. A spreadsheet knows its columns. That structure was put
there by somebody who understood the domain, and it is a working index that
somebody else already paid for.

Now here is the example to keep.

```text
Which customers spent more than five hundred pounds last month
```

That is a query. It is not a similarity search, and the difference is not
stylistic.

Look at what it actually asks for. A comparison, which is amount greater than
five hundred. An aggregation, which is the sum of a customer's orders rather
than any single order. And a filter over a range of dates, which requires knowing
what today is and what the boundaries of last month were. Not one of those three
operations is a text operation. There is no wording of that question that makes
it about which sentences resemble which other sentences.

It is fourteen words of SQL.

```sql
SELECT customer_id, SUM(amount) AS total
FROM orders
WHERE created_at >= '2026-08-01' AND created_at < '2026-09-01'
GROUP BY customer_id
HAVING SUM(amount) > 500;
```

That returns the right answer. Exactly the right answer, every row that
qualifies and no row that does not, computed from the data as it stands at this
instant. It is auditable, in that somebody can read the query and confirm it
means what the question meant. It is testable. It costs a few milliseconds. And
it is provably complete, which is a property no similarity search has ever had.

Now watch what a vector search does with the same question, because this is the
part worth understanding properly.

You embed the sentence "which customers spent more than five hundred pounds last
month". You get back the chunks whose embeddings sit nearest to it. Those chunks
will be about customers, about spending, about amounts, quite possibly about
thresholds and about months. They will be topically excellent. And they will be
the wrong rows, because nearness in embedding space is a measure of what a piece
of text is about, and the question is not about a topic. Five hundred and four
hundred and eighty are close in meaning and far apart in fact. A vector index has
no arithmetic in it. It cannot add two numbers together, so it cannot aggregate.
It has no idea which month contains today.

And here is why this is worse than a plain failure. It does not return nothing.
It returns five paragraphs about customer spending, the model reads them, and
the model writes you a confident paragraph naming three customers. Some of those
customers may even be right. Nothing in the output is marked as a guess. You have
built a machine that produces plausible financial answers by resemblance, and the
only way to catch it is to already know the answer.

So the test for question two is two clauses and you need both. Does the data
have structure, and do you know what you are asking. If you know what you are
asking, asking it exactly is always better than asking something that rhymes
with it.

There is a version of this that is genuinely useful and it is worth naming so
you do not confuse the two. Give the agent a tool that runs a parameterised query
and let the model choose the parameters. The model turns a sentence into
arguments, and the database does the part databases are good at. That is a
different architecture from retrieval and it is usually the right one for
anything with a schema. What is not right is retrieving text about the data and
hoping the model can compute over it.

### Question three. Is it text the agent can navigate for itself

If the corpus is code, or anything else where the words in the question are the
same words that appear in the target, give the agent glob and grep and stop.

Lesson 09 made this argument in full and there is no reason to repeat it. The
short version is that code has already been indexed by hand, by every developer
who chose a name, and that the index is the names themselves. `parse_arguments`
is called `parse_arguments` in its definition and at every call site, so
searching for that string finds all of them and nothing else. Programming
languages do not have synonyms, and the compiler enforces that far more strictly
than any embedding model approximates it.

Two things from lesson 09 are worth carrying into this chapter specifically.

The first is that an index over code goes stale the instant the agent edits a
file, and the agent's whole purpose is to edit files. Grep has no index, so it
cannot be stale. It reads the file the agent wrote a millisecond ago.

The second is the one that generalises furthest. A similarity search is a single
shot. You embed, you get ten chunks, that is your answer. The agent loop is not
a single shot. It searches, reads what came back, and searches again with what
it learned, and each step is chosen because of what the previous step returned.
Two crude tools inside a loop that can refine beat one clever tool that gets one
attempt. Hold that thought, because section 8 is about what it means for the
thing we are building here.

Question three is broader than code, and this is where people stop too early.
Configuration files, logs, structured Markdown with predictable headings, CSV
exports, anything with identifiers or error codes or field names in it. If a
person answering this question would reach for control F, the agent should reach
for grep.

### Question four. None of the above

Now, and only now, vector search earns its place.

You are here because the corpus is too large for the window, has no structure to
query, and is written in words that do not match the words in the questions.
Support tickets written by thousands of different customers. Research papers.
Years of internal wiki pages written by people who each invented their own
vocabulary. Meeting transcripts. Policy documents that a person asks about using
words the policy never uses.

Lesson 09 listed the three properties that have to hold together, and they still
do. Large unstructured prose, questions about meaning rather than words, and a
corpus that changes slowly enough that a nightly rebuild is acceptable.

If that is your situation, build the vector index. Do not let this chapter talk
you out of it. That is a real problem with a good solution and the solution is
the one everybody is talking about.

The rest of this chapter builds something simpler than that, for the case which
is more common than either extreme. The corpus is prose rather than code, so
question three's answer is not quite right. It is not large enough or synonym
heavy enough to justify an embedding pipeline, so question four's answer is too
much. That middle is where most people's actual documents live, and it is well
served by about twenty lines of scoring.

## 3. What retrieval actually is, with the magic removed

Strip the vocabulary away and retrieval is one sentence.

You have some pieces of text and a question. You give every piece a score
according to how likely it is to answer the question. You return the few with the
highest scores.

That is all of it. Chunking is the part where you decide what a piece is.
Embedding is one particular way of computing the score. A vector database is a
way of computing that score quickly when there are ten million pieces. All three
are implementations of a detail. The shape is score and sort.

Here is `search_notes`, complete.

```python
def search_notes(question, limit=TOP_RESULTS, root=None, pattern=DEFAULT_PATTERN):
    root = Path(root or os.environ.get("AGENTPATH_WORKSPACE", ".")).resolve()
    index = build_index(root, pattern)
    if not index:
        return f"there are no {pattern} documents to search"

    appearances = {}
    for entry in index:
        for word in entry["words"]:
            appearances[word] = appearances.get(word, 0) + 1
    rarity = {word: math.log(len(index) / count) for word, count in appearances.items()}

    question_words = set(words(question))
    ranked = sorted(index, key=lambda entry: score(question_words, entry, rarity), reverse=True)
    best = [entry for entry in ranked if score(question_words, entry, rarity) > 0]
    if not best:
        return f"nothing in the documents mentions any of the words in {question!r}"
    _, _, truncate = _from_tools()
    parts = [f"{entry['source']}\n{entry['text']}" for entry in best[: int(limit)]]
    return truncate("\n\n".join(parts))
```

Read the middle three statements and you have read the technique. Count how many
passages each word appears in. Turn that count into a weight. Sort the passages
by the sum of the weights of the words they share with the question.

The scoring function itself is one line.

```python
def score(question_words, entry, rarity):
    return sum(rarity.get(word, 0.0) for word in question_words & entry["words"])
```

`question_words & entry["words"]` is a set intersection, which is the words the
question and the passage have in common. Sum their weights. That is the score.

Two smaller decisions in that function are worth naming now and defending later.

The filter `if score(...) > 0` throws away every passage that shares no words
with the question at all. Without it, a search would always return five
passages, because sorting a list always produces a top five even when every
score is zero. Returning five arbitrary paragraphs to a model that asked a
question the corpus cannot answer is much worse than returning a sentence saying
so, and section 9 has the check that proves this behaviour is there on purpose.

And `truncate` is lesson 07's cap, applied here for lesson 07's reason. Every
tool result goes into the conversation and is resent on every later request.
There is no way to take it back. A tool that can return an unbounded amount of
text is a context window problem waiting for the right question.

Now the two remaining functions. `words` is the tokeniser.

```python
WORD = re.compile(r"[A-Za-z0-9_]+")


def words(text):
    return WORD.findall(text.lower())
```

Lowercase everything and take runs of letters, digits and underscores.
`Refunds,` becomes `refunds`. Punctuation disappears, so a word at the end of a
sentence matches the same word in the middle of one. Underscores are kept
because identifiers such as `issue_refund` should stay one token rather than
becoming two.

Two of those borrowed names arrive through a small function rather than a
plain import at the top of the file.

```python
def _from_tools():
    import tools

    return tools.SKIP_DIRECTORIES, tools.looks_like_a_secret, tools.truncate
```

The import sits inside the function on purpose. `tools.py` imports
`retrieval.py` so it can register the tool, and if `retrieval.py` imported
`tools.py` back at the top of the file, each one would need the other to
finish loading before it could finish loading itself. Python fails on
whichever you ask for first. Putting the import inside the function delays it
until the moment it is called, which is long after both files have loaded.
Borrowing rather than copying is the entire argument of this section, so the
borrowing has to survive the order the files load in.

And `build_index` reads the files.

```python
def build_index(root, pattern=DEFAULT_PATTERN):
    """Read the documents once and remember their words."""
    skip, is_secret, _ = _from_tools()
    index = []
    for path in sorted(root.rglob(pattern)):
        if any(part in skip for part in path.relative_to(root).parts):
            continue
        if is_secret(path.name):
            continue
        for line_number, text in passages_in(path):
            index.append(
                {
                    "source": f"{path.relative_to(root).as_posix()}:{line_number}",
                    "text": text,
                    "words": set(words(text)),
                }
            )
    return index
```

Three things in there are reused rather than invented, and two of them arrive
through `_from_tools` under the local names `skip` and `is_secret`.
`SKIP_DIRECTORIES` is lesson 07's set, so retrieval does not index your virtual
environment. `looks_like_a_secret` is lesson 07's helper, and it is here because lesson 09
found the hole where a search tool walked the tree itself and bypassed the
credential refusal that `read_file` enforced. A rule enforced at one entry point
is not enforced. `as_posix()` is lesson 09's line, so a source on Windows reads
`docs/refunds.md` rather than `docs\refunds.md`.

Notice what is not there. There is no persistent index, no cache file, no
database. `build_index` runs on every call and reads the documents fresh.

That is a deliberate trade and it is worth being precise about the cost. Here is
the whole of this course's lesson folder, indexed.

```text
passages 11828 built in 0.17s
```

Nearly twelve thousand paragraphs across twenty four chapters of Markdown, in
both languages the course ships in, read from disk and tokenised in under a
fifth of a second. At that price, keeping an index around to avoid rebuilding it
would be an optimisation that buys a fifth of a second and costs you the entire
category of bug where the index disagrees with the disk. The agent edits files.
The index is never stale because there is no index.

That trade reverses somewhere. A million documents will not read in a fifth of a
second and you will need to persist something. Notice that this is the same
staleness problem section 7 lists as a cost of embeddings, arriving from a
completely different direction, which tells you it is a property of keeping a
derived copy of your data rather than a property of vectors.

## 4. Scoring by rarity

Here is the one idea in the scoring, in plain language.

A word that appears in every passage cannot tell them apart, so it should count
for nothing. A word that appears in exactly one passage points straight at it,
so it should count for a lot.

That is the whole thing. It has a name, inverse document frequency, and the name
is much more intimidating than the idea. Two lines implement it.

```python
    appearances = {}
    for entry in index:
        for word in entry["words"]:
            appearances[word] = appearances.get(word, 0) + 1
    rarity = {word: math.log(len(index) / count) for word, count in appearances.items()}
```

Count the passages each word appears in. Divide the total number of passages by
that count, and take the logarithm. A word in every passage gives a ratio of one
and a logarithm of zero, so it contributes nothing. A word in one passage out of
a thousand gives a ratio of a thousand, and a much larger weight.

Take the check's fixture, which is three small Markdown files. Here is the index
it produces, eight passages.

```text
refunds.md:1  | # Refunds
refunds.md:3  | Customers may request a refund within thirty days of purchase.
refunds.md:5  | Refunds are paid back to the original card.
shipping.md:1 | # Shipping
shipping.md:3 | Orders are dispatched within two working days.
shipping.md:5 | Delivery takes three to five days.
team.md:1     | # The team
team.md:3     | The team works remotely across three time zones.
```

And here are the weights, computed from those eight.

```text
the          appears in 3 of 8  rarity 0.981
days         appears in 3 of 8  rarity 0.981
refunds      appears in 2 of 8  rarity 1.386
three        appears in 2 of 8  rarity 1.386
team         appears in 2 of 8  rarity 1.386
refund       appears in 1 of 8  rarity 2.079
dispatched   appears in 1 of 8  rarity 2.079
long         appears in 0 of 8  rarity 0.000
```

Read the column of numbers. `the` is worth less than half of `refund`, and
nobody wrote a list of stopwords to make that happen. It fell out of counting.
That is the property worth appreciating. The weights adapt to whatever corpus
you point this at, so a corpus of legal documents will automatically discount
`agreement` and `party` without anybody deciding they were common.

The last row is the missing word case. `rarity.get(word, 0.0)` returns zero for a
word that appears nowhere, so a question containing `long` is not penalised or
crashed by it, the word simply contributes nothing.

Now watch a real search. The question is `how long to ask for a refund`, which
uses none of the exact phrasing of any document.

```text
question words: ['a', 'ask', 'for', 'how', 'long', 'refund', 'to']

4.159  refunds.md:3   overlap=['a', 'refund']
1.386  refunds.md:5   overlap=['to']
1.386  shipping.md:5  overlap=['to']
0.000  refunds.md:1   overlap=[]
0.000  shipping.md:3  overlap=[]
0.000  team.md:3      overlap=[]
```

And here is what the tool returns.

```text
refunds.md:3
Customers may request a refund within thirty days of purchase.

refunds.md:5
Refunds are paid back to the original card.

shipping.md:5
Delivery takes three to five days.
```

Three passages, not five, because only three scored above zero and the filter
dropped the rest. The first one is the answer. Four of the seven question words
were noise, `how` and `long` and `ask` and `for` contributed nothing at all, and
the one word that carried meaning found the right sentence anyway.

Now be honest about the second and third results, because they are noise. Both
scored 1.386 on the word `to`. Both are irrelevant.

The reason is instructive. In an eight passage corpus, `to` appears twice, which
makes it look rare. In a real corpus of ten thousand passages, `to` appears in
nearly all of them and its weight collapses to almost nothing, which is exactly
what you want. The same is true of `a`, which contributed half of the winning
score here because it happened to appear in exactly one of eight passages. The
rarity statistic is doing the right arithmetic on data too thin to support it.

That is worth stating rather than hiding, for two reasons. It is the honest
behaviour of the code in this folder and you would find it in ten minutes. And
it is a general property of every statistical retrieval method including the
expensive ones. They are all estimates over a corpus, they are all noisier on a
small corpus, and none of them tells you which of its own results are noise.
Section 6 is about the one thing that makes that survivable.

This single idea, term overlap weighted by rarity, is most of what classical
search engines do. Add a correction for passage length, so a long passage does
not win merely by containing more words, and a saturation term, so the tenth
occurrence of a word counts less than the second, and you have BM25, which is
the algorithm sitting under Lucene, Elasticsearch and a large fraction of the
search boxes you have ever typed into. Those two refinements are worth having
and they are refinements. The engine is the two lines above.

## 5. Why paragraphs rather than fixed size chunks

`build_index` gets its pieces from here.

```python
def passages_in(path):
    """Split a file into paragraphs, keeping the line each one starts on."""
    passages = []
    line_number = 1
    for block in path.read_text(encoding="utf-8", errors="replace").split("\n\n"):
        if block.strip():
            passages.append((line_number, block.strip()))
        line_number += block.count("\n") + 2
    return passages
```

Split on the blank line. Keep the line number each block starts on, which is
what makes the source in section 6 possible. Skip blocks that are empty after
stripping, which is what happens when a file has two blank lines in a row.

The standard alternative, and the one nearly every tutorial reaches for, is to
cut every N characters. Four hundred, five hundred, a thousand, usually with an
overlap between neighbours so that a sentence spanning a boundary is not
entirely lost.

The argument for a paragraph is one sentence. A paragraph is a unit that a
person wrote on purpose. Somebody decided where it started and where it ended,
and they decided that on the basis of it being one idea. You are getting a
segmentation for free that was performed by a human being who understood the
content, and it is better than anything a character counter will produce.

The argument against a fixed size cut is best made by doing it. Here is the
docstring at the top of `retrieval.py`, which is 1066 characters of ordinary
prose, cut every four hundred characters.

```text
--- chunk starting at 0
Retrieval, built the small way, so you can see what it actually is.

Retrieval means finding the parts of a body of text that are most likely to
answer a question. People often assume that requires embeddings and a vector
database. It does not. It requires a way to score a piece of text against a
question, and the scoring below is about twenty lines.

The scoring is term overlap weighted by how ra

--- chunk starting at 400
re each word is. A word that
appears in every document tells you nothing about which document you want,
so it counts for almost nothing. A word that appears in one document is a
strong signal, so it counts for a lot. That single idea is most of what
classical search engines do, and it is enough to be genuinely useful.

What this cannot do is match meaning when the words differ. A question about
re

--- chunk starting at 800
funds will not find a document that only says money back, and a question
about dispatch will not find a document that says dispatched. That is
exactly the gap embeddings fill, and it is the honest reason to reach for
them. It is not a reason to reach for them first.
```

Look at what happened at the two boundaries, because both are worse than they
first appear.

The first chunk ends with `weighted by how ra`. The second begins with
`re each word is`. The word `rare` has been split into `ra` and `re`, and the
sentence that explains the entire technique now exists in neither chunk. If you
retrieve the first chunk you get a promise with no explanation. If you retrieve
the second you get an explanation whose subject is missing.

The second boundary is the one that should make you wince. The second chunk ends
`A question about re` and the third begins `funds will not find a document`. The
word `refunds` has been cut in half. Which means the chunk that is entirely about
refunds does not contain the word `refund` anywhere in it, and no keyword search
will ever find it. It has produced two tokens, `re` and `funds`, that mean
nothing and match nothing.

That is not bad luck. It is the guaranteed behaviour of a rule that knows
nothing about the text it is cutting, applied a few thousand times. Some
percentage of your boundaries land inside a word, more of them land inside a
sentence, and the results read as nonsense.

Now the fair account, because paragraphs are not free.

A paragraph is not a fixed size, so passages vary from one line to several
hundred words. Long passages get an advantage in the scoring, because more words
means more chances to overlap with the question, and this version has no length
correction. That is the first of the two refinements section 4 said turns this
into BM25, and it is the more important of them.

Some documents have no paragraph structure at all. A minified file, a CSV, a
transcript exported as one enormous block. Splitting on the blank line gives you
one passage containing the whole file, which is useless. In practice you handle
that by falling back to a size cut when a paragraph exceeds some length, which
is a reasonable hybrid and is left as an exercise.

And headings become their own passages, which is a genuine mixed result. In
section 4's index, `# Refunds` is a passage on its own containing one word. Run
a real query over this course and the top hit is a heading.

```text
09-search-tools/README.md:778
## 7. Why we cap the number of results
```

That is an excellent pointer and a poor answer, and it is only excellent because
of the next section.

## 6. Why every result carries its source

Every passage comes back with the file and the line it came from, produced in
`build_index`.

```python
"source": f"{path.relative_to(root).as_posix()}:{line_number}",
```

And rendered in front of every result.

```python
    parts = [f"{entry['source']}\n{entry['text']}" for entry in best[: int(limit)]]
```

This is four words of format string and it is the difference between a tool that
works and a tool that is dangerous.

A passage with no source is nearly useless, for two separate reasons that fail
in two different directions.

**The agent cannot go and read more.** Retrieval returns a fragment by
construction. That fragment frequently answers half the question, or answers it
with a qualification that lives in the next paragraph. With a source, the model
has somewhere to go, and it already has the tools to go there. Look at the
heading result again.

```text
09-search-tools/README.md:778
## 7. Why we cap the number of results
```

On its own that is a heading with no content. With the source attached, the next
tool call is obvious and the agent makes it without being told. Read that file.
Grep near it. The retrieval result was not the answer, it was a pointer, and a
pointer without an address is not a pointer.

This is the property lesson 09 argued for when it explained why `grep_files`
returns paths and line numbers rather than a summary. The output of one tool is
the argument of the next, with no transformation in between. Return a nicely
formatted digest with no paths in it and the chain breaks at the first link, and
the agent has to either accept the fragment or start over.

**A person cannot check it.** This is the more serious one.

The whole reason retrieval exists is that a model's own recall is not
trustworthy for facts about your particular documents. So you fetch the
documents. But if the model then writes a paragraph that blends five retrieved
fragments into fluent prose, and nothing anywhere records where those fragments
came from, you have moved the trust problem rather than solved it. The output is
now confident, specific and unverifiable, which is a worse position than an
obvious guess, because an obvious guess gets checked.

With a source on every passage, the chain is intact. The model was given
`refunds.md:3`. You can open `refunds.md`, go to line 3, and read what it
actually says. When the answer is wrong you can find out whether the retrieval
fetched the wrong passage or the model misread the right one, and those are
different bugs with different fixes.

Section 4's noise makes this concrete. Two of the three results were irrelevant,
matched on the word `to`. A reader who can see `shipping.md:5` on the front of a
passage about delivery times can dismiss it in a second. Strip the sources and
those three passages arrive as one undifferentiated block of context with no
handle on any of them.

The check asserts this, and the phrasing of the failure message is the argument
in one line.

```python
    if ":" not in answer.splitlines()[0]:
        fail("a passage came back with no source, so the agent cannot go and read more")
```

The general rule is worth more than the tool. Anything that fetches text on
behalf of a model should return where the text came from, every time, in a form
the next tool accepts. Cite or do not fetch.

## 7. What this genuinely cannot do, and what would fix it

Now the honest part, and it is a real limitation rather than a token one.

This matches words. It does not match meaning. Two words that mean the same thing
are, to this code, two unrelated tokens.

Here is the failure, run against the check's fixture.

```text
--- search_notes('dispatch')
nothing in the documents mentions any of the words in 'dispatch'

--- search_notes('dispatched')
shipping.md:3
Orders are dispatched within two working days.
```

The document says `dispatched`. You asked about `dispatch`. Two characters of
difference, obviously the same concept to any reader, and the tool returns
nothing. Not a worse answer. Nothing.

The same failure with different words, and this one is worse because it cannot
be fixed by trimming letters. A question about refunds will not find a document
that says money back. A question about how to cancel will not find a policy that
uses the word terminate. A question about time off will not find the section
headed annual leave. In every case the document contains the answer, the user
asked a perfectly reasonable question, and the system says nothing was found.

There are two things to say about that and the order matters.

The first is that saying nothing is the correct behaviour given what the code
knows. It found no overlap, so it reports no overlap, rather than returning the
five least bad passages and letting the model construct an answer from them. A
retrieval system that always returns something is a system that has removed your
ability to tell the difference between an answer and a shrug.

The second is that this is exactly, precisely the gap embeddings fill, and it is
the real reason to reach for them.

An embedding model turns a piece of text into a few hundred or a few thousand
numbers, arranged so that text with similar meaning ends up close together in
that space regardless of the words used. `dispatched` and `dispatch` land in
almost the same place. So do `refund` and `money back`. So do `terminate your
subscription` and `how do I cancel`. That is not a marginal improvement over
word matching, it is a different capability, and where the synonym problem is
your actual problem there is no amount of cleverness with word counts that
substitutes for it.

Notice how narrow that claim is, though, and how exactly it lines up with
question four. Embeddings are the answer to one specific problem, which is that
the words in the question are not the words in the document. If your users ask
in your documentation's own vocabulary, or your corpus is code, or the question
is a query over structured data, this capability is not the thing standing
between you and a working system.

### What embeddings cost

Be fair in both directions, so here is the bill.

**An index, and the index goes stale.** You must embed every chunk in advance
and store the vectors somewhere. The moment a document changes, its vectors are
wrong, and nothing tells you. There is no error and no warning. A stale index
returns confidently outdated passages, and the failure surfaces days later as a
support complaint. So you need a rebuild strategy, which means either rebuilding
everything on a schedule and accepting a staleness window, or tracking which
chunks came from which version of which file and rebuilding incrementally, which
is a cache invalidation problem. Compare the fifth of a second in section 3.

**A model to run.** Something has to turn text into vectors, at index time and
again on every single query. Call an API and you have a second provider, a
second key, a second rate limit, a second thing that can be down, and a per
query cost and latency on the critical path of every search. Run it locally and
you have a model file to ship, a runtime to install, and hardware requirements
that your smallest deployment target may not meet. Either way, a dependency the
version in this folder does not have. `retrieval.py` imports `math`, `os`, `re`
and `pathlib`.

**A pipeline to maintain.** This is the cost people discover last. The
embedding model has a version, and re-embedding with a new version means
re-embedding everything, because vectors from two versions are not comparable.
The chunking strategy has parameters that someone has to own. The vector store
is another service to deploy, monitor, back up and upgrade. And retrieval
quality becomes a thing that needs evaluating, which needs a test set of
questions with known answers, which somebody has to write and keep current.

None of that is an argument against paying it. It is an argument for knowing the
price before you agree to it, and for checking that the thing you are buying is
the thing you needed. If your problem is that users ask about refunds and your
documents say money back, this is money well spent. If your problem is that you
never checked whether the documents fit in the context window, it is not.

### The middle ground

Lesson 09 mentioned hybrid retrieval in one line and it deserves two here,
because it is what serious systems actually do.

Run both. Take the keyword results and the vector results, merge the two ranked
lists, and return the combination. Keyword search contributes exactness, and it
is unbeatable on identifiers, error codes, product names and anything else with
one correct spelling. Vector search contributes the synonym handling. Merged,
they beat either one alone, consistently enough that it is close to standard
practice.

And notice the direction that pushes you. If you end up needing embeddings, you
will most likely also want the word scoring in this folder. Building this first
is not a detour on the way to the real thing. It is the half of the real thing
that most people skip.

## 8. Retrieval is a tool, not a system

Here is the whole of the wiring that adds retrieval to the harness, at the
bottom of `tools.py`.

```python
# Lesson 16 adds retrieval. Everything above is unchanged from lesson 15.

from retrieval import SCHEMA as RETRIEVAL_SCHEMA  # noqa: E402
from retrieval import search_notes  # noqa: E402

SCHEMAS.append(RETRIEVAL_SCHEMA)
FUNCTIONS['search_notes'] = search_notes
```

Nine lines including the blanks, and `agent.py` did not change. That is lesson
11's seam holding for the eighth tool, which is worth noticing but is not the
point of this section.

The point is what those nine lines imply about the architecture, and it is the
thing most retrieval systems get wrong.

In a conventional retrieval augmented generation setup, retrieval is not a tool.
It is a step. Every question goes through the same pipeline. Embed the user's
question, fetch the top chunks, paste them into the prompt, call the model. The
retrieval happens before the model is consulted, on every request, whether or not
it was needed.

Consider what that does. A user says "thanks, that worked". The pipeline
dutifully embeds it, retrieves five paragraphs of documentation that are
statistically nearest to a thank you, and pastes them into the prompt. The user
asks something that needs three lookups in sequence, where the second question is
only apparent once the first is answered, and the pipeline retrieves once, from
the original wording, and has no mechanism for a second attempt. This is lesson
09's single shot problem showing up as an architectural property rather than as a
property of vectors.

Here, retrieval is a tool. The model decides whether to call it, decides what to
search for, reads the result, and decides what to do next. It can skip it
entirely. It can call it, get the noisy result from section 4, notice that two of
three passages are irrelevant, and call `read_file` on the source of the one that
is not. It can call it twice with different wording. It can grep instead.

That is the loop from lesson 04 doing the job it has always done, and it means the
question "which passages are relevant" is answered by something that can reason
about the answer, rather than by a cosine distance computed before anybody read
anything.

The cost of that design is that the model has to know when to use it. Which makes
the tool description carry real weight. Here it is, verbatim.

```python
SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_notes",
        "description": (
            "Search the project documents for passages related to a question, and "
            "return them with the file and line they came from. Use this for prose. "
            "For code, grep_files is usually better because names are exact."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "What you want to know"},
                "limit": {"type": "integer", "description": "How many passages to return"},
            },
            "required": ["question"],
        },
    },
}
```

Three sentences, and the third one is the interesting one.

```text
For code, grep_files is usually better because names are exact.
```

That is a tool description telling the model to prefer a different tool. It is
worth sitting with how unusual that is. Almost every tool description ever
written is an advertisement for its own tool, and the result is an agent holding
eight tools each of which claims to be the right one.

The reason it belongs here is that the agent now has two overlapping ways to
search text, and overlapping tools are where models get confused. `grep_files`
and `search_notes` both take something like a query and both return something
like matching text with a file and a line. Without guidance the model will pick
between them by vibe, and the vibe of "search the project documents for passages
related to a question" is very appealing when you are looking for a function.

So the description does three things in three sentences. It says what the tool
does. It says what it is for, which is prose. And it names the specific
alternative and gives the reason to prefer it, so that the model can apply the
rule to a case the sentence did not anticipate.

`because names are exact` is doing more work than `use grep_files instead for
code` would. A rule with its reason attached generalises. A model that
understands why exactness matters will also reach for grep on an error code, a
configuration key or a product SKU, none of which are code and all of which have
one correct spelling. This is lesson 10's argument about tool descriptions,
arriving in the place where it matters most, which is when two tools could both
plausibly answer.

Note finally that the four questions of section 2 have not gone away just
because a tool exists. Question one still says put small documents in the
prompt, and if your notes fit, the right move is `build_system_prompt` from
lesson 10 rather than this tool. Question three still says grep for code, and the
tool description says so itself. Having built retrieval does not make it the
answer. It makes it the fourth answer, available when the first three did not
fit.

## 9. Running check.py

`check.py` builds a small workspace in a temporary directory and asserts five
things. Four of them prove the tool works. One proves that it does not, which
takes some explaining.

The fixture is four files.

```python
    (workspace / "refunds.md").write_text(
        "# Refunds\n\nCustomers may request a refund within thirty days of purchase.\n\n"
        "Refunds are paid back to the original card.\n",
        encoding="utf-8",
    )
    (workspace / "shipping.md").write_text(
        "# Shipping\n\nOrders are dispatched within two working days.\n\n"
        "Delivery takes three to five days.\n",
        encoding="utf-8",
    )
    (workspace / "team.md").write_text(
        "# The team\n\nThe team works remotely across three time zones.\n",
        encoding="utf-8",
    )
    (workspace / "billing.py").write_text(
        "def issue_refund(order_id):\n    return True\n", encoding="utf-8"
    )
```

Three Markdown files so there is something to retrieve over, and enough of them
that the rarity weights are computed from more than one document. `shipping.md`
exists to contain the word `dispatched` for the fourth assertion. And
`billing.py` is not Markdown at all, so the default pattern `*.md` never sees it,
which is what makes the fifth assertion a fair comparison rather than a rigged
one.

Run it from the lesson folder, or run every lesson at once from the repository
root.

```bash
cd lessons/16-retrieval
python check.py
```

```bash
python ci/run_lessons.py
```

A passing run.

```text
OK a question in ordinary words found the right passage
OK every passage says which file and line it came from
OK a question with no matching words says so instead of guessing
OK word matching does not understand word endings, which is the honest limit
OK when you know the exact name, grep answers directly and costs nothing to build
```

Five lines, no network, no API key, no model. Retrieval is an ordinary Python
function and the fact that a model will eventually call it has nothing to do with
whether it works.

Take them one at a time.

**The first** asks `how long to ask for a refund`, which shares almost no
phrasing with any document, and requires the answer to start with `refunds.md`.
That is the whole feature, proved end to end through `tools.run`, which is the
same dispatch path the agent loop uses.

**The second** checks that the first line of the answer contains a colon, which
is the `file:line` source from section 6. It is a small assertion guarding a
property that is easy to lose in a refactor and expensive to lose in production.

**The third** asks about `quantum entanglement` and requires the words `nothing
in the documents` in the reply. It proves the zero score filter is doing its job.
Without it the tool would return the three highest scoring passages out of eight
regardless of the fact that all three scored zero, and the model would receive
three paragraphs about refunds and shipping in response to a physics question.

**The fourth is the interesting one, because it tests a limitation on purpose.**

```python
    missed = tools.run("search_notes", {"question": "dispatch"})
    if "nothing in the documents" not in missed:
        fail("this check is wrong, dispatch should not match dispatched")
    print("OK word matching does not understand word endings, which is the honest limit")
```

Read the failure message. It does not say the tool is broken. It says the check
is wrong.

That is a deliberate inversion and it exists because of what this assertion is
for. `shipping.md` contains the word `dispatched`. The question is `dispatch`.
Section 7 explained that these are unrelated tokens to this code and that the
search therefore returns nothing. This assertion pins that behaviour in place.

Why pin a weakness in a test suite. Three reasons.

It is documentation that cannot rot. Section 7 makes a claim in prose about what
this tool cannot do, and prose in a README drifts away from the code that it
describes. This assertion fails the build if the claim stops being true.

It makes the limit impossible to skim past. A reader who runs the check sees a
line about word endings printed alongside four lines about things working. That
is harder to forget than a paragraph, and forgetting it is how somebody ships
this over a corpus where the synonym problem is the whole problem.

And it means a future change gets caught. Suppose somebody adds a stemmer, so
that `dispatched` and `dispatch` both reduce to `dispatch`. That is a genuine
improvement and it should be made deliberately, with the section 7 argument
revisited and the README updated. This assertion turns that change from a silent
one into a conversation, because the build goes red and the message says to look
at the check.

There is a real skill in this and it generalises past retrieval. When a system
has a known limitation that people will trip over, write a test that asserts the
limitation. It converts folklore into something the build enforces.

**The fifth** is the chapter's argument, executed.

```python
    exact = tools.run("grep_files", {"pattern": "issue_refund", "glob": "*.py"})
    if "billing.py" not in exact:
        fail("grep did not find an exact name, which is what it is for")
    print("OK when you know the exact name, grep answers directly and costs nothing to build")
```

```text
billing.py:1: def issue_refund(order_id):
```

One hit, the right one, the file and the line, from a tool with no index, no
scoring, no rarity weights and no chunking decision. That is question three of
section 2 answering itself in the same check file as question four, so the
comparison is not rhetorical.

If the first line fails, look at whether the workspace environment variable was
set before `tools` was imported, which is lesson 09's ordering trap and it is
still here. If the second fails, the source format string lost its line number.
If the fourth fails and the tool did return a passage, something added stemming
or fuzzy matching, and section 7 needs rewriting before that change lands.

## 10. What you cannot do yet

Take stock. The agent has permissions that remember what you decided, sessions
written to disk, context management that will not overflow, a token accounting
you can read, and now a way to search prose that is not code. That is a harness.

And every line of it assumes nothing goes wrong.

Look at `provider.stream` and notice there is no `try` anywhere near it. A rate
limit, a five second network blip, a gateway restart, a `500` from an overloaded
endpoint, and `httpx` raises, the exception travels up through `run` and out of
your program, and you get a traceback. Everything in that conversation is lost,
including the six files it had already read and the retrieval it had already
paid for.

Retrieval adds its own version of the same problem. `build_index` reads every
matching file in the workspace. A file that vanishes between the walk and the
read, a permissions error on one document, a disk that is briefly unavailable
over a network mount, and the whole search fails rather than the one file being
skipped. Compare `grep_files` from lesson 09, which catches `OSError` per file
and carries on. That is the same defensiveness applied at a smaller granularity,
and it is worth asking, for every loop you write over a filesystem, whether one
bad element should end the operation.

The `raise RuntimeError` at the bottom of the loop is the same shape of problem
from the other end. Hitting the turn limit is frequently not a failure at all, it
often means the agent was making progress and needed one more turn. Crashing is a
poor answer to that, and so is silently continuing.

That is lesson 17. Which failures are worth retrying and which are not,
exponential backoff with jitter, and honouring the `Retry-After` header when the
server sends one. It also covers the two things that are easy to get badly wrong.
Retrying a tool that has side effects means doing the side effect twice, so an
idempotency key is required and a retry loop around the model call is not
sufficient. And interrupting an agent has to stop every layer at once, the open
stream, any subprocess it spawned, and any pending permission question, because
real harnesses have shipped the bug where the screen says stopped and the tool is
still running.

Then lesson 18 is the second milestone, where all of it becomes a real command
line tool with `chat`, `run` and `resume`.

### Exercises before you move on

**One.** Add the length correction from section 5. Divide each score by the
square root of the number of words in the passage, or by the length relative to
the average passage length, and rerun the check. The interesting part is not the
formula, it is watching which results change. Then find a query where the
correction makes the answer worse and decide what that tells you.

**Two.** Handle the document with no paragraphs. Find or make a file that is one
enormous block, confirm that `passages_in` returns a single passage covering the
whole thing, and add a fallback that splits an over-long block on sentence
boundaries rather than on a character count. Keep the line numbers correct, which
is the part that takes the time and is the reason the source in section 6 is
worth protecting.

**Three.** Build the hybrid from section 7, without embeddings. Run
`search_notes` and `grep_files` on the same question, merge the two ranked lists,
and return the combination with a note saying which tool found each passage. Then
ask the harder question, which is how you rank a keyword hit against a scored
passage when the two numbers mean completely different things. There is no clean
answer and the standard approach is reciprocal rank fusion, which is worth
looking up once you have felt why the obvious approaches do not work.

**Four.** Run the four questions of section 2 against something real that you
own. Write down the corpus, the answer to each question, and where you stopped.
If you stopped at question one, put the documents in the prompt this afternoon
and see whether it works. That exercise has saved more engineering time than any
other paragraph in this chapter.

On to lesson 17.
