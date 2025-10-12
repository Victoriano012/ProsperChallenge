import random
import string
import json


def get_claim_number():

    # Generate 7 random alphanumeric characters
    alphanumeric_chars = "".join(
        random.choices(string.ascii_uppercase + string.digits, k=7)
    )

    # Insert "000" at a random position within the 7 characters
    insert_pos = random.randint(0, 7)
    claim_number = (
        alphanumeric_chars[:insert_pos] + "000" + alphanumeric_chars[insert_pos:]
    )

    return claim_number


def get_system_prompt() -> str:
    claim_number = get_claim_number()
    with open("questions.json", "r") as f:
        claim_info = json.load(f)

    with open("system_prompt.txt", "r") as f:
        system_prompt = f.read().strip()

    return system_prompt.format(claim_number=claim_number, claim_info=claim_info)
