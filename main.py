import argparse
import os
import re
import subprocess
from pathlib import Path
from typing import List, Tuple

import requests
from dotenv import load_dotenv
from pylatexenc.latexwalker import LatexNode, LatexWalker, LatexEnvironmentNode

from utils.to_scrapbox import node2mask, ReferenceMasker


def parse(tex: str) -> List[LatexNode]:
    w = LatexWalker(tex)
    nodelist, *_ = w.get_latex_nodes(pos=0)

    # extract document body
    for node in nodelist[::-1]:
        if (
            isinstance(node, LatexEnvironmentNode)
            and node.environmentname == "document"
        ):
            return node.nodelist

    print("Error: No document environment found.")
    exit(1)


def make_masked_text(nodelist: List[LatexNode]) -> Tuple[str, Tuple[str, str]]:
    # TODO: make this class?
    masked_expr_list, mask_pairs = zip(*[node2mask(node) for node in nodelist])
    masked_text = "".join(masked_expr_list)
    mask_dict = dict(filter(lambda x: x is not None, mask_pairs))
    return masked_text, mask_dict


def translate_text(api_key, text, source_lang, target_lang):
    """
    Translate the given text using the DeepL API.

    Args:
        api_key (str): The API key for DeepL.
        text (str): The text to translate.
        source_lang (str): The source language.
        target_lang (str): The target language.

    Returns:
        str: The translated text.
    """
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }
    payload = {
        "auth_key": api_key,
        "text": text,
        "source_lang": source_lang,
        "target_lang": target_lang,
    }
    response = requests.post(
        "https://api-free.deepl.com/v2/translate",
        headers=headers,
        data=payload,
    )
    if response.status_code != 200:
        print(response.json())
        print(f"Error: DeepL API responsed {response.status_code}")
        exit(1)

    return response.json()["translations"][0]["text"]


def make_unmasked_text(masked_text: str, mask_dict: dict) -> str:
    for mask, expr in mask_dict.items():
        expr = re.sub(r"\\", r"\\\\", expr)  # escape backslashes
        masked_text = re.sub(mask, expr, masked_text, flags=re.IGNORECASE)
    return masked_text


def main():
    parser = argparse.ArgumentParser(
        description="Translate and convert TeX / Mathpix Markdown"
    )
    parser.add_argument("path", type=str, help="path to input file")
    parser.add_argument("--no-copy", action="store_true", help="copy to clipboard")
    parser.add_argument("--stdout", action="store_true", help="print to stdout")
    parser.add_argument("--source", type=str, default="EN", help="source language")
    parser.add_argument("--target", type=str, default="JA", help="target language")
    args = parser.parse_args()
    path = Path(args.path)

    load_dotenv()

    with open(path, "r", encoding="utf-8") as f:
        tex = f.read()

    nodelist = parse(tex)

    # pre-translation process
    masked_text, mask_dict = make_masked_text(nodelist)
    ref_masker = ReferenceMasker()
    masked_text = ref_masker.mask(masked_text)

    with open(path.with_suffix(".mask.log"), "w", encoding="utf-8") as f:
        f.write(masked_text)

    # translation
    translated_text = translate_text(
        os.getenv("DEEPL_API_KEY"), masked_text, args.source, args.target
    )
    with open(path.with_suffix(".trans.log"), "w", encoding="utf-8") as f:
        f.write(translated_text)

    # post-translation process
    translated_text = ref_masker.unmask(translated_text)
    with open(path.with_suffix(".post.log"), "w", encoding="utf-8") as f:
        f.write(translated_text)
    output = make_unmasked_text(translated_text, mask_dict)
    with open(path.with_suffix(".out.log"), "w", encoding="utf-8") as f:
        f.write(output)

    if args.stdout:
        print(output)

    if not args.no_copy:
        # copy to clipboard
        subprocess.run("clip.exe", input=output.encode("utf-16"), check=True)

        print("Converted text has been copied to clipboard.")


if __name__ == "__main__":
    main()
