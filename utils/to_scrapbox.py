import re
from typing import List, Tuple, Optional

from pylatexenc.latexwalker import (
    LatexNode,
    LatexCharsNode,
    LatexEnvironmentNode,
    LatexMacroNode,
    LatexMathNode,
    LatexGroupNode,
    LatexSpecialsNode,
)

from utils.utils import replace, get_next_mask


common_replace_patterns = [
    (re.compile("\n"), " "),  # newline
]
macro_replace_patterns = [
    # (re.compile(r"\\emph"), r"\\bold"),  # \emph{}
]
math_replace_patterns = [
    (re.compile(r"\\Big\{(.+?)\}"), r"\\Big\1"),  # \Big{}
]
env_replace_patterns = [
    (re.compile(r"\{split\}"), r"\{aligned\}"),  # split env
]
special_replace_patterns = [
    (re.compile(r"(~+)"), "[$ \1]"),  # non-breaking space
]

# macro / env to remove
macros_remove = [
    "documentclass",
    "usepackage",
    "title",
    "author",
    "date",
    "maketitle",
    "section",
    "subsection",
    "subsubsection",
    "paragraph",
    "subparagraph",
    "label",
    "ref",
    "cite",
    "footnote",
]
envs_remove = []

# macro / env to escape with ``
macros_escape = []
envs_escape = [
    "enumerate",
    "table",
    "tabular",
]

# # 中身をそのまま出力する macro / env
# macros_raw = [
#     "leftline",
#     "rightline",
#     "centerline",
# ]

mask_count = 0


def node2mask(node: LatexNode) -> Tuple[str, Optional[Tuple[str, str]]]:
    """
    Convert a LaTeX node to a Scrapbox-compatible node.

    Args:
        node (LatexNode): The LaTeX node to be converted.

    Returns:
        tuple:
            masked_expr (str): The masked expression.
            mask_pair (tuple): A tuple of the mask and the original expression. If the node is not masked, returns None.
    """
    if isinstance(node, LatexCharsNode):
        return node.chars, None

    global mask_count
    mask = get_next_mask(mask_count)
    mask_count += 1

    code = node.latex_verbatim()
    for before, after in common_replace_patterns:
        code = replace(code, before, after)

    def remove_delims(code, delims):
        code = code[len(delims[0]) : -len(delims[1])]
        return code

    if isinstance(node, LatexMathNode):
        for before, after in math_replace_patterns:
            code = replace(code, before, after)
        code = remove_delims(code, node.delimiters)
        code = f"[$ {code} ]"

    elif isinstance(node, LatexMacroNode):
        if node.macroname in macros_remove:
            return "", None
        if len(node.nodeargs) == 0:
            return "", None

        for macro in macros_escape:
            if macro in code:
                code = f"`{code}`"
                return mask, (mask, code)

        for before, after in macro_replace_patterns:
            code = replace(code, before, after)

    elif isinstance(node, LatexEnvironmentNode):
        if node.environmentname in envs_remove:
            return "", None

        for env in envs_escape:
            if env in code:
                code = f"`{code}`"
                return mask, (mask, code)

        for before, after in env_replace_patterns:
            code = replace(code, before, after)

    elif isinstance(node, LatexGroupNode):
        code = remove_delims(code, node.delimiters)

    elif isinstance(node, LatexSpecialsNode):
        if "-" in node.specials_chars:
            return node.specials_chars, None

        for before, after in special_replace_patterns:
            code = replace(code, before, after)

    else:
        raise NotImplementedError

    return mask, (mask, code)


class ReferenceMasker:
    reference_mask = "#REF#"

    def __init__(self):
        self.ref_text = ""

    def _find_reference_section(self, text):
        """
        Finds the 'References' section in the given text.

        Args:
            text (str): The text to search.

        Returns:
            tuple:
                start_pos (int): The start position of the 'References' section.
                end_pos (int): The end position of the 'References' section.
        """
        match = re.search(r"\\section\*?\{References?\}", text, flags=re.IGNORECASE)
        if not match:
            return None, None

        start_pos = match.end()
        next_section_match = re.search(r"\n\\section", text[start_pos:])
        if next_section_match:
            end_pos = start_pos + next_section_match.start()
        else:
            end_pos = len(text)

        return start_pos, end_pos

    def mask(self, text):
        """
        Masks the 'References' section in the given text to avoid translation.

        Args:
            text (str): The text containing the 'References' section.

        Returns:
            tuple:
                masked_text (str): The text with the 'References' section masked.
                ref_text (str): The text of the 'References' section.
        """
        start_pos, end_pos = self._find_reference_section(text)
        masked_text = text[:start_pos] + self.reference_mask + text[end_pos:]
        self.ref_text = text[start_pos:end_pos]  # TODO: add "References" heading

        return masked_text

    def unmask(self, masked_text):
        """
        Unmasks the 'References' section in the given text.

        Args:
            masked_text (str): The text with the 'References' section masked.
            ref_text (str): The text of the 'References' section.

        Returns:
            str: The text with the 'References' section unmasked.
        """
        return masked_text.replace(self.reference_mask, self.ref_text)
