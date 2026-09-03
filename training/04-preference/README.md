# Training 4. Preference tuning, without a reward model

This folder is the code behind the fourth chapter of part 4 of the book,
at [book/20-preference.md](../../book/20-preference.md). The chapter takes
the third training round from foundations chapter 7, preference tuning,
and runs it on the foundations chapter 4 grid with DPO, where a preference is a pair
of next words. This file is the short version for running the code.

The numpy files need no GPU. `train_dpo.py` needs one.

## What is here

`grid.py`, the foundations chapter 4 grid, is unchanged from the previous folders.

`dpo.py` holds the loss and its gradient. `dpo_loss` says how far the
model is from preferring chosen over rejected, relative to a frozen
reference. `dpo_gradient` is that loss differentiated by the chain rule.
`train_dpo` steps downhill on it, and `drift` measures how far the whole
model moved, which is what the reference term is there to limit.

```python
def dpo_loss(weights, reference, preferences, index, beta=1.0):
    """How far the policy is from preferring chosen over rejected, relative to the reference."""
    total = 0.0
    for context, chosen, rejected in preferences:
        policy_margin = log_probability(weights, context, chosen, index) - log_probability(
            weights, context, rejected, index
        )
        reference_margin = log_probability(reference, context, chosen, index) - log_probability(
            reference, context, rejected, index
        )
        total += -np.log(sigmoid(beta * (policy_margin - reference_margin)))
    return total / len(preferences)
```

`train_dpo.py` is the same loss on an open model, with trl holding the
reference and the loop and a file of preference pairs as the data. It
is not run in CI.

`check.py` pins the claims the chapter makes.

## Run it

```bash
python dpo.py
```

```text
dpo loss at the start 0.693, after training 0.013

after 'the agent'   reference   tuned
  asks              0.000    0.003
  runs              0.121    0.015
  reads             0.496    0.554
  decides           0.371    0.415

mean change in every probability of the model 0.0015
the same with plain finetuning on the chosen words only 0.0043
```

```bash
python check.py
```

```text
OK at the start the loss is log two, because the policy and the reference agree exactly
OK the loss falls, with no reward model and no reinforcement learning anywhere
OK every chosen word gains on its rejected word, relative to where the reference was
OK the reference term keeps the model near where it started, plain finetuning drifts more
OK beta only matters once the policy has moved, it is the leash and not the direction
```

On a GPU.

```bash
pip install "agentpath-kit[training]"
python train_dpo.py pairs.jsonl --model adapter-merged --output dpo-adapter
```

## What to notice

The loss starts at 0.693, which is log two, and that is not a coincidence.
At step zero the policy is the reference, the margins cancel, the sigmoid
sits at a half, and minus log a half is log two. Every DPO run starts
there, and a run that does not has a bug in its reference.

Read the `runs` row. The rejected word fell from 0.121 to 0.015 while the
chosen word barely rose, because the base model had never seen `asks`
follow `agent` and there is only so far a sixty step nudge takes a word
from nothing. Preference tuning pushes rejected down far more easily than
it pulls chosen up, and on a real model that is where most of its effect
shows, in what the model stops saying.

The last two lines are the reference term doing its job. DPO moved the
model's probabilities by 0.0015 on average. Plain fine tuning on the
chosen words alone, the same steps at the same rate, moved them by three
times that. The reference is the leash, beta is its length, and it is
the whole difference between a model that learned a preference and one
that forgot everything else to satisfy it.
