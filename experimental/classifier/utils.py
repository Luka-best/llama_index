"""Helper functions for Titanic GPT-3 experiments."""

# form prompt, run GPT
from gpt_index.prompts.base import Prompt
import pandas as pd
from typing import Optional, Tuple
from sklearn.model_selection import train_test_split
import re
from gpt_index.langchain_helpers.chain_wrapper import openai_llm_predict


def get_train_and_eval_data(
    csv_path: str
) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
    """Get train and eval data."""
    df = pd.read_csv(csv_path)
    label_col = 'Survived'
    cols_to_drop = ["PassengerId", "Ticket", "Name", "Cabin"]
    df = df.drop(cols_to_drop, axis=1)
    labels = df.pop(label_col)
    train_df, eval_df, train_labels, eval_labels = train_test_split(df, labels, test_size=0.25, random_state=0)
    return train_df, train_labels, eval_df, eval_labels


def get_sorted_dict_str(d: dict) -> str:
    """Get sorted dict string."""
    keys = sorted(list(d.keys()))
    return "\n".join([f"{k}:{d[k]}" for k in keys])

def get_label_str(labels: pd.Series, i: int) -> str:
    """Get label string."""
    return f"{labels.name}: {labels.iloc[i]}"

def get_train_str(
    train_df: pd.DataFrame, train_labels: pd.Series, train_n: int = 10
) -> str:
    """Get train str."""
    dict_list = train_df.to_dict('records')[:train_n]
    item_list = []
    for i, d in enumerate(dict_list):
        dict_str = get_sorted_dict_str(d)
        label_str = get_label_str(train_labels, i)
        item_str = f"This is the Data:\n{dict_str}\nThis is the correct answer:\n{label_str}"
        item_list.append(item_str)

    return "\n\n".join(item_list)


def extract_float_given_response(response: str, n: int = 1) -> Optional[float]:
    """Extract number given the GPT-generated response.

    Used by tree-structured indices.

    """
    numbers = re.findall("\d+\.\d+", response)
    if len(numbers) == 0:
        return None
    else:
        return float(numbers[0])



def get_eval_preds(train_str: str, eval_df, n: int = 20):
    """Get eval preds."""
    eval_preds = []
    for i in range(n):
        eval_str = get_sorted_dict_str(eval_df.iloc[i])
        response, _ = openai_llm_predict(train_prompt, train_str=train_str, eval_str=eval_str)
        pred = extract_float_given_response(response)
        print(f'Getting preds: {i}/{n}: {pred}')
        if pred is None:
            # something went wrong, impute a 0.5 
            eval_preds.append(0.5)
        else:
            eval_preds.append(pred)
    return eval_preds
    

train_prompt_str = (
    "The following structured data is provided in \"Feature Name\":\"Feature Value\" format.\n"
    "Each datapoint describes a passenger on the Titanic.\n"
    "The task is to decide whether the passenger survived.\n"
    "Some example datapoints are given below: \n"
    "-------------------\n"
    "{train_str}\n"
    "-------------------\n"
    "Given this, predict whether the following passenger survived. "
    "Return answer as a float probability value between 0 and 1. \n"
    "{eval_str}\n"
    "Survived: "
)

train_prompt = Prompt(input_variables=["train_str", "eval_str"], template=train_prompt_str)


## prompt to summarize the data
query_str = "Which is the relationship between these features and predicting survival?"
qa_data_str = (
    "The following structured data is provided in \"Feature Name\":\"Feature Value\" format.\n"
    "Each datapoint describes a passenger on the Titanic.\n"
    "The task is to decide whether the passenger survived.\n"
    "Some example datapoints are given below: \n"
    "-------------------\n"
    "{context_str}\n"
    "-------------------\n"
    "Given this, answer the question: {query_str}"
)

qa_data_prompt = Prompt(
    input_variables=["context_str", "query_str"], template=qa_data_str
)

# prompt to refine the answer
refine_str = (
    "The original question is as follows: {query_str}\n"
    "We have provided an existing answer: {existing_answer}\n"
    "The following structured data is provided in \"Feature Name\":\"Feature Value\" format.\n"
    "Each datapoint describes a passenger on the Titanic.\n"
    "The task is to decide whether the passenger survived.\n"
    "We have the opportunity to refine the existing answer"
    "(only if needed) with some more datapoints below.\n"
    "------------\n"
    "{context_msg}\n"
    "------------\n"
    "Given the new context, refine the original answer to better "
    "answer the question. "
    "If the context isn't useful, return the original answer."
)
DEFAULT_REFINE_PROMPT = Prompt(
    input_variables=["query_str", "existing_answer", "context_msg"],
    template=refine_str,
)

