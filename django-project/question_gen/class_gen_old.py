#%%
import os.path
import os
import json
import random
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.agent.openai import OpenAIAgent
from llama_index.llms.openai import OpenAI
from llama_index.core.llms import ChatMessage
import question_gen.prompts as prompts
import re
from json_repair import repair_json
import json_repair
import time
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Get the GPT_key from environment variables
gpt_key = os.environ.get('GPT_key')

# If GPT_key is not found in environment variables, raise an error
if not gpt_key:
    raise EnvironmentError("GPT_key not found in environment variables or .env file")

# Set the OpenAI API key
os.environ["OPENAI_API_KEY"] = gpt_key
prompts = prompts.TwoAQG_Prompts()

class TwoAQG:
    def __init__(self):
        self.input_paper = ""
        self.llm_json = OpenAI(model="gpt-4o-mini", temperature=0, response_format={"type": "json_object"})
        self.llm = OpenAI(model="gpt-4o-mini", temperature=0)
        self.diagnoses = []
        self.stem_json = {}
        self.final_json = {}
        self.paper_facts = []
        self.log_level = 1
        # Log 0: No logging
        # Log 1: Log basic information
        # Log 2: Log detailed information

    ### HELPERS ###
    def print_if_log_1(self, message):
        if self.log_level >= 1:
            print(message)
    
    def print_if_log_2(self, message):
        if self.log_level >= 2:
            print(message)

    def setInputPaper(self, input_paper):
        self.input_paper = input_paper
    
    def getLLMJSON(self, message_lst):
        # Send the list of messages to the LLM and get the response
        resp = self.llm_json.chat(message_lst)
        try:
            # Try to parse the response content as JSON
            resp_json = json_repair.loads(resp.message.content)
            # Return the parsed JSON object
            return resp_json
        except json.JSONDecodeError:
            # If JSON decoding fails, print an error message and the response content
            self.print_if_log_1(f'JSONDecodeError!')
            self.print_if_log_2(f'\n\nGot:\n{resp.message.content}\n\nRetrying...')
            
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
        intermediate_resp = self.llm_json.chat(messages)
        intermediate = intermediate_resp.message.content
            
        try:
            # Try to parse the corrected response content as JSON
            resp_json = json_repair.loads(intermediate)
            # Return the parsed JSON object
            return resp_json
        except json.JSONDecodeError:
            # If JSON decoding fails again, we give up
            self.print_if_log_1(f'JSONDecodeError Again!')
            self.print_if_log_2(f'\n\nGot:\n{resp.message.content}')
            raise ValueError("No valid JSON object found in the response")
        
    def generateCOT(self, user_prompt):
        """
        Generates a chain of thought (CoT) based on the provided user prompt.
        This method follows a three-part process:
        1. Creates an overall plan based on the user prompt.
        2. Generates the output for each step in the plan.
        3. Synthesizes the final output from the steps.
        Args:
            user_prompt (str): The prompt provided by the user to generate the CoT.
        Returns:
            dict: The final synthesized output in JSON format.
        """

        ### PART 1: CREATE THE OVERALL PLAN
        messages = [
            ChatMessage(role="system", content=prompts.cot_sys_1()),
            ChatMessage(role="user", content=user_prompt),
        ]
        plan_json = self.getLLMJSON(messages)
        self.print_if_log_1("Created the plan")

        ### PART 2: GENERATE THE OUTPUT FOR EACH STEP
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
                ChatMessage(role="user", content=user_prompt),
            ]

            step_json = self.getLLMJSON(messages)
            step_reasoning.append(step_json)
            self.print_if_log_1(f"Completed step {len(steps_so_far)}/{total_steps}")

        ### PART 3: SYNTHESISE OUTPUT
        messages = [
            ChatMessage(role="system", content=prompts.cot_sys_3(steps_remaining)),
            ChatMessage(role="user", content=f'{user_prompt}'),
        ]

        resp = self.llm_json.chat(messages)
        self.print_if_log_1("Completed the plan")

        return resp.message.content
    
    ############################################################################################################

    ### QUESTION GENERATION FUNCTIONS ###
    def generateDx(self, input_paper, no_dx=3):
        """
        # STEP 1# 
        Generates one or more questions based on the input paper and the specified number of diagnoses.
        Args:
            input_paper (str): The input paper (text) used to generate the question.
            no_dx (int, optional): The number of diagnoses to generate. Defaults to 3.
        Returns:
            Returns a list of JSONs containing the info for the question stems.
            
            JSON format:
            {
                "Patient_Age": int,
                "Patient_Gender": "M"/"F",
                "Clinical_History": "Clinical History",
                "Imaging_Modality": "Imaging Modality",
                "Imaging_Findings": "Imaging Findings",
                "Diagnosis": "Diagnosis"
            }
        """
        messages = [ChatMessage(role="user", content=prompts.create_dx(input_paper))]
        lst_diagnoses = self.getLLMJSON(messages)['Diagnoses']

        if lst_diagnoses is None:
            raise ValueError("No relevant diagnoses found in the input paper")
        
        if len(lst_diagnoses) < no_dx:
            no_dx = len(lst_diagnoses)
            print(f"Will only generate {no_dx} question(s) due to insufficient data")

        messages = [ChatMessage(role="user", content=prompts.choose_rare_dx(lst_diagnoses))]
        lst_rare = self.getLLMJSON(messages)['Diagnoses']

        self.print_if_log_2(f"Possible diagnoses: {', '.join(lst_rare)}")

        messages = [ChatMessage(role="user", content=prompts.create_qn(input_paper, lst_rare, no_dx))]
        return self.getLLMJSON(messages)

    def generateStem(self, stem_json, diagnosis):
        """
        # STEP 2 #
        Generates a question stem based on the provided diagnosis - From the JSON format to the prose format.
        Args:
            stem_json (dict): The JSON object containing the question stem information. From self.generateDx().
            diagnosis (str): The diagnosis information used to generate the question stem.
        Returns:
            dict: A JSON object containing the question stem in JSON format.

            JSON format:
            {
                "Question_Stem": "Question stem",
                "Diagnosis": "Diagnosis"
            }
        """

        # String the question stem into prose
        messages = [ChatMessage(role="user", content=prompts.create_text(diagnosis))]
        #self.stem_json = self.getLLMJSON(messages)
        self.print_if_log_1(f"Question generated for the diagnosis: {stem_json['Diagnosis']}")
        self.print_if_log_2(json.dumps(stem_json, indent=4))

        # Return the JSON object (self.stem_json in the previous version)
        return self.getLLMJSON(messages)
    
    def generateOptions(self, input_paper, diagnosis):
        """
        # STEP 3 #
        Generates options for each question based on the given diagnosis using chain-of-thought reasoning.
        Args:
            input_paper (str): The input paper (text) used to generate options.
            diagnosis (str): The diagnosis information used to generate options.
        This method performs the following steps:
        1. Creates a user prompt using the provided diagnosis and input paper.
        2. Generates a chain-of-thought response from the language model.
        3. Constructs a series of chat messages including the user prompt, the model's response, and an output format prompt.
        4. Retrieves the final JSON output from the language model based on the constructed messages.
        Returns:
            dict: A JSON object containing the options for the question.
            JSON format:
            {
                "Option_Correct": {
                    "Name": "Correct Option",
                    "Explanation": "Explanation of the correct option"
                },
                "Option_Wrong_1": {
                    "Name": "Wrong Option 1",
                    "Explanation": "Explanation of the wrong option 1"
                },
                "Option_Wrong_2": {
                    "Name": "Wrong Option 2",
                    "Explanation": "Explanation of the wrong option 2"
                },
                "Option_Wrong_3": {
                    "Name": "Wrong Option 3",
                    "Explanation": "Explanation of the wrong option 3"
                },
                "Option_Wrong_4": {
                    "Name": "Wrong Option 4",
                    "Explanation": "Explanation of the wrong option 4"
                }
            }
        """

        # Use chain-of-thought reasoning to create all the options for each question
        self.print_if_log_1("Generating options...")
        user_prompt = prompts.cot_prompt_1_user(input_paper, diagnosis)
        llm_resp_cot = self.generateCOT(user_prompt)

        messages = [
            ChatMessage(role='user', content=user_prompt),
            ChatMessage(role='assistant', content=llm_resp_cot),
            ChatMessage(role='user', content=prompts.output_format())
        ]
        
        #self.final_json = self.getLLMJSON(messages)
        self.print_if_log_2(json.dumps(self.final_json, indent=4))

        # Return the JSON object (self.final_json in the previous version)
        return self.getLLMJSON(messages)
    
    def completeQuestion(self, stem_json, final_json):
        """
        # STEP 4 #
        Constructs a complete question dictionary from the provided JSON data, shuffles the options, 
        and ensures the correct option is identified.
        The method performs the following steps:
        1. Extracts the question stem, correct answer, and options from the JSON data.
        2. Asserts that the correct answer matches the name of the correct option.
        3. Shuffles the options to randomize their order.
        4. Identifies the letter of the correct option after shuffling.
        5. Constructs the final question dictionary with the shuffled options, correct option index, 
           and explanations for each option.
        6. Prints the final question dictionary in a formatted JSON string.
        Returns:
            dict: A dictionary containing the complete question with the following keys:
                - "Question_Stem": The stem of the question.
                - "Options": A list of option names in the shuffled order.
                - "Correct_Option_Index": The letter of the correct option.
                - "Explanation": The explanation for the correct option.
                - "Explanation_Other": A list of explanations for the incorrect options.
        """
        
        # Putting everything together
        question_stem = stem_json['Question_Stem']
        answer = stem_json['Diagnosis']
        correct_option = final_json['Option_Correct']
        wrong_option_1 = final_json['Option_Wrong_1']
        wrong_option_2 = final_json['Option_Wrong_2']
        wrong_option_3 = final_json['Option_Wrong_3']
        wrong_option_4 = final_json['Option_Wrong_4']

        ## We should ensure that answer and correct_option['Name'] are the same
        assert answer.lower() == correct_option['Name'].lower()

        options = [
            {"option": "a", "content": correct_option},
            {"option": "b", "content": wrong_option_1},
            {"option": "c", "content": wrong_option_2},
            {"option": "d", "content": wrong_option_3},
            {"option": "e", "content": wrong_option_4},
        ]

        random.shuffle(options)

        # Find the correct option after shuffling
        final_question = {
            "Question_Stem": question_stem,
            "Options": {opt["option"]: opt["content"]["Name"] for opt in options},
            "Correct_Option_Index": options.index(next(opt for opt in options if opt["content"]["Name"].lower() == answer.lower())),
            "Explanation": correct_option["Explanation"],
            "Explanation_Other": [
                f"{wrong_option_1['Name']}: {wrong_option_1['Explanation']}", 
                f"{wrong_option_2['Name']}: {wrong_option_2['Explanation']}",
                f"{wrong_option_3['Name']}: {wrong_option_3['Explanation']}",
                f"{wrong_option_4['Name']}: {wrong_option_4['Explanation']}"
            ]
        }

        final_question["Options"] = [opt["content"]["Name"] for opt in options]

        self.print_if_log_1("Initial question generated")
        self.print_if_log_2(json.dumps(final_question, indent=4))
        self.print_if_log_2('\n**************************************\n')
        return final_question
    
    def refineQuestion(self, input_qn):
        # Non-COT refining
        # Deprecated
        messages = [ChatMessage(role="system", content=prompts.refine_qn(self.input_paper, input_qn))]
        modified_json = self.getLLMJSON(messages)
        
        self.print_if_log_1("Final question generated")
        self.print_if_log_2(json.dumps(modified_json, indent=4))
        return modified_json

    def refineQuestionCOT(self, input_paper, input_qn):
        """
        # STEP 5 #
        Refines a given question using a Chain-of-Thought (COT) approach.
        Args:
            input_qn (str): The initial question to be refined.
        Returns:
            dict: A JSON object containing the refined question.

            JSON format:
            {
                "Question_Stem": "The refined question stem",
                "Options": ["Option A", "Option B", "Option C", "Option D"],
                "Correct_Option_Index": 0,
                "Explanation": "Explanation of the correct option",
                "Explanation_Other": ["Explanation of option B", "Explanation of option C", "Explanation of option D"]
            }
        Workflow:
            1. Generates a user prompt using the initial question and input paper.
            2. Obtains a COT response from the language model.
            3. Constructs a series of chat messages including the user prompt, COT response, and a follow-up prompt.
            4. Sends the chat messages to the language model to get a refined question in JSON format.
            5. Logs the final refined question if logging is enabled.
        """

        user_prompt = prompts.refine_qn_cot_1(input_paper, input_qn)
        llm_resp_cot = self.generateCOT(user_prompt)

        messages = [
            ChatMessage(role='user', content=user_prompt),
            ChatMessage(role='assistant', content=llm_resp_cot),
            ChatMessage(role='user', content=prompts.refine_qn_cot_2())
        ]
        
        mod_json = self.getLLMJSON(messages)

        self.print_if_log_1("Final question:")
        self.print_if_log_1(json.dumps(mod_json, indent=4))
        return mod_json
    
    def generateQuestion(self, no_dx=3):
        """
        Generates a set of questions based on the number of diagnoses provided.
        Args:
            no_dx (int, optional): The number of diagnoses to generate questions for. Defaults to 3.
        Returns:
            None
        """

        diagnoses = self.generateDx(self.input_paper, no_dx)
        output_dx_lst = []

        for dx in diagnoses:
            # Track the start time
            start_time = time.time()

            # Generate the question
            qn_stem = self.generateStem(dx, dx['Diagnosis'])
            qn_options = self.generateOptions(self.input_paper, dx['Diagnosis'])
            init_qn = self.completeQuestion(qn_stem, qn_options)
            modified_qn = self.refineQuestionCOT(init_qn, self.input_paper)
            output_dx_lst.append(modified_qn)

            # Track the end time
            end_time = time.time()
            # Calculate the time taken
            time_taken = end_time - start_time
            time_taken_min_sec = [int(time_taken // 60), int(time_taken % 60)]
            self.print_if_log_1(f'Time taken: {time_taken_min_sec[0]} mins {time_taken_min_sec[1]} secs')

        return output_dx_lst
    
    def generateFacts(self, input_paper, no_facts=10):
        resp = self.getLLMJSON([ChatMessage(role="user", content=prompts.get_facts(input_paper, no_facts))])
        self.paper_facts = resp['Facts']
        return self.paper_facts
    
    def getDOI(self, input_paper):
        resp = self.getLLMJSON([ChatMessage(role="user", content=prompts.get_doi(input_paper))])
        return resp['DOI']
    
    def displayPlaintextQuestion(self, question_dict):
        """
        Returns a question in plaintext format.
        Args:
            question_dict (dict): A dictionary containing the question information.
        """
        output = question_dict["Question_Stem"] + '\n'
        for idx, option in enumerate(question_dict["Options"]):
            output += f"{chr(65 + idx)}. {option}\n"
        
        output += '\n******************************************\n\n'
        output += f"Correct Option: {chr(65 + question_dict['Correct_Option_Index'])}\n\n"
        output += f"Explanation:\n{question_dict['Explanation']}\n\n"
        output += '\n\n'.join(question_dict['Explanation_Other'])

        return output

# %%
