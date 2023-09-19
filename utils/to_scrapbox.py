import re

from pylatexenc.latexwalker import (
    LatexCharsNode,
    LatexEnvironmentNode,
    LatexMacroNode,
    LatexMathNode,
)

from utils.utils import replace


def replace_heading(match):
    level = min(3, len(match.group(1)))
    return f"[{'*' * (4 - level)} {match.group(2)}]"


pre_translation_replace_patterns = [
    (re.compile(r"```(.+?)```", flags=re.DOTALL), r"\1"),  # codeblock
]
post_translation_replace_patterns = [
    (re.compile(r"\[(.+?)\]"), r"`[\1]`"),  # citation
    (re.compile(r"\*\*(.+?)\*\*"), r"[* \1]"),  # bold (do after citation)
    (re.compile(r"^(#+)\s*(.+?)\s*$", flags=re.MULTILINE), replace_heading),  # heading
]
code_replace_patterns = [
    (re.compile("\n"), " "),  # newline
    (re.compile(r"\\emph"), r"\\bold"),  # \emph{}
    (re.compile(r"\{split\}"), r"\{aligned\}"),  # split env
    (re.compile(r"\\Big\{(.+?)\}"), r"\\Big\1"),  # \Big{}
]

reference_mask = "#REF#"

# TODO: update
macros_unsupported = [
    "emph",
]
envs_unsupported = [
    "enumerate",
    "table",
    "tabular",
]


def replace_pre_translation(text):
    """
    Replace TeX/Markdown notations in pre-translation text with Scrapbox-compatible notations.

    Args:
        text (str): The text to be converted.

    Returns:
        str: The converted text.
    """
    for before, after in pre_translation_replace_patterns:
        text = replace(text, before, after)
    return text


def replace_post_translation(text):
    """
    Replace TeX/Markdown notations in post-translation text with Scrapbox-compatible notations.

    Args:
        text (str): The text to be converted.

    Returns:
        str: The converted text.
    """
    for before, after in post_translation_replace_patterns:
        text = replace(text, before, after)
    return text


def mask_reference(text):
    """
    Masks the 'References' section in the given text to avoid translation.

    Args:
        text (str): The text containing the 'References' section.

    Returns:
        tuple:
            masked_text (str): The text with the 'References' section masked.
            ref_text (str): The text of the 'References' section.
    """

    # find "Reference(s)" section
    match = re.search(r"#+\s*References?", text, flags=re.IGNORECASE)
    if not match:
        return text, ""

    # find the range of the section
    start_pos = match.end()
    next_section_match = re.search(r"\n#{1,3}\s*\w+", text[start_pos:])
    if next_section_match:
        end_pos = start_pos + next_section_match.start()
    else:
        end_pos = len(text)

    masked_text = text[:start_pos] + reference_mask + text[end_pos:]
    ref_text = text[start_pos:end_pos]

    return masked_text, ref_text


def unmask_reference(masked_text, ref_text):
    """
    Unmask the 'References' section in the given text.

    Args:
        text (str): The text with the 'References' section masked.
        ref_text (str): The text of the 'References' section.

    Returns:
        str: The text with the 'References' section unmasked.
    """

    return masked_text.replace(reference_mask, ref_text)


def node_to_expr(node):
    """
    Convert a LatexNode to a Scrapbox-compatible expression.

    Args:
        node (LatexNode): The LaTeX node to be converted.

    Returns:
        expr (str): The converted Scrapbox-compatible expression.
    """
    assert not isinstance(node, LatexCharsNode)

    expr = node.latex_verbatim()

    for before, after in code_replace_patterns:
        expr = replace(expr, before, after)

    if isinstance(node, LatexMathNode):
        # remove delimiters of math expressions
        expr = expr[len(node.delimiters[0]) : -len(node.delimiters[1])]

    # enclose with [$ ] if the node is supported by KaTeX
    # otherwise, enclose with ``
    def is_unsupported(node):
        if isinstance(node, LatexMacroNode):
            return node.macroname in macros_unsupported
        elif isinstance(node, LatexEnvironmentNode):
            return node.environmentname in envs_unsupported
        else:
            return False

    if not hasattr(node, "nodelist"):
        return expr

    for child in node.nodelist:
        if is_unsupported(child):
            expr = f"`{expr}`"
            break
    else:
        expr = f"[$ {expr} ]"

    return expr
