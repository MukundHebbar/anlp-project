"""Student model differences needed by the existing GRPO loop."""
import json
from pathlib import Path


def family(model_path):
    kind = json.loads((Path(model_path) / 'config.json').read_text())['model_type']
    if kind not in {'llama', 'qwen3_5'}:
        raise ValueError(f'Unsupported training model_type: {kind}')
    return kind


def load_student(model_path, **kwargs):
    import transformers
    loader = (transformers.AutoModelForCausalLM if family(model_path) == 'llama'
              else transformers.Qwen3_5ForConditionalGeneration)
    return loader.from_pretrained(model_path, **kwargs)


def stop_tokens(tokenizer, model_path):
    """Preserve Qwen stop handling; use Llama's end-of-turn plus configured EOS IDs."""
    if family(model_path) == 'qwen3_5':
        return ({tokenizer.convert_tokens_to_ids(t) for t in ('<|im_end|>', '<|endoftext|>')},
                tokenizer.convert_tokens_to_ids('<|im_end|>'))
    vocab = tokenizer.get_vocab()
    end = vocab.get('<|eot_id|>')
    if end is None:
        raise ValueError('Llama instruct tokenizer has no end-of-turn token')
    path = Path(model_path) / 'generation_config.json'
    settings = json.loads(path.read_text()) if path.exists() else {}
    eos = settings.get('eos_token_id', tokenizer.eos_token_id)
    ids = eos if isinstance(eos, list) else [eos]
    return {i for i in ids if i is not None} | {end}, end
