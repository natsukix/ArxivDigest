"""
run:
python -m relevancy run_all_day_paper \
  --output_dir ./data \
  --model_name="gpt-3.5-turbo-16k" \
"""
import time
import json
import os
import random
import re
import string
from datetime import datetime

import numpy as np
import tqdm
import utils


def encode_prompt(query, prompt_papers):
    """Encode multiple prompt instructions into a single string."""
    with open("src/relevancy_prompt.txt", "r", encoding="utf-8") as f:
        prompt = f.read() + "\n"
    prompt += query['interest']

    for idx, task_dict in enumerate(prompt_papers):
        (title, authors, abstract) = task_dict["title"], task_dict["authors"], task_dict["abstract"]
        if not title:
            raise
        prompt += f"###\n"
        prompt += f"{idx + 1}. Title: {title}\n"
        prompt += f"{idx + 1}. Authors: {authors}\n"
        prompt += f"{idx + 1}. Abstract: {abstract}\n"
    prompt += f"\n Generate response:\n1."
    try:
        print(prompt)
    except UnicodeEncodeError:
        print(f"Prompt length: {len(prompt)} characters (printing skipped due to encoding issue)")
    return prompt


def post_process_chat_gpt_response(paper_data, response, threshold_score=8):
    selected_data = []
    if response is None:
        return []
    
    content = response['message']['content']
    
    # デバッグ出力
    print(f"[DEBUG] Response content type: {type(content)}")
    print(f"[DEBUG] Response content length: {len(content) if content else 0}")
    print(f"[DEBUG] Response content preview: {content[:500] if content else 'EMPTY'}")
    
    # ```json ... ``` マークダウン形式を削除
    content = re.sub(r'```json\s*', '', content)
    content = re.sub(r'```\s*', '', content)
    
    import pprint
    score_items = []
    
    # 複数行の整形されたJSON形式を検出（{...}形式）
    # マルチラインJSONを検出して結合
    json_objects = []
    buffer = []
    brace_count = 0
    
    for line in content.split('\n'):
        stripped = line.strip()
        if not stripped:
            continue
            
        # 開き括弧をカウント
        brace_count += stripped.count('{') - stripped.count('}')
        buffer.append(line)
        
        # 括弧が閉じたらJSONオブジェクトとして処理
        if brace_count == 0 and buffer:
            json_str = '\n'.join(buffer)
            if 'relevancy score' in json_str.lower():
                json_objects.append(json_str)
            buffer = []
    
    # まずマルチラインJSONをパース
    if json_objects:
        try:
            for json_str in json_objects:
                score_items.append(json.loads(json_str))
        except Exception as e:
            print(f"Multi-line JSON parse error: {e}")
            # フォールバック：単一行JSONとして処理
            pass
    
    # フォールバック：単一行JSON形式の処理
    if not score_items:
        json_items = content.replace("\n\n", "\n").split("\n")
        pattern = r"^\d+\.\s*|\\"
        try:
            for line in json_items:
                if line.strip() and "relevancy score" in line.lower():
                    # 番号とドットを削除
                    clean_line = re.sub(pattern, "", line).strip()
                    # まだ番号が残っている場合は再度削除
                    clean_line = re.sub(r'^\d+\.', '', clean_line).strip()
                    if clean_line:
                        score_items.append(json.loads(clean_line))
        except Exception as e:
            print(f"Single-line JSON parse error: {e}")
            pprint.pprint([re.sub(pattern, "", line).strip() for line in json_items if "relevancy score" in line.lower()])
            raise RuntimeError("failed")
    
    pprint.pprint(score_items)
    scores = []
    for item in score_items:
        temp = item["Relevancy score"]
        if isinstance(temp, str) and "/" in temp:
            scores.append(int(temp.split("/")[0]))
        else:
            scores.append(int(temp))
    if len(score_items) != len(paper_data):
        score_items = score_items[:len(paper_data)]
        hallucination = True
    else:
        hallucination = False

    for idx, inst in enumerate(score_items):
        # if the decoding stops due to length, the last example is likely truncated so we discard it
        if scores[idx] < threshold_score:
            continue
        output_str = "Title: " + paper_data[idx]["title"] + "\n"
        output_str += "Authors: " + paper_data[idx]["authors"] + "\n"
        output_str += "Link: " + paper_data[idx]["main_page"] + "\n"
        for key, value in inst.items():
            paper_data[idx][key] = value
            output_str += str(key) + ": " + str(value) + "\n"
        paper_data[idx]['summarized_text'] = output_str
        selected_data.append(paper_data[idx])
    return selected_data, hallucination


def find_word_in_string(w, s):
    return re.compile(r"\b({0})\b".format(w), flags=re.IGNORECASE).search(s)


def process_subject_fields(subjects):
    all_subjects = subjects.split(";")
    all_subjects = [s.split(" (")[0].strip() for s in all_subjects]
    return all_subjects

def generate_relevance_score(
    all_papers,
    query,
    model_name="gpt-3.5-turbo-16k",
    threshold_score=8,
    num_paper_in_prompt=4,
    temperature=0.4,
    top_p=1.0,
    sorting=True
):
    ans_data = []
    request_idx = 1
    hallucination = False
    for id in tqdm.tqdm(range(0, len(all_papers), num_paper_in_prompt)):
        prompt_papers = all_papers[id:id+num_paper_in_prompt]
        # only sampling from the seed tasks
        prompt = encode_prompt(query, prompt_papers)

        decoding_args = utils.OpenAIDecodingArguments(
            temperature=temperature,
            n=1,
            max_tokens=128*num_paper_in_prompt, # The response for each paper should be less than 128 tokens. 
            top_p=top_p,
        )
        request_start = time.time()
        response = None
        try:
            response = utils.openai_completion(
                prompts=prompt,
                model_name=model_name,
                batch_size=1,
                decoding_args=decoding_args,
                logit_bias={"100257": -100},  # prevent the <|endoftext|> from being generated
            )
            print("Response type:", type(response))
            # OpenAI 1.3.0互換：attributeアクセスを試す
            if hasattr(response, 'message'):
                print("Response has 'message' attribute")
                content = response.message.content
            elif hasattr(response, 'text'):
                print("Response has 'text' attribute")
                content = response.text
            else:
                print("Response attributes:", dir(response))
                raise ValueError(f"Cannot extract content from response type {type(response)}")
            print("response content", content)
        except Exception as e:
            print(f"Error getting response: {e}")
            if response:
                print(f"Response object: {response}")
            raise
        request_duration = time.time() - request_start

        process_start = time.time()
        # レスポンスを辞書形式に変換（後方互換性のため）
        response_dict = {'message': {'content': response.message.content if hasattr(response, 'message') else response.text}}
        batch_data, hallu = post_process_chat_gpt_response(prompt_papers, response_dict, threshold_score=threshold_score)
        hallucination = hallucination or hallu
        ans_data.extend(batch_data)

        print(f"Request {request_idx+1} took {request_duration:.2f}s")
        print(f"Post-processing took {time.time() - process_start:.2f}s")

    if sorting:
        ans_data = sorted(ans_data, key=lambda x: int(x["Relevancy score"]), reverse=True)
    
    return ans_data, hallucination

def run_all_day_paper(
    query={"interest":"", "subjects":["Computation and Language", "Artificial Intelligence"]},
    date=None,
    data_dir="../data",
    model_name="gpt-3.5-turbo-16k",
    threshold_score=8,
    num_paper_in_prompt=8,
    temperature=0.4,
    top_p=1.0
):
    if date is None:
        date = datetime.today().strftime('%a, %d %b %y')
        # string format such as Wed, 10 May 23
    print ("the date for the arxiv data is: ", date)

    all_papers = [json.loads(l) for l in open(f"{data_dir}/{date}.jsonl", "r")]
    print (f"We found {len(all_papers)}.")

    all_papers_in_subjects = [
        t for t in all_papers
        if bool(set(process_subject_fields(t['subjects'])) & set(query['subjects']))
    ]
    print(f"After filtering subjects, we have {len(all_papers_in_subjects)} papers left.")
    ans_data = generate_relevance_score(all_papers_in_subjects, query, model_name, threshold_score, num_paper_in_prompt, temperature, top_p)
    utils.write_ans_to_file(ans_data, date, output_dir="../outputs")
    return ans_data


if __name__ == "__main__":
    query = {"interest":"""
    1. Large language model pretraining and finetunings
    2. Multimodal machine learning
    3. Do not care about specific application, for example, information extraction, summarization, etc.
    4. Not interested in paper focus on specific languages, e.g., Arabic, Chinese, etc.\n""",
    "subjects":["Computation and Language"]}
    ans_data = run_all_day_paper(query)
