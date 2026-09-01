import pytest

from agentpath.tools.base import ToolRegistry
from agentpath.tools.retrieval import retrieval_tools
from agentpath.types import ToolCall


@pytest.fixture
def registry(tmp_path):
    (tmp_path / "refunds.md").write_text(
        "# Refunds\n\nCustomers may request a refund within thirty days of purchase.\n\n"
        "Refunds are paid to the original card.\n",
        encoding="utf-8",
    )
    (tmp_path / "shipping.md").write_text(
        "# Shipping\n\nOrders are dispatched within two working days.\n\n"
        "Delivery takes three to five days.\n",
        encoding="utf-8",
    )
    (tmp_path / "team.md").write_text(
        "# The team\n\nThe team works remotely across three time zones.\n",
        encoding="utf-8",
    )
    return ToolRegistry(retrieval_tools(tmp_path))


def call(registry, **arguments):
    return registry.run(ToolCall(id="1", name="search_notes", arguments=arguments)).content


def test_the_right_document_comes_first(registry):
    result = call(registry, question="how long do customers have to ask for a refund")
    assert result.splitlines()[0].startswith("refunds.md")


def test_results_say_where_they_came_from(registry):
    """A passage with no source is useless, because the agent cannot go and read more."""
    assert ":" in call(registry, question="refund").splitlines()[0]


def test_a_rare_word_beats_a_common_one(registry):
    """dispatched appears once, days appears in several passages.

    A scorer that only counted matching words would let days decide, and
    days is in the refund document too. Weighting by rarity is what makes
    the passage that actually answers the question win.
    """
    result = call(registry, question="dispatched days")
    assert result.splitlines()[0].startswith("shipping.md")


def test_word_matching_does_not_understand_word_endings(registry):
    """An honest test of the limit this approach has.

    The document says dispatched and the question says dispatch, so nothing
    matches. This is not a bug to fix here. It is the exact gap that
    embeddings fill, and knowing where the gap is matters more than
    pretending it is not there. Lesson 16 covers the decision.
    """
    result = call(registry, question="dispatch")
    assert "nothing in the documents" in result


def test_a_word_in_every_passage_carries_no_weight():
    """This is the whole idea of the scoring, tested directly.

    A word that appears in every passage cannot tell any of them apart, so
    its rarity has to be zero rather than merely small.
    """
    import math

    from agentpath.tools.retrieval import score

    index = [{"words": {"the", "alpha"}}, {"words": {"the", "beta"}}]
    rarity = {"the": math.log(2 / 2), "alpha": math.log(2 / 1)}
    assert score({"the"}, index[0], rarity) == 0.0
    assert score({"alpha"}, index[0], rarity) > 0.0


def test_a_question_with_no_matching_words_says_so(registry):
    assert "nothing in the documents" in call(registry, question="quantum entanglement")


def test_an_empty_document_set_is_reported_not_crashed(tmp_path):
    registry = ToolRegistry(retrieval_tools(tmp_path))
    assert "no *.md documents" in call(registry, question="anything")


def test_credential_files_are_not_indexed(tmp_path):
    """Retrieval must honour the same refusal every other tool honours."""
    (tmp_path / ".env.md").write_text("API_KEY=sk-supersecret\n", encoding="utf-8")
    registry = ToolRegistry(retrieval_tools(tmp_path))
    assert "sk-supersecret" not in call(registry, question="API_KEY")

NEWLINE = "\n"
PARAGRAPH = "\n\n"

def test_one_unreadable_path_does_not_kill_the_whole_tool(tmp_path):
    """A directory can match a file pattern, and then everything stops."""
    (tmp_path / "archive.md").mkdir()
    (tmp_path / "real.md").write_text(
        "# Notes" + PARAGRAPH + "the refund window is thirty days" + NEWLINE,
        encoding="utf-8",
    )
    registry = ToolRegistry(retrieval_tools(tmp_path))
    result = call(registry, question="refund window")
    assert "real.md" in result
    assert "Error" not in result
