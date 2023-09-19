import argparse
import os
import re
import subprocess
from pathlib import Path

import requests
from dotenv import load_dotenv
from pylatexenc.latexwalker import LatexCharsNode, LatexWalker

from utils.to_scrapbox import (
    mask_reference,
    node_to_expr,
    replace_post_translation,
    # replace_pre_translation,
    unmask_reference,
)
from utils.utils import get_next_mask


def parse(tex):
    """
    Parse the given LaTeX or Mathpix Markdown text into a list of nodes.

    Args:
        tex (str): The text to parse.

    Returns:
        list: A list of parsed nodes.
    """
    w = LatexWalker(tex)
    nodelist, *_ = w.get_latex_nodes(pos=0)
    return nodelist


def mask_codes(nodelist):
    """
    Replace non-text LaTeX elements (e.g., equations, macros) with masks to avoid translation.

    Args:
        nodelist (list): A list of parsed LaTeX nodes.

    Returns:
        tuple:
        - masked_text (str): The text with masked codes.
        - mask_dict (dict): A dictionary mapping masks to their corresponding LaTeX nodes.
    """
    masked_text = ""
    mask_dict = {}
    mask_count = 0
    for node in nodelist:
        if isinstance(node, LatexCharsNode):
            masked_text += node.chars
        else:
            mask = get_next_mask(mask_count)
            masked_text += mask
            mask_dict[mask] = node
            mask_count += 1
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


def unmask_codes(translated_text, mask_dict):
    """
    Replace the masks in the translated text with their corresponding expressions.
    The expressions are converted to desired formats.

    Args:
        translated_text (str): The text that has been translated and contains masks to be replaced.
        mask_dict (dict): A dictionary mapping masks to LaTeX nodes.

    Returns:
        unmasked (str): The translated text with all masks replaced by their corresponding expressions.
    """
    for mask, node in mask_dict.items():
        expr = node_to_expr(node)
        expr = re.sub(r"\\", r"\\\\", expr)  # escape backslashes
        translated_text = re.sub(mask, expr, translated_text, flags=re.IGNORECASE)
        # translated_text = translated_text.replace(mask, expr)
    return translated_text


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

    # pre-parse process
    tex = re.sub(r"```(.+?)```", r"\1", tex)  # remove code blocks

    nodelist = parse(tex)

    masked_text, mask_dict = mask_codes(nodelist)

    # pre-translation process
    masked_text, ref_text = mask_reference(masked_text)
    # masked_text = replace_pre_translation(masked_text)
    with open(path.with_suffix(".mask.log"), "w", encoding="utf-8") as f:
        f.write(masked_text)

    # translation
    translated_text = translate_text(
        os.getenv("DEEPL_API_KEY"), masked_text, args.source, args.target
    )
    with open(path.with_suffix(".trans.log"), "w", encoding="utf-8") as f:
        f.write(translated_text)

    # post-translation process
    translated_text = unmask_reference(translated_text, ref_text)
    translated_text = replace_post_translation(translated_text)
    with open(path.with_suffix(".post.log"), "w", encoding="utf-8") as f:
        f.write(translated_text)

    output = unmask_codes(translated_text, mask_dict)
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
