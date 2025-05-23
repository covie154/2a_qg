### PROMPT LIBRARY FOR 2AQG ###

class TwoAQG_Prompts:
    def __init__(self):
        self.qn_structure = '''Below is a series of FRCR 2A specimen questions, enclosed in three backticks (```). \
        Please provide a general format to these questions with tags enclosed by <>. \
        Summarise all 11 questions into one Question.'''

        self.generate_more_qns = '''Below is a series of FRCR 2A specimen questions, enclosed in three backticks (```). \
        Please generate five more questions in a similar format to the provided questions.'''

    def debug_json(self, pre_json):
        return f'''You have received a JSON object with the following structure:
        {pre_json}

        Please debug the JSON object and provide a corrected version of the JSON object. Ensure that the JSON object is valid and follows the correct structure.'''

    def create_dx(self, input_paper):
        return f'''Below is a scientific article, enclosed in three backticks (```). \
        I'm trying to set a single best answer multiple choice question based on a clinical scenario. 
        Based on this article, name me all valid conditions/diagnoses described in this article.

        Valid conditions would include all of the following: Demographic information, clinical history and pictures of the diagnosis
        Do not include a diagnosis if it does not have all of this information above. 
        For example, if a diagnosis is listed as a differential diagnosis of only has the imaging features and no clinical history, it is not a valid diagnosis.

        Please follow the json schema below.
        It is very critical that you answer only as a JSON object and JSON stringify it as a single string. Don't include any other verbose explanations and don't include the markdown syntax anywhere.

        {{
            "Diagnoses": [
                "Diagnosis 1",
                "Diagnosis 2",
                "Diagnosis 3",
                ...]
        }}
        
        ```
        {input_paper}
        ```
        '''
    
    def choose_rare_dx(self, input_dx, no_dx=3):
        return f'''Below is a a list of diagnoses, enclosed in three backticks (```). \
        Please return the top {no_dx+2} rarest diagnoses from the list with characteristic imaging features.
        Please return your answer as a list of diagnoses in a JSON object as shown below.
        It is very critical that you answer only as a JSON object and JSON stringify it as a single string. Don't include any other verbose explanations and don't include the markdown syntax anywhere.

        {{
            "Diagnoses": [
                "Diagnosis 1",
                "Diagnosis 2",
                "Diagnosis 3",
                ...]
        }}
        ```
        {input_dx}
        ```
        '''
    
    # Create the basic question skeleton based on the provided article
    def create_qn(self, input_paper, dx_lst, no_dx=3):
        return f'''Below is a scientific article, enclosed in three backticks (```). \
        I'm trying to set a single best answer multiple choice question based on a clinical scenario. \
        Based on this article, name me a diagnosis described in this article, and provide me with the following details for this scenario: \
        <Patient_Age> <Patient_Gender> <Clinical_History> <Imaging_Modality> <Imaging_Findings> <Diagnosis>. \
        Please return {no_dx} sets of these details for {no_dx} different diagnoses described in the article.
        Where possible, choose rarer diagnoses that have characteristic imaging features. Consider the following diagnoses: {', '.join(dx_lst)}
        Please return your answer as a list of JSONs each with the following format:
        {{
            "Patient_Age": int,
            "Patient_Gender": "M"/"F",
            "Clinical_History": "Clinical History",
            "Imaging_Modality": "Imaging Modality",
            "Imaging_Findings": "Imaging Findings",
            "Diagnosis": "Diagnosis"
        }}

        It is very critical that you answer only as a JSON object and JSON stringify it as a single string. Don't include any other verbose explanations and don't include the markdown syntax anywhere.

        ```
        {input_paper}
        ```
        '''
    
    def create_text(self, clinical_scenario):
        return f'''Below is a JSON representing a clinical scenario:
        {clinical_scenario}

        I'm trying to set a single best answer multiple choice question based on a clinical scenario. \
        Use the information provided in the JSON to create the question stem in complete, concise, formal English. \
        For the gender, M should be replaced with male and F with female
        Please follow the general structure for the stem as follows:
        ```
        A <Patient_Age> year old <Patient_Gender> presents with <Clinical_History>. <Imaging_Modality> showed <Imaging_Findings>. 

        What is the most likely diagnosis?
        ```

        Please format your answer as a JSON with the following format:
        {{
            "Question_Stem": "Question Stem",
            "Diagnosis": <Diagnosis>
        }}
        It is very critical that you answer only as a JSON object and JSON stringify it as a single string. Don't include any other verbose explanations, the word json and don't include the markdown syntax anywhere.
        '''
    
    def cot_sys_1(self):
        return '''You are an AI that uses reasoning and chain of thought to generate a detailed plan to address the user's request.

        Generate a detailed plan to address the user's request.

        - Each step should be done in logical order to address the request.
        - The plan should have a dynamic number of steps, as many as needed depending on the difficulty of the task.
        - Ensure that each step is clear, specific, and focuses on one task.
        - Format the plan with each step on a new line.
        - Do not return the final answer to the user; instead, plan out how you will solve the problem.
        - Each step should be as if it's instructions or prompts to another AI to solve the problem.
        - Provide your response strictly as a JSON using the format below. It is very critical that you answer only as a JSON object and JSON stringify it as a single string. Don't include any other verbose explanations and don't include the markdown syntax anywhere.
        - generate as much steps as you think logically needed to address the request.
        Example format (do not include the word 'Step' and the number; output directly the title of the step):

        {
            "PLAN": [
                {
                    "title": "step one title",
                    "description: "step one description"
                },
                {
                    "title": "step two title",
                    "description: "step two description"
                },
                {
                    "title": "step three title",
                    "description: "step three description"
                },
                ...
            ]
        }'''
    
    def cot_prompt_1_user(self, input_paper, clinical_scenario):
        return f'''Below is a scientific article, enclosed in three backticks (```). \
        I'm trying to set a single best answer multiple choice question based on a clinical scenario. \
        The information given as follows:
        {clinical_scenario}
        Please give 4 more close but incorrect answers to the question. You don't need to label them with A-D or 1-4.
        One should be extremely close to the correct answer, and the other three should be plausible but incorrect. 
        Explain why the given answer is correct and why the other 4 are incorrect.
        Explain your answers using the information given in the article.
        ```
        {input_paper}
        ```
        '''
    
    def cot_sys_2(self, steps_so_far, steps_remaining):
        return f'''You are an assistant executing steps to address the user's request based on a given plan.

        Here are the steps done so far:
        <STEPS_DONE>
        {steps_so_far}
        </STEPS_DONE>

        Here are the remaining steps:
        <STEPS_REMAINING>
        {steps_remaining}
        </STEPS_REMAINING>

        Your task:
        - Carefully read the next step provided by the user.
        - Before executing, ensure you fully understand the user's request and the specific tasks required.
        - Break down and execute the next step precisely and in detail.
        - After execution, reflect on the result to verify its correctness.
        - Provide a detailed reflection explaining what went well, any errors found, and how you corrected them.
        - Use precise calculations or coding as needed, employing reasoning and logic as a human would.
        - Maintain consistent formatting and clarity in your response.
        - Provide your response strictly as a JSON with the format below. It is very critical that you answer only as a JSON object and JSON stringify it as a single string. Don't include any other verbose explanations and don't include the markdown syntax anywhere.

        Format:
        {{
            "NEXT_STEP": {{
                "title": "Title of the next step",
                "description": "Description of the next step",
                "EXECUTION": "Execution of the next step",
                "REFLECTION": "Detailed reflection on the execution, including any corrections"
            }}
        }}

        Important:
        - Do not skip any steps.
        - Ensure that both EXECUTION and REFLECTION sections are filled.
        - If you have completed all steps, include '<done>' in your reflection.
        '''
    
    def cot_sys_3(self, step_reasoning):
        return f'''You are an assistant tasked with providing a comprehensive answer to the user's request based on the executed plan and reflections.

        Here is the executed plan and reflections:
        <EXECUTED_PLAN>
        {step_reasoning}
        </EXECUTED_PLAN>

        Your task:
        - Provide a complete, clear, concise, and informative answer to the user's original message.
        - Incorporate insights from the reflections to improve the final answer.
        - Ensure all calculations and code are accurate.
        - Do not mention the plan, execution steps, or reflections in your final answer; just provide the direct response.
        '''

    def output_format(self):
        return f'''Please format your response as a JSON object with the following format:
        {{
            "Option_Correct": {{
                "Name": "Diagnosis",
                "Explanation": "Explanation of why this is the correct answer"
            }},
            "Option_Wrong_1": {{
                "Name": "Diagnosis",
                "Explanation": "Explanation of why this is the wrong answer"
            }},
            "Option_Wrong_2": {{
                "Name": "Diagnosis",
                "Explanation": "Explanation of why this is the wrong answer"
            }},
            "Option_Wrong_3": {{
                "Name": "Diagnosis",
                "Explanation": "Explanation of why this is the wrong answer"
            }},
            "Option_Wrong_4": {{
                "Name": "Diagnosis",
                "Explanation": "Explanation of why this is the wrong answer"
            }},
        }}
        Provide your response strictly as a JSON with the format below. It is very critical that you answer only as a JSON object and JSON stringify it as a single string. Don't include any other verbose explanations and don't include the markdown syntax anywhere.
        '''
    
    def get_facts(self, input_paper, no_facts):
        return f'''Please provide a list of {no_facts} facts or key points extracted from the article enclosed in three backticks (```). \
        Ensure that each fact is clear, concise, and directly related to the content of the article. \
        Format your response as a according to the JSON schema below. 
        Do not include any irrelevant information or verbose explanations. 
        It is very critical that you answer only as a JSON object and JSON stringify it as a single string. Don't include any other verbose explanations and don't include the markdown syntax anywhere.
        
        {{
            "Facts": [
                "Fact 1",
                "Fact 2",
                "Fact 3",
                ...
            ]
        }}
        ```
        {input_paper}
        ```
        '''
    
    def refine_qn(self, input_paper, input_qn):
        return f'''Below is a single best answer multiple choice question based on a clinical scenario. \
        Some context is also given below for reference, enclosed in three backticks (```). \
        Please make this question more difficult. This may take the form of reducing the number of clues given, or making the question stem more ambiguous. \
        Nevertheless please ensure that the provided answer is still the best answer.
        Do not place the answer in the question stem.
        Return your answer in the same JSON schema as the original question, updating the included explanation as required.
        Please retain the phrase "What is the most likely diagnosis?" in the question stem.

        {input_qn}

        ```
        {input_paper}
        ```
        '''
    
    def refine_qn_cot_1(self, input_paper, input_qn):
        return f'''Below is a single best answer multiple choice question based on a clinical scenario. \
        Some context is also given below for reference, enclosed in three backticks (```). \
        Please make this question more difficult. This may take the form of reducing the number of clues given, or making the question stem more ambiguous. \
        Nevertheless please ensure that the provided answer is still the best answer.
        Do not place the answer in the question stem.

        {input_qn}

        ```
        {input_paper}
        ```
        '''
    
    def refine_qn_cot_2(self):
        return f'''Return your final answer in the same JSON schema as the original question, updating the included explanation as required.
        Please retain the phrase "What is the most likely diagnosis?" in the question stem.
        Also include the original "Explanation_Other" field. You may copy the original explanation if it is still relevant, \
        or modify it accordingly.'''
    
    def get_doi(self, input_paper):
        return f'''Below is a scientific article, enclosed in three backticks (```). \
        Please provide the DOI of the article. The doi format is typically in the form of "doi.org/xxxx", \
        e.g. "doi.org/10.1234/abcd.1234". 

        Please return your answer as a JSON object with the following format:
        {{
            "DOI": "doi.org/xxxx"
        }}
        It is very critical that you answer only as a JSON object and JSON stringify it as a single string. Don't include any other verbose explanations and don't include the markdown syntax anywhere

        ```
        {input_paper}
        ```
        '''

# Example usage
prompts = TwoAQG_Prompts()