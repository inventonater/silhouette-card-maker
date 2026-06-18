import io
import json
import os

import pytest
from PIL import Image

from plugins.ai_gen.spec import load_spec, Spec, ResolvedCard
from plugins.ai_gen.backends.base import ImageGenerator, GenerationError
from plugins.ai_gen.generate import generate_candidates
from plugins.ai_gen.build import collect_approved, find_cutting_template, _clean_id


def _png_bytes(color=(255, 0, 0)) -> bytes:
    buf = io.BytesIO()
    Image.new('RGB', (8, 8), color).save(buf, format='PNG')
    return buf.getvalue()


class FakeBackend(ImageGenerator):
    """In-memory backend that records calls and returns dummy PNGs (no network)."""

    def __init__(self):
        self.calls = []

    def generate(self, prompt, n, *, size, quality, thinking, reference_images=None):
        self.calls.append({
            'prompt': prompt, 'n': n, 'size': size, 'quality': quality,
            'thinking': thinking, 'reference_images': reference_images,
        })
        return [_png_bytes() for _ in range(n)]


def _write_spec(tmp_path, data) -> str:
    spec_path = os.path.join(tmp_path, 'spec.json')
    with open(spec_path, 'w') as f:
        json.dump(data, f)
    return spec_path


# --- spec parsing -----------------------------------------------------------

@pytest.mark.unit
def test_spec_applies_defaults_and_overrides(tmp_path):
    spec = Spec.model_validate({
        'defaults': {'variations': 8, 'size': '1024x1536', 'quality': 'high', 'thinking': 'high'},
        'cards': [
            {'id': 'a', 'prompt': 'p'},
            {'id': 'b', 'prompt': 'p2', 'variations': 3, 'quality': 'low'},
        ],
    })
    cards = spec.resolved_cards(str(tmp_path))
    assert (cards[0].variations, cards[0].quality) == (8, 'high')
    assert (cards[1].variations, cards[1].quality) == (3, 'low')


@pytest.mark.unit
def test_spec_rejects_duplicate_ids(tmp_path):
    with pytest.raises(Exception):
        Spec.model_validate({'cards': [
            {'id': 'dup', 'prompt': 'x'}, {'id': 'dup', 'prompt': 'y'},
        ]})


@pytest.mark.unit
def test_spec_rejects_bad_id():
    with pytest.raises(Exception):
        Spec.model_validate({'cards': [{'id': 'bad id!', 'prompt': 'x'}]})


@pytest.mark.unit
def test_spec_rejects_empty_cards():
    with pytest.raises(Exception):
        Spec.model_validate({'cards': []})


@pytest.mark.unit
def test_reference_paths_resolved_relative_to_spec(tmp_path):
    card = Spec.model_validate({'cards': [
        {'id': 'a', 'prompt': 'p', 'reference': 'refs/x.png'},
    ]}).resolved_cards(str(tmp_path))[0]
    assert card.reference_images == [os.path.join(str(tmp_path), 'refs', 'x.png')]


@pytest.mark.unit
def test_load_example_spec():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    spec = load_spec(os.path.join(repo_root, 'game', 'specs', 'example.json'))
    assert len(spec.cards) >= 1


# --- generate ---------------------------------------------------------------

@pytest.mark.unit
def test_generate_writes_candidates(tmp_path, monkeypatch):
    fake = FakeBackend()
    monkeypatch.setattr('plugins.ai_gen.generate.get_backend', lambda name: fake)

    spec_path = _write_spec(tmp_path, {
        'defaults': {'variations': 2},
        'cards': [{'id': 'card_one', 'prompt': 'hello'}],
    })
    out_dir = os.path.join(tmp_path, 'candidates')
    generate_candidates(spec_path, 'openai', out_dir, overwrite=False)

    files = sorted(os.listdir(os.path.join(out_dir, 'card_one')))
    assert files == ['card_one-1.png', 'card_one-2.png']
    assert fake.calls[0]['n'] == 2


@pytest.mark.unit
def test_generate_skips_existing_without_overwrite(tmp_path, monkeypatch):
    fake = FakeBackend()
    monkeypatch.setattr('plugins.ai_gen.generate.get_backend', lambda name: fake)

    spec_path = _write_spec(tmp_path, {'cards': [{'id': 'c', 'prompt': 'p', 'variations': 1}]})
    out_dir = os.path.join(tmp_path, 'candidates')

    generate_candidates(spec_path, 'openai', out_dir, overwrite=False)
    generate_candidates(spec_path, 'openai', out_dir, overwrite=False)
    assert len(fake.calls) == 1  # second run skipped

    generate_candidates(spec_path, 'openai', out_dir, overwrite=True)
    assert len(fake.calls) == 2  # overwrite regenerates


# --- collect / build --------------------------------------------------------

@pytest.mark.unit
def test_collect_approved_copies_survivors(tmp_path):
    candidates = os.path.join(tmp_path, 'candidates')
    front = os.path.join(tmp_path, 'front')
    os.makedirs(front)

    # two cards, with 2 and 1 surviving variations
    for card_id, count in [('alpha', 2), ('beta', 1)]:
        d = os.path.join(candidates, card_id)
        os.makedirs(d)
        for k in range(1, count + 1):
            with open(os.path.join(d, f'{card_id}-{k}.png'), 'wb') as f:
                f.write(_png_bytes())

    # an excluded folder
    excluded = os.path.join(candidates, '_archive')
    os.makedirs(excluded)
    with open(os.path.join(excluded, 'x-1.png'), 'wb') as f:
        f.write(_png_bytes())

    copied = collect_approved(candidates, front)
    assert copied == 3
    names = sorted(os.listdir(front))
    assert names == ['001alpha1.png', '001alpha2.png', '002beta1.png']


@pytest.mark.unit
def test_collect_ignores_non_image_files(tmp_path):
    candidates = os.path.join(tmp_path, 'candidates')
    front = os.path.join(tmp_path, 'front')
    os.makedirs(front)
    d = os.path.join(candidates, 'card')
    os.makedirs(d)
    with open(os.path.join(d, 'card-1.png'), 'wb') as f:
        f.write(_png_bytes())
    with open(os.path.join(d, 'notes.txt'), 'w') as f:
        f.write('not an image')

    assert collect_approved(candidates, front) == 1


@pytest.mark.unit
def test_clean_id_strips_punctuation():
    assert _clean_id('fire-drake_01') == 'firedrake_01'


@pytest.mark.unit
def test_find_cutting_template_for_standard_tabloid():
    # The repo ships standard tabloid/a3 templates; the build step should find them.
    assert find_cutting_template('tabloid', 'standard') is not None
    assert find_cutting_template('a3', 'standard') is not None


@pytest.mark.unit
def test_find_cutting_template_missing_returns_none():
    assert find_cutting_template('nonexistent_paper', 'nonexistent_card') is None


# --- backend selection ------------------------------------------------------

@pytest.mark.unit
def test_browser_backend_not_implemented():
    from plugins.ai_gen.backends import get_backend
    backend = get_backend('browser')
    with pytest.raises(GenerationError):
        backend.generate('p', 1, size='1024x1536', quality='high', thinking='high')


@pytest.mark.unit
def test_unknown_backend_raises():
    from plugins.ai_gen.backends import get_backend
    with pytest.raises(GenerationError):
        get_backend('does_not_exist')
