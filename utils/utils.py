def get_next_mask(mask_count):
    """
    Get the next mask.

    Args:
        mask_count (int): The current mask count.

    Returns:
        str: The next mask.
    """
    return f"EQ{mask_count:03}"


def replace(text, re0, re1):
    return re0.sub(re1, text)
