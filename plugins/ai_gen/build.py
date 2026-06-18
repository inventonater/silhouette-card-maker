import glob
import os
import re
import shutil
import sys

import click
from natsort import natsorted

# Add repo root to path so this can be run as a script (mirrors other plugins).
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, REPO_ROOT)

from utilities import (
    Registration,
    FitMode,
    generate_pdf,
    ensure_directory,
    get_image_file_paths,
    load_layout_config,
    get_all_card_size_names,
    get_all_paper_size_names,
)

front_directory = os.path.join(REPO_ROOT, 'game', 'front')
back_directory = os.path.join(REPO_ROOT, 'game', 'back')
double_sided_directory = os.path.join(REPO_ROOT, 'game', 'double_sided')
output_directory = os.path.join(REPO_ROOT, 'game', 'output')
candidates_directory = os.path.join(REPO_ROOT, 'game', 'candidates')
cutting_templates_directory = os.path.join(REPO_ROOT, 'cutting_templates')

default_output_path = os.path.join(output_directory, 'game.pdf')

layout_config = load_layout_config()
card_size_choices = get_all_card_size_names(layout_config)
paper_size_choices = get_all_paper_size_names(layout_config)


def _clean_id(card_id: str) -> str:
    return re.sub(r'[^\w]', '', card_id)


def _clear_directory(dir_path: str) -> None:
    """Remove files from a game image directory, preserving placeholder markers."""
    for item in os.listdir(dir_path):
        if item in ('README.md', 'EMPTY.md'):
            continue
        full_path = os.path.join(dir_path, item)
        if os.path.isfile(full_path):
            os.remove(full_path)
        elif os.path.isdir(full_path):
            shutil.rmtree(full_path)


def collect_approved(candidates_dir: str, front_dir: str) -> int:
    """Copy surviving candidate images into the front directory.

    Each card's folder under ``candidates_dir`` is treated as approved: every
    image left in it is copied into ``front_dir`` with a layout-friendly name.
    Folders whose name starts with "_" are ignored. Returns the count copied.
    """
    if not os.path.isdir(candidates_dir):
        raise click.ClickException(
            f'Candidates directory "{candidates_dir}" does not exist. '
            'Run plugins/ai_gen/generate.py first.'
        )

    card_dirs = sorted(
        d for d in os.listdir(candidates_dir)
        if os.path.isdir(os.path.join(candidates_dir, d)) and not d.startswith('_')
    )

    copied = 0
    for index, card_id in enumerate(card_dirs, start=1):
        card_dir = os.path.join(candidates_dir, card_id)
        images = natsorted(get_image_file_paths(card_dir))
        clean = _clean_id(card_id)

        for copy_num, rel_path in enumerate(images, start=1):
            src = os.path.join(card_dir, rel_path)
            dest_name = f'{index:03d}{clean}{copy_num}.png'
            shutil.copyfile(src, os.path.join(front_dir, dest_name))
            copied += 1

    return copied


def find_cutting_template(paper_size: str, card_size: str) -> str | None:
    """Return the newest matching .studio3 cutting template, if present."""
    pattern = os.path.join(cutting_templates_directory, f'{paper_size}-{card_size}-v*.studio3')
    matches = natsorted(glob.glob(pattern))
    return matches[-1] if matches else None


@click.command()
@click.option('--candidates_dir', default=candidates_directory, show_default=True,
              help='Directory containing per-card candidate folders.')
@click.option('--card_size', default='standard', type=click.Choice(card_size_choices, case_sensitive=False),
              show_default=True, help='The desired card size.')
@click.option('--paper_size', default='tabloid', type=click.Choice(paper_size_choices, case_sensitive=False),
              show_default=True, help='The desired paper size.')
@click.option('--registration', default=Registration.FOUR.value,
              type=click.Choice([t.value for t in Registration], case_sensitive=False),
              show_default=True, help='Registration marks (4 = Silhouette Cameo 5 Alpha).')
@click.option('--fit', default=FitMode.CROP.value, type=click.Choice([t.value for t in FitMode], case_sensitive=False),
              show_default=True, help='How to fit images to card size.')
@click.option('--ppi', default=300, type=click.IntRange(min=1), show_default=True, help='Pixels per inch.')
@click.option('--quality', default=100, type=click.IntRange(min=0, max=100), show_default=True,
              help='Output compression quality.')
@click.option('--output_path', default=default_output_path, show_default=True, help='Output PDF path.')
@click.option('--clean', is_flag=True, default=False, help='Clear the front directory before collecting.')
def cli(candidates_dir, card_size, paper_size, registration, fit, ppi, quality, output_path, clean):
    """Collect approved candidates and build the print PDF + name the cut template."""
    ensure_directory(front_directory)
    ensure_directory(back_directory)
    ensure_directory(double_sided_directory)

    if clean:
        _clear_directory(front_directory)
        print(f'Cleared {os.path.relpath(front_directory, REPO_ROOT)}.')

    copied = collect_approved(candidates_dir, front_directory)
    if copied == 0:
        raise click.ClickException(
            'No approved candidate images found. Generate candidates and keep at '
            'least one variation per card before building.'
        )
    print(f'Collected {copied} approved card image(s) into {os.path.relpath(front_directory, REPO_ROOT)}.')

    generate_pdf(
        front_directory,
        back_directory,
        double_sided_directory,
        output_path,
        False,            # output_images
        card_size,
        paper_size,
        Registration(registration),
        True,             # only_fronts
        FitMode(fit),
        None,             # crop_string
        None,             # crop_backs_string
        0,                # extend_corners
        ppi,
        quality,
        [],               # skip_indices
        False,            # load_offset
        None,             # label
    )

    print(f'\nWrote print PDF to {os.path.relpath(output_path, REPO_ROOT)}')

    template = find_cutting_template(paper_size, card_size)
    if template:
        print(
            'Next: print the PDF on your Epson ET-8550, then open this cutting '
            f'template in Silhouette Studio:\n  {os.path.relpath(template, REPO_ROOT)}\n'
            f'Confirm the printed {registration}-corner registration marks align with the template.'
        )
    else:
        print(
            f'No cutting template found for {paper_size}/{card_size}. '
            'Generate one with generate_dxf.py / dxf_to_studio3.py.'
        )


if __name__ == '__main__':
    cli()
