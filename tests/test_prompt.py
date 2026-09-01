from agentpath.prompt import build_system_prompt


def test_prompt_names_the_workspace(tmp_path):
    prompt = build_system_prompt(tmp_path)
    assert str(tmp_path.resolve()) in prompt


def test_prompt_states_the_platform(tmp_path):
    assert "Platform" in build_system_prompt(tmp_path)


def test_extra_instructions_are_appended(tmp_path):
    prompt = build_system_prompt(tmp_path, extra="Always write tests first.")
    assert prompt.rstrip().endswith("Always write tests first.")
