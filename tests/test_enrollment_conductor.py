import os
import numpy as np
import pytest
from unittest.mock import MagicMock
from EnrollmentConductor import EnrollmentConductor


def _dummy_embedding(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    e = rng.random(80).astype(np.float32)
    return e / np.linalg.norm(e)


@pytest.fixture
def conductor():
    return EnrollmentConductor('Alex', 'her')


# ─── greeting ────────────────────────────────────────────────────────────────

class TestGreeting:
    def test_greeting_contains_name(self, conductor):
        assert 'Alex' in conductor.greeting()

    def test_greeting_added_to_history(self, conductor):
        conductor.greeting()
        assert len(conductor._question_history) == 1

    def test_tts_name_used_in_greeting_when_provided(self):
        c = EnrollmentConductor('A.J.', 'him', tts_name='A J')
        greeting = c.greeting()
        assert 'A J' in greeting
        assert 'A.J.' not in greeting

    def test_tts_name_defaults_to_name(self):
        c = EnrollmentConductor('Alex', 'her')
        assert c.tts_name == 'Alex'


# ─── add_sample ──────────────────────────────────────────────────────────────

class TestAddSample:
    def test_sample_count_increments(self, conductor):
        conductor.add_sample(_dummy_embedding())
        assert len(conductor._samples) == 1

    def test_multiple_samples_accumulate(self, conductor):
        for i in range(3):
            conductor.add_sample(_dummy_embedding(i))
        assert len(conductor._samples) == 3


# ─── try_parse_age ───────────────────────────────────────────────────────────

class TestTryParseAge:
    def test_digit_age(self, conductor):
        assert conductor.try_parse_age('I am 8') is True
        assert conductor.age == 8

    def test_word_age(self, conductor):
        assert conductor.try_parse_age("I'm six years old") is True
        assert conductor.age == 6

    def test_word_age_no_qualifier(self, conductor):
        assert conductor.try_parse_age('seven') is True
        assert conductor.age == 7

    def test_ignores_large_numbers(self, conductor):
        assert conductor.try_parse_age('I saw 100 birds') is False
        assert conductor.age is None

    def test_adult_digit_age(self, conductor):
        assert conductor.try_parse_age("I'm 50") is True
        assert conductor.age == 50

    def test_adult_word_age(self, conductor):
        assert conductor.try_parse_age('fifty') is True
        assert conductor.age == 50

    def test_all_word_numbers_include_decades(self, conductor):
        for word, expected in [('twenty', 20), ('thirty', 30), ('forty', 40),
                                ('fifty', 50), ('sixty', 60), ('seventy', 70)]:
            c = EnrollmentConductor('Test', 'them')
            assert c.try_parse_age(word) is True
            assert c.age == expected

    def test_returns_false_on_no_age(self, conductor):
        assert conductor.try_parse_age('I like cats') is False

    def test_all_word_numbers_1_to_18(self, conductor):
        words = ['one','two','three','four','five','six','seven','eight','nine','ten',
                 'eleven','twelve','thirteen','fourteen','fifteen','sixteen','seventeen','eighteen']
        for i, word in enumerate(words, 1):
            c = EnrollmentConductor('Test', 'them')
            assert c.try_parse_age(word) is True
            assert c.age == i


# ─── is_complete / needs_age ─────────────────────────────────────────────────

class TestCompletion:
    def test_not_complete_initially(self, conductor):
        assert conductor.is_complete() is False

    def test_not_complete_with_samples_but_no_age(self, conductor):
        for i in range(6):
            conductor.add_sample(_dummy_embedding(i))
        assert conductor.is_complete() is False

    def test_not_complete_with_age_but_few_samples(self, conductor):
        conductor.age = 8
        for i in range(3):
            conductor.add_sample(_dummy_embedding(i))
        assert conductor.is_complete() is False

    def test_complete_with_samples_and_age(self, conductor):
        conductor.age = 8
        for i in range(6):
            conductor.add_sample(_dummy_embedding(i))
        assert conductor.is_complete() is True

    def test_needs_age_when_samples_done_but_no_age(self, conductor):
        for i in range(6):
            conductor.add_sample(_dummy_embedding(i))
        assert conductor.needs_age() is True

    def test_needs_age_false_when_age_set(self, conductor):
        conductor.age = 8
        for i in range(6):
            conductor.add_sample(_dummy_embedding(i))
        assert conductor.needs_age() is False


# ─── _next_prompt ────────────────────────────────────────────────────────────

class TestNextPrompt:
    def test_asks_age_after_two_samples(self, conductor):
        for i in range(2):
            conductor.add_sample(_dummy_embedding(i))
        prompt = conductor._next_prompt('something')
        assert 'old' in prompt.lower() or 'age' in prompt.lower()

    def test_asks_age_only_once(self, conductor):
        for i in range(4):
            conductor.add_sample(_dummy_embedding(i))
        prompts = [conductor._next_prompt('x') for _ in range(4)]
        age_prompts = [p for p in prompts if 'old' in p.lower() or 'age' in p.lower()]
        assert len(age_prompts) == 1

    def test_returns_string(self, conductor):
        prompt = conductor._next_prompt('some answer')
        assert isinstance(prompt, str) and len(prompt) > 0

    def test_uses_ask_claude_when_provided(self):
        claude_response = 'What is your favourite dinosaur?'
        ask_claude = MagicMock(return_value=claude_response)
        c = EnrollmentConductor('Test', 'them', ask_claude=ask_claude)
        result = c._next_prompt('I like pizza')
        assert result == claude_response
        ask_claude.assert_called_once_with('I like pizza', c)

    def test_falls_back_to_template_when_claude_returns_empty(self):
        ask_claude = MagicMock(return_value='')
        c = EnrollmentConductor('Test', 'them', ask_claude=ask_claude)
        result = c._next_prompt('I like pizza')
        assert isinstance(result, str) and len(result) > 0


# ─── save ────────────────────────────────────────────────────────────────────

class TestSave:
    def test_save_creates_npz(self, conductor, tmp_path):
        conductor.age = 6
        for i in range(6):
            conductor.add_sample(_dummy_embedding(i))
        path = conductor.save(str(tmp_path))
        assert os.path.exists(path)

    def test_saved_data_is_loadable(self, conductor, tmp_path):
        conductor.age = 6
        for i in range(6):
            conductor.add_sample(_dummy_embedding(i))
        path = conductor.save(str(tmp_path))
        data = np.load(path, allow_pickle=False)
        assert str(data['name']) == 'Alex'
        assert int(data['age']) == 6
        assert str(data['pronoun']) == 'her'
        assert data['embedding'].shape == (80,)

    def test_embedding_is_averaged(self, conductor, tmp_path):
        conductor.age = 6
        embeddings = [_dummy_embedding(i) for i in range(6)]
        for e in embeddings:
            conductor.add_sample(e)
        path = conductor.save(str(tmp_path))
        data = np.load(path, allow_pickle=False)
        expected = np.mean(embeddings, axis=0)
        np.testing.assert_allclose(data['embedding'], expected, rtol=1e-5)

    def test_creates_profiles_dir_if_missing(self, conductor, tmp_path):
        conductor.age = 6
        for i in range(6):
            conductor.add_sample(_dummy_embedding(i))
        new_dir = str(tmp_path / 'new_profiles')
        conductor.save(new_dir)
        assert os.path.isdir(new_dir)
