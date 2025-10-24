import dataclasses
import logging
import math
import os
import io
import sys
import time
import json
from typing import Optional, Sequence, Union

import openai
import tqdm
from openai import OpenAI
import copy

# OpenAI 1.3.0互換性のため、シムを作成
try:
    from openai import openai_object
    StrOrOpenAIObject = Union[str, openai_object.OpenAIObject]
except ImportError:
    # OpenAI 1.3.0ではopenai_objectが存在しない
    StrOrOpenAIObject = Union[str, dict]

# OpenAI API キー設定（互換性維持）
openai_org = os.getenv("OPENAI_ORG")
if openai_org is not None:
    logging.warning(f"Note: openai.organization is deprecated in OpenAI 1.3.0")


@dataclasses.dataclass
class OpenAIDecodingArguments(object):
    max_tokens: int = 1800
    temperature: float = 0.2
    top_p: float = 1.0
    n: int = 1
    stream: bool = False
    stop: Optional[Sequence[str]] = None
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    # logprobs: Optional[int] = None


def openai_completion(
    prompts, #: Union[str, Sequence[str], Sequence[dict[str, str]], dict[str, str]],
    decoding_args: OpenAIDecodingArguments,
    model_name="text-davinci-003",
    sleep_time=2,
    batch_size=1,
    max_instances=sys.maxsize,
    max_batches=sys.maxsize,
    return_text=False,
    **decoding_kwargs,
) -> Union[Union[StrOrOpenAIObject], Sequence[StrOrOpenAIObject], Sequence[Sequence[StrOrOpenAIObject]],]:
    """Decode with OpenAI API.

    Args:
        prompts: A string or a list of strings to complete. If it is a chat model the strings should be formatted
            as explained here: https://github.com/openai/openai-python/blob/main/chatml.md. If it is a chat model
            it can also be a dictionary (or list thereof) as explained here:
            https://github.com/openai/openai-cookbook/blob/main/examples/How_to_format_inputs_to_ChatGPT_models.ipynb
        decoding_args: Decoding arguments.
        model_name: Model name. Can be either in the format of "org/model" or just "model".
        sleep_time: Time to sleep once the rate-limit is hit.
        batch_size: Number of prompts to send in a single request. Only for non chat model.
        max_instances: Maximum number of prompts to decode.
        max_batches: Maximum number of batches to decode. This argument will be deprecated in the future.
        return_text: If True, return text instead of full completion object (which contains things like logprob).
        decoding_kwargs: Additional decoding arguments. Pass in `best_of` and `logit_bias` if you need them.

    Returns:
        A completion or a list of completions.
        Depending on return_text, return_openai_object, and decoding_args.n, the completion type can be one of
            - a string (if return_text is True)
            - an openai_object.OpenAIObject object (if return_text is False)
            - a list of objects of the above types (if decoding_args.n > 1)
    """
    is_chat_model = "gpt" in model_name
    is_single_prompt = isinstance(prompts, (str, dict))
    if is_single_prompt:
        prompts = [prompts]

    if max_batches < sys.maxsize:
        logging.warning(
            "`max_batches` will be deprecated in the future, please use `max_instances` instead."
            "Setting `max_instances` to `max_batches * batch_size` for now."
        )
        max_instances = max_batches * batch_size

    prompts = prompts[:max_instances]
    num_prompts = len(prompts)
    prompt_batches = [
        prompts[batch_id * batch_size : (batch_id + 1) * batch_size]
        for batch_id in range(int(math.ceil(num_prompts / batch_size)))
    ]

    completions = []
    for batch_id, prompt_batch in tqdm.tqdm(
        enumerate(prompt_batches),
        desc="prompt_batches",
        total=len(prompt_batches),
    ):
        batch_decoding_args = copy.deepcopy(decoding_args)  # cloning the decoding_args

        backoff = 3

        while True:
            try:
                # gpt-5シリーズはmax_completion_tokensを使用
                shared_kwargs = dict(
                    model=model_name,
                    **batch_decoding_args.__dict__,
                    **decoding_kwargs,
                    request_timeout=120,  # 2分のタイムアウトを追加
                )
                
                # gpt-5シリーズの場合の調整
                if "gpt-5" in model_name:
                    # max_tokensをmax_completion_tokensに変更
                    if "max_tokens" in shared_kwargs:
                        shared_kwargs["max_completion_tokens"] = shared_kwargs.pop("max_tokens")
                    # gpt-5-nanoはtemperature, logit_biasをサポートしないため削除
                    if "nano" in model_name:
                        shared_kwargs.pop("temperature", None)
                        shared_kwargs.pop("logit_bias", None)
                
                if is_chat_model:
                    # OpenAI 1.3.0互換の処理
                    try:
                        # 互換性シムを試す
                        completion_batch = openai.ChatCompletion.create(
                            messages=[
                                {"role": "system", "content": "You are a helpful assistant."},
                                {"role": "user", "content": prompt_batch[0]}
                            ],
                            **shared_kwargs
                        )
                    except TypeError as e:
                        if "proxies" in str(e):
                            # Fallback: use OpenAI client directly with environment variable
                            api_key = os.getenv("OPENAI_API_KEY")
                            client = OpenAI(api_key=api_key)
                            response = client.chat.completions.create(
                                messages=[
                                    {"role": "system", "content": "You are a helpful assistant."},
                                    {"role": "user", "content": prompt_batch[0]}
                                ],
                                **shared_kwargs
                            )
                            # 互換性のため、response.choicesをlistに変換
                            completion_batch = type('obj', (object,), {
                                'choices': [type('obj', (object,), {'text': choice.message.content})() for choice in response.choices],
                                'usage': response.usage
                            })()
                        else:
                            raise
                else:
                    try:
                        completion_batch = openai.Completion.create(prompt=prompt_batch, **shared_kwargs)
                    except TypeError as e:
                        if "proxies" in str(e):
                            # Fallback: use OpenAI client directly
                            api_key = os.getenv("OPENAI_API_KEY")
                            client = OpenAI(api_key=api_key)
                            response = client.chat.completions.create(
                                messages=[
                                    {"role": "system", "content": "You are a helpful assistant."},
                                    {"role": "user", "content": prompt_batch[0]}
                                ],
                                **shared_kwargs
                            )
                            completion_batch = type('obj', (object,), {
                                'choices': [type('obj', (object,), {'text': choice.message.content})() for choice in response.choices],
                                'usage': response.usage
                            })()
                        else:
                            raise

                choices = completion_batch.choices
                
                for choice in choices:
                    choice.total_tokens = completion_batch.usage.total_tokens
                completions.extend(choices)
                break
            except Exception as e:
                logging.warning(f"OpenAIError: {e}.")
                if "Please reduce your prompt" in str(e):

                    batch_decoding_args.max_tokens = int(batch_decoding_args.max_tokens * 0.8)
                    logging.warning(f"Reducing target length to {batch_decoding_args.max_tokens}, Retrying...")
                elif not backoff:
                    logging.error("Hit too many failures, exiting")
                    raise e
                else:
                    backoff -= 1
                    logging.warning("Hit request rate limit; retrying...")
                    time.sleep(sleep_time)  # Annoying rate limit on requests.

    if return_text:
        completions = [completion.text for completion in completions]
    if decoding_args.n > 1:
        # make completions a nested list, where each entry is a consecutive decoding_args.n of original entries.
        completions = [completions[i : i + decoding_args.n] for i in range(0, len(completions), decoding_args.n)]
    if is_single_prompt:
        # Return non-tuple if only 1 input and 1 generation.
        (completions,) = completions
    return completions


def write_ans_to_file(ans_data, file_prefix, output_dir="./output"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    filename = os.path.join(output_dir, file_prefix + ".txt")
    with open(filename, "w") as f:
        for ans in ans_data:
            f.write(ans + "\n")
