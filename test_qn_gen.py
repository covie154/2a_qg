#%%
import logging
import sys
import os.path
import os
import json
import random
from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    load_index_from_storage,
)
from llama_index.llms.openai import OpenAI
from llama_index.agent.openai import OpenAIAgent
from llama_index.llms.openai import OpenAI
from llama_index.core.llms import ChatMessage
import prompts
import re

gpt_key = os.environ.get('GPT_key')
os.environ["OPENAI_API_KEY"] = gpt_key

with open('Papers/2a_specimen_rcr.txt', 'r') as file:
    twoa_specimen_rcr = file.read()

prompts = prompts.TwoAQG_Prompts()

'''
    General format for a type 1 question:
    <Patient_Age> <Patient_Gender> <Clinical>. <Imaging>. 
    What is the most likely diagnosis?
    (a) <Option_A>
    (b) <Option_B>
    (c) <Option_C>
    (d) <Option_D>
    (e) <Option_E>

    Ans: <Correct_Answer>

    Other options instead of diagnosis:
    - The avulsion of which muscle is most likely to have caused this injury? - Causative organ/structure
    - Which vessel should be catheterised to maximise the chance of demonstrating the bleeding point and what would be the most likely cause of this?
    - What is the least likely diagnosis?
    - On T1-weighted images, by what is a recurrent L5/S1 disc prolapse indicated?
    - Clinical findings, then What is most likely to be found on imaging?
'''

with open('Papers/Radiographics Splenic Lesions.txt', 'r') as file:
    rg_splenic = file.read()

# Uncomment to enable Logging
#logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
#logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

'''
# LLamaIndex RAG code
# check if storage already exists
PERSIST_DIR = "./storage"
if not os.path.exists(PERSIST_DIR):
    # load the documents and create the index
    documents = SimpleDirectoryReader("data").load_data()
    index = VectorStoreIndex.from_documents(documents)
    # store it for later
    index.storage_context.persist(persist_dir=PERSIST_DIR)
else:
    # load the existing index
    storage_context = StorageContext.from_defaults(persist_dir=PERSIST_DIR)
    index = load_index_from_storage(storage_context)


llm = OpenAI(model="gpt-4o-mini", temperature=0)
query_engine = index.as_query_engine()
response = query_engine.query("What did the author do growing up?")
print(response)
'''
llm_json = OpenAI(model="gpt-4o-mini", temperature=0, response_format={"type": "json_object"})
llm = OpenAI(model="gpt-4o-mini", temperature=0)

def getLLMJSON(message_lst):
    # Send the list of messages to the LLM and get the response
    resp = llm_json.chat(message_lst)
    try:
        # Try to parse the response content as JSON
        resp_json = json.loads(resp.message.content)
        # Return the parsed JSON object
        return resp_json
    except json.JSONDecodeError:
        # If JSON decoding fails, print an error message and the response content
        print(f'JSONDecodeError!\n\nGot:\n{resp.message.content}\n\nRetrying...')
        
    # Attempt to find a valid JSON object within the response content using regex
    match = re.search(r'\{.*\}', resp.message.content, re.DOTALL)
    if match:
        # If a valid JSON object is found, parse it
        intermediate = match.group()
    else:
        # If no valid JSON object is found, print an error message
        print('No valid JSON object found in the response. Retrying...')
        
        # Ask the LLM for help
        messages = [ChatMessage(role="user", content=prompts.debug_json(resp.message.content))]
        intermediate_resp = llm_json.chat(messages)
        intermediate = intermediate_resp.message.content
        
    try:
        # Try to parse the corrected response content as JSON
        resp_json = json.loads(intermediate)
        # Return the parsed JSON object
        return resp_json
    except json.JSONDecodeError:
        # If JSON decoding fails again, we give up
        print(f'JSONDecodeError Again!\n\nGot:\n{resp.message.content}')
        raise ValueError("No valid JSON object found in the response")

messages = [ChatMessage(role="user", content=prompts.create_qn(rg_splenic))]
three_diagnoses = getLLMJSON(messages)

#%%
# String the question stem into prose
messages = [ChatMessage(role="user", content=prompts.create_text(three_diagnoses[0]))]
stem_json = getLLMJSON(messages)
print("Question generated!")
# %%
# Use chain-of-thought reasoning to create all the options for each question

### PART 1: CREATE THE OVERALL PLAN
messages = [
    ChatMessage(role="system", content=prompts.cot_sys_1()),
    ChatMessage(role="user", content=prompts.cot_prompt_1_user(rg_splenic, three_diagnoses[0])),
]
plan_json = getLLMJSON(messages)
print("Got the plan right here!")

#%%
### STEP 2: GENERATE THE OUTPUT FOR EACH STEP
steps_so_far = []
steps_remaining = plan_json['PLAN']
step_reasoning = []
total_steps = len(plan_json['PLAN'])

for step in steps_remaining:
    cot_sys_2 = prompts.cot_sys_2(steps_so_far, steps_remaining)
    steps_so_far.append(step)
    steps_remaining = steps_remaining[1:]

    messages = [
        ChatMessage(role="system", content=cot_sys_2),
        ChatMessage(role="user", content=prompts.cot_prompt_1_user(rg_splenic, three_diagnoses[0])),
    ]

    step_json = getLLMJSON(messages)
    step_reasoning.append(step_json)
    print(f"Completed step {len(steps_so_far)}/{total_steps}")

# %%
### STEP 3: SYNTHESISE OUTPUT
messages = [
    ChatMessage(role="system", content=prompts.cot_sys_3(steps_remaining)),
    ChatMessage(role="user", content=f'{prompts.cot_prompt_1_user(rg_splenic, three_diagnoses[0])}\n\n{prompts.output_format()}'),
]

final_json = getLLMJSON(messages)
# %%
# Putting everything together

question_stem = stem_json['Question_Stem']
answer = stem_json['Diagnosis']
correct_option = final_json['Option_Correct']
wrong_option_1 = final_json['Option_Wrong_1']
wrong_option_2 = final_json['Option_Wrong_2']
wrong_option_3 = final_json['Option_Wrong_3']
wrong_option_4 = final_json['Option_Wrong_4']

## We should ensure that answer and correct_option['Name'] are the same
assert answer == correct_option['Name']

options = [
    {"option": "a", "content": correct_option},
    {"option": "b", "content": wrong_option_1},
    {"option": "c", "content": wrong_option_2},
    {"option": "d", "content": wrong_option_3},
    {"option": "e", "content": wrong_option_4},
]

random.shuffle(options)

# Find the correct option after shuffling
correct_option_letter = next(opt["option"] for opt in options if opt["content"]["Name"] == answer)

final_question = {
    "Question_Stem": question_stem,
    "Options": {opt["option"]: opt["content"]["Name"] for opt in options},
    #"Correct_Option": correct_option_letter,
    "Correct_Option_Index": options.index(next(opt for opt in options if opt["content"]["Name"] == answer)),
    "Explanation": correct_option["Explanation"],
    "Explanation_Other": [
        f"{wrong_option_1['Name']}: {wrong_option_1['Explanation']}", 
        f"{wrong_option_2['Name']}: {wrong_option_2['Explanation']}",
        f"{wrong_option_3['Name']}: {wrong_option_3['Explanation']}",
        f"{wrong_option_4['Name']}: {wrong_option_4['Explanation']}"
    ]
}

final_question["Options"] = [opt["content"]["Name"] for opt in options]

print(json.dumps(final_question, indent=4))
# %%
