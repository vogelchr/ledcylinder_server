#!/usr/bin/python
from PIL import PcfFontFile
import tempfile
from gzip import GzipFile
from pathlib import Path
from logging import getLogger
import shutil

logger = getLogger(__name__)


def convert_font(src_fn: Path, dst_pil_fn: Path, dst_pbm_fn: Path) -> bool:
    if '.gz' in src_fn.suffixes:
        fp = GzipFile(src_fn)
    else:
        fp = src_fn.open('rb')
    pff = PcfFontFile.PcfFontFile(fp)

    ###
    # PcfFontFile has quirky way to save the pil fonts,
    # it takes a basename and creates a pbm and a pil file
    # from that...
    ###
    with tempfile.NamedTemporaryFile('wb') as tmp_file:
        tmp_pcf_fn = Path(tmp_file.name)
        tmp_pil_fn = tmp_pcf_fn.with_suffix('.pil')
        tmp_pbm_fn = tmp_pcf_fn.with_suffix('.pbm')

        ret = False

        try:
            pff.save(tmp_pcf_fn)  # will save to xxx.pil and xxx.pbm
            shutil.copy(tmp_pil_fn, dst_pil_fn)
            shutil.copy(tmp_pbm_fn, dst_pbm_fn)
            ret = True
        except Exception as exc:
            logger.exception('*** Exception while converting fonts! ***')

        tmp_pbm_fn.unlink(missing_ok=True)
        tmp_pil_fn.unlink(missing_ok=True)

        return ret

def populate_font_cache(cache_path: Path, src_path: Path):
    logger.info(f'{cache_path} {src_path}')
    cache_path.mkdir(exist_ok=True)

    number_of_fonts = 0

    for parent, _, files in src_path.walk():
        for file in files:
            src_pcf_fn = parent / file
            if '.pcf' not in src_pcf_fn.suffixes:
                continue

            dst_pil_fn = (cache_path / src_pcf_fn.stem.lower()
                            ).with_suffix('.pil')
            dst_pbm_fn = (cache_path / src_pcf_fn.stem.lower()).with_suffix('.pbm')

            if dst_pil_fn.exists() and dst_pbm_fn.exists():
                number_of_fonts += 1
                continue

            if convert_font(src_pcf_fn, dst_pil_fn, dst_pbm_fn):
                print(f'Converted {src_pcf_fn.stem} -> {dst_pil_fn}')
                number_of_fonts += 1

    if not number_of_fonts:
        logger.error(
            '*** ERROR: No fonts discovered, this can\'t be right! ***')
    logger.info(f'{number_of_fonts} fonts converted.')


if __name__ == '__main__':
    import argparse
    import logging
    parser = argparse.ArgumentParser()
    parser.add_argument('cache_dir', type=Path)
    parser.add_argument('src_dir', type=Path)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

    logger.info(f'Filling {args.cache_dir} with fonts from {args.src_dir}...')

    populate_font_cache(args.cache_dir, args.src_dir)
