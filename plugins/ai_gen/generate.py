import os
import sys

import click

# Add repo root to path so this can be run as a script (mirrors other plugins).
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, REPO_ROOT)

from utilities import ensure_directory
from plugins.ai_gen.spec import load_spec, ResolvedCard
from plugins.ai_gen.backends import get_backend, get_backend_names
from plugins.ai_gen.backends.base import GenerationError

default_candidates_directory = os.path.join(REPO_ROOT, 'game', 'candidates')


def _existing_candidate_images(card_dir: str) -> list:
    if not os.path.isdir(card_dir):
        return []
    return [f for f in os.listdir(card_dir) if not f.startswith('.')]


def generate_candidates(spec_path: str, backend_name: str, out_dir: str, overwrite: bool) -> None:
    spec = load_spec(spec_path)
    base_dir = os.path.dirname(os.path.abspath(spec_path))
    cards = spec.resolved_cards(base_dir)

    backend = get_backend(backend_name)
    ensure_directory(out_dir)

    print(f'Generating candidates for {len(cards)} card(s) using the "{backend_name}" backend.\n')

    for card in cards:
        card_dir = os.path.join(out_dir, card.id)

        if not overwrite and _existing_candidate_images(card_dir):
            print(f'[{card.id}] already has candidates, skipping (use --overwrite to regenerate).')
            continue

        # Validate reference images up front for a clear error.
        for ref in card.reference_images:
            if not os.path.isfile(ref):
                raise click.ClickException(f'[{card.id}] reference image not found: {ref}')

        ref_note = f' (with {len(card.reference_images)} reference image(s))' if card.reference_images else ''
        print(f'[{card.id}] generating {card.variations} variation(s){ref_note}...')

        try:
            images = backend.generate(
                card.prompt,
                card.variations,
                size=card.size,
                quality=card.quality,
                thinking=card.thinking,
                reference_images=card.reference_images or None,
            )
        except GenerationError as e:
            raise click.ClickException(str(e))

        if not images:
            raise click.ClickException(f'[{card.id}] backend returned no images.')

        ensure_directory(card_dir)
        for k, data in enumerate(images, start=1):
            image_path = os.path.join(card_dir, f'{card.id}-{k}.png')
            with open(image_path, 'wb') as f:
                f.write(data)

        print(f'[{card.id}] saved {len(images)} candidate(s) to {card_dir}')

    print(
        '\nDone. Review the candidates in each '
        f'{os.path.relpath(out_dir, REPO_ROOT)}/<card_id>/ folder and DELETE the '
        'variations you do not want. Whatever remains is treated as approved.\n'
        'Then run: python plugins/ai_gen/build.py'
    )


@click.command()
@click.argument('spec_path')
@click.option('--backend', 'backend_name', default='openai',
              type=click.Choice(get_backend_names(), case_sensitive=False),
              show_default=True, help='Image generation backend to use.')
@click.option('--out', 'out_dir', default=default_candidates_directory, show_default=True,
              help='Directory to write candidate folders into.')
@click.option('--overwrite', is_flag=True, default=False,
              help='Regenerate candidates even if a card already has some.')
def cli(spec_path: str, backend_name: str, out_dir: str, overwrite: bool):
    """Generate candidate card images from a JSON SPEC_PATH."""
    if not os.path.isfile(spec_path):
        raise click.ClickException(f'{spec_path} is not a valid file.')
    generate_candidates(spec_path, backend_name, out_dir, overwrite)


if __name__ == '__main__':
    cli()
