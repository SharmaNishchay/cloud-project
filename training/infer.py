"""Shared prompt format + greedy generation used for training data, evaluation and tests."""
PROMPT_FMT = "Command: {text}\nJSON:"


def build_prompt(text):
    return PROMPT_FMT.format(text=text)


def first_line(decoded):
    return decoded.strip().split("\n")[0].strip()


def generate(model, tok, text, max_new_tokens=64):
    import torch
    enc = tok(build_prompt(text), return_tensors="pt")
    with torch.no_grad():
        out = model.generate(**enc, max_new_tokens=max_new_tokens, do_sample=False,
                             pad_token_id=tok.eos_token_id, eos_token_id=tok.eos_token_id)
    new = out[0][enc["input_ids"].shape[1]:]
    return first_line(tok.decode(new, skip_special_tokens=True))
