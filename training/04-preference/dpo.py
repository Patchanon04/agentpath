"""Preference tuning, the third training round from foundations chapter 7, in numpy.

Instruction tuning shows the model good answers. Preference tuning shows
it pairs, one answer a person preferred and one they did not, and asks
it to move toward the first and away from the second. RLHF did this by
training a separate reward model and then running reinforcement
learning against it. DPO, direct preference optimization, showed in
2023 that the same objective can be written as a loss on the model's
own probabilities, with no reward model and no reinforcement learning,
which is why it is what most people run now. This file runs it on the
chapter 4 grid, where a preference is a pair of next words.
"""
import numpy as np
from grid import BASE_CORPUS, gradient, pairs, pretrain, softmax, vocabulary

# After 'the agent', people prefer 'asks' to 'runs'. After 'the tool',
# they prefer 'returns' to 'and'. The base model has never seen 'asks'
# follow 'agent', so this is a preference it has to learn against its
# own habit.
PREFERENCES = [
    ("agent", "asks", "runs"),
    ("tool", "returns", "and"),
    ("model", "asks", "reads"),
]


def log_probability(weights, context, word, index):
    row = softmax(weights[index[context]])
    return float(np.log(row[index[word]]))


def dpo_loss(weights, reference, preferences, index, beta=1.0):
    """How far the policy is from preferring chosen over rejected, relative to the reference.

    For each pair, take how much more the policy likes chosen than
    rejected, subtract how much more the reference already did, scale by
    beta, and push it through a sigmoid. The reference term is what
    stops the model from simply making every rejected word impossible.
    It is only rewarded for moving the preference relative to where it
    started, and beta says how far from the reference it is allowed to
    drift. That is the whole of DPO.
    """
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


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def dpo_gradient(weights, reference, preferences, index, beta=1.0):
    """The gradient of dpo_loss with respect to the grid, by the chain rule.

    For a softmax row, the gradient of log probability of a word is one
    hot at the word minus the probabilities. The DPO loss weights the
    difference of the chosen and rejected gradients by how wrong the
    current margin still is, so pairs the model already gets right pull
    almost nothing and pairs it gets wrong pull hard.
    """
    change = np.zeros_like(weights)
    for context, chosen, rejected in preferences:
        row = index[context]
        probabilities = softmax(weights[row])
        policy_margin = np.log(probabilities[index[chosen]]) - np.log(
            probabilities[index[rejected]]
        )
        reference_row = softmax(reference[row])
        reference_margin = np.log(reference_row[index[chosen]]) - np.log(
            reference_row[index[rejected]]
        )
        pull = beta * (1.0 - sigmoid(beta * (policy_margin - reference_margin)))
        difference = np.zeros_like(probabilities)
        difference[index[chosen]] += 1.0
        difference[index[rejected]] -= 1.0
        change[row] -= pull * difference / len(preferences)
    return change


def train_dpo(reference, preferences, index, steps=60, learning_rate=2.0, beta=1.0):
    weights = reference.copy()
    history = []
    for _ in range(steps):
        history.append(dpo_loss(weights, reference, preferences, index, beta))
        weights -= learning_rate * dpo_gradient(weights, reference, preferences, index, beta)
    return weights, history


def drift(weights, reference, index):
    """How far the whole model moved, as the mean absolute change in probabilities."""
    return float(np.abs(softmax(weights) - softmax(reference)).mean())


if __name__ == "__main__":
    words, index = vocabulary(BASE_CORPUS, " ".join(w for p in PREFERENCES for w in p))
    reference = pretrain(index)
    tuned, history = train_dpo(reference, PREFERENCES, index)
    print(f"dpo loss at the start {history[0]:.3f}, after training {history[-1]:.3f}")
    print()
    print("after 'the agent'   reference   tuned")
    for word in ["asks", "runs", "reads", "decides"]:
        before = np.exp(log_probability(reference, "agent", word, index))
        after = np.exp(log_probability(tuned, "agent", word, index))
        print(f"  {word:8s}          {before:.3f}    {after:.3f}")
    print()
    print(f"mean change in every probability of the model {drift(tuned, reference, index):.4f}")
    naive = reference.copy()
    xs, ys = pairs("the agent asks . the tool returns . the model asks .", index)
    for _ in range(60):
        naive -= 2.0 * gradient(naive, xs, ys)
    moved = drift(naive, reference, index)
    print(f"the same with plain finetuning on the chosen words only {moved:.4f}")
