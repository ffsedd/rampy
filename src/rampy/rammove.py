#!/usr/bin/env python3
from __future__ import annotations

import logging
import shutil
from pathlib import Path

from rampy.zlib import zak_dict, find_zakazky_dir

ROOT = Path.home() / "Dropbox/zumi_2/ANALYZY/RAMAN/RAMANPY"


def configure_logging() -> None:
    logging.basicConfig(
        format="!%(levelno)s [%(module)10s%(lineno)4d]\t%(message)s",
        level=logging.INFO,
    )


def extract_zakazka_number(pdf_path: Path) -> int | None:
    try:
        return int(pdf_path.stem[:4])
    except ValueError:
        logging.error("pdf nezačíná číslem zakázky: %s", pdf_path)
        return None


def copy_files(src_dir: Path, pattern: str, dst_dir: Path) -> None:
    dst_dir.mkdir(parents=True, exist_ok=True)

    for path in src_dir.glob(pattern):
        name = path.name.replace("%", "_")
        shutil.copy2(path, dst_dir / name)


def process_pdf(pdf_path: Path, zak_dict: dict[int, Path], done_dir: Path) -> None:
    zakno = extract_zakazka_number(pdf_path)
    if zakno is None:
        return

    trg_root = zak_dict[zakno] / "pytex" / "raman"

    # copy pdf
    spektra_dir = trg_root / "spektra"
    spektra_dir.mkdir(parents=True, exist_ok=True)

    pdf_name = pdf_path.name.replace("%", "_")
    shutil.copy2(pdf_path, spektra_dir / pdf_name)

    # source folder with spectra files
    src_dir = pdf_path.parent / pdf_path.stem

    copy_files(src_dir, "*.jdx", trg_root / "jdx")
    copy_files(src_dir, "*.jpg", trg_root / "lokalizace")

    # move processed data
    pdf_path.rename(done_dir / pdf_path.name)

    done_src = done_dir / src_dir.name
    if done_src.exists():
        shutil.rmtree(done_src)

    src_dir.rename(done_src)

    logging.info("%s -> %s", pdf_path, trg_root)


def process_root(root: Path, zak_dict: dict[int, Path]) -> None:
    done_dir = root / "_DONE"
    done_dir.mkdir(exist_ok=True)

    for pdf_path in root.glob("*.pdf"):
        process_pdf(pdf_path, zak_dict, done_dir)


def main() -> None:
    configure_logging()
    zak_root =  find_zakazky_dir()
    zdic = zak_dict(zak_root)
    root = ROOT.resolve()

    process_root(root, zdic)


if __name__ == "__main__":
    main()