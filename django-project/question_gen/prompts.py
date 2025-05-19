### PROMPT LIBRARY FOR 2AQG ###
from llama_index.core.bridge.pydantic import BaseModel
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
        return f'''Below is a scientific article, enclosed in <input_paper> tags. \
        I'm trying to set a single best answer multiple choice question based on a clinical scenario. 
        Based on this article, name me all valid conditions/diagnoses described in this article.

        Valid conditions would include all of the following: Demographic information, clinical history and pictures of the diagnosis
        Do not include a diagnosis if it does not have all of this information above. 
        For example, if a diagnosis is listed as a differential diagnosis of only has the imaging features and no clinical history, it is not a valid diagnosis.

        Return your response as a JSON with the following format:
        {{
            "Diagnoses": [
                "Diagnosis 1",
                "Diagnosis 2",
                "Diagnosis 3",
                ...]
        }}
        
        <input_paper>
        {input_paper}
        </input_paper>
        '''
        
    class output_create_dx(BaseModel):
        Diagnoses: list[str]
    
    def choose_rare_dx(self, input_dx, no_dx=3):
        return f'''Below is a a list of diagnoses, enclosed in <dx> tags. \
        Please return the top {no_dx+2} rarest diagnoses from the list with characteristic imaging features.
        Return your response as a JSON with the following format:
        {{
            "Diagnoses": [
                "Diagnosis 1",
                "Diagnosis 2",
                "Diagnosis 3",
                ...]
        }}
        
        <dx>
        {input_dx}
        </dx>
        '''
    
    class output_choose_rare_dx(BaseModel):
        Diagnoses: list[str]
    
    # Create the basic question skeleton based on the provided article
    def create_qn(self, input_paper, dx_lst, no_dx=3):
        return f'''Below is a scientific article, enclosed in <input_paper> tags. \
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

        <input_paper>
        {input_paper}
        </input_paper>
        '''
        
    class output_create_qn(BaseModel):
        class one_scenario(BaseModel):
            Patient_Age: int
            Patient_Gender: str
            Clinical_History: str
            Imaging_Modality: str
            Imaging_Findings: str
            Diagnosis: str
        
        Diagnoses: list[one_scenario]
    
    def create_text(self, clinical_scenario):
        return f'''Below is a JSON representing a clinical scenario:
        {clinical_scenario}

        I'm trying to set a single best answer multiple choice question based on a clinical scenario. \
        Use the information provided in the JSON to create the question stem in complete, concise, formal English. \
        Use medical jargon where appropriate. Do not use layman language.
        For the gender, M should be replaced with male and F with female
        Please follow the general structure for the stem as follows:
        
        <question_stem_structure>
        A {{Patient_Age}} year old {{Patient_Gender}} presents with {{Clinical_History}}. {{Imaging_Modality}} showed {{Imaging_Findings}}. 

        What is the most likely diagnosis?
        </question_stem_structure>

        Please format your answer as a JSON with the following format:
        {{
            "Question_Stem": "Question Stem",
            "Diagnosis": <Diagnosis>
        }}
        '''
    
    class output_create_text(BaseModel):
        Question_Stem: str
        Diagnosis: str
    
    def cot_prompt_1_user(self, input_paper, clinical_scenario):
        return f'''Below is a scientific article, enclosed in <input_paper> tags. \
        I'm trying to set a single best answer multiple choice question based on a clinical scenario. \
        The information given as follows:
        {clinical_scenario}
        Please give 4 more close but incorrect answers to the question. You don't need to label them with A-D or 1-4.
        One should be extremely close to the correct answer, and the other three should be plausible but incorrect. 
        Explain why the given answer is correct and why the other <input_paper> tags.4 are incorrect.
        Explain your answers using the information given in the article.
        You should have a total of 5 answers.
        
        <input_paper>
        {input_paper}
        </input_paper>
        
        Please format your response as a JSON object with the following format:
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
        '''
    
    class output_cot_prompt_1_user(BaseModel):
        class one_option(BaseModel):
            Name: str
            Explanation: str
        
        Option_Correct: one_option
        Option_Wrong_1: one_option
        Option_Wrong_2: one_option
        Option_Wrong_3: one_option
        Option_Wrong_4: one_option
    
    def get_facts(self, input_paper, no_facts):
        return f'''Please provide a list of {no_facts} facts or key points extracted from the article enclosed in <input_paper> tags. \
        Ensure that each fact is clear, concise, and directly related to the content of the article. \
        Format your response as a according to the JSON schema below. 
        Do not include any irrelevant information or verbose explanations. 
        
        {{
            "Facts": [
                "Fact 1",
                "Fact 2",
                "Fact 3",
                ...
            ]
        }}
        
        <input_paper>
        {input_paper}
        </input_paper>
        '''
    
    class output_get_facts(BaseModel):
        Facts: list[str]
    
    def options_same(self, option_1, option_2):
        return f'''Below are two options, enclosed in <option_1> and <option_2> tags. \
        Your job is to determine whether these two options are essentially the same or not. \
        This means that they should refer to the same condition, even if they are phrased differently. 
        For example, "CJD" and "Creutzfeldt-Jakob disease" are the same condition, but "CJD" and "MS" are not.
        
        Please compare the two options and provide a JSON object with the following format:
        {{
            "Same": true/false
        }}
        
        <option_1>
        {option_1}
        </option_1>
        
        <option_2>
        {option_2}
        </option_2>
        '''
    
    class output_options_same(BaseModel):
        Same: bool
    
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
        return f'''Below is a single best answer multiple choice question based on a clinical scenario, enclosed in <input_qn> tags. \
        Some context is also given below for reference, enclosed in <input_paper> tags. \
        Please make this question more difficult. This may take the form of reducing the number of clues given, or making the question stem more ambiguous. \
        Nevertheless please ensure that the provided answer is still the best answer.
        Do not place the answer in the question stem.

        <input_qn>
        {input_qn}
        </input_qn>
        
        <input_paper>
        {input_paper}
        </input_paper>
        
        Return your final answer in the same JSON schema as the original question, updating the included explanation as required.
        Please retain the phrase "What is the most likely diagnosis?" in the question stem.
        Also include the original "Explanation_Other" field. This is a list of length 4\
        with each entry explaining why the wrong entries are wrong individually. \
        You may copy the original explanation if it is still relevant, \
        or modify it accordingly.
        '''
        
    '''
    dict: A dictionary containing the complete question with the following keys:
    - "Question_Stem": The stem of the question.
    - "Options": A list of option names in the shuffled order.
    - "Correct_Option_Index": The letter of the correct option.
    - "Explanation": The explanation for the correct option.
    - "Explanation_Other": A list of explanations for the incorrect options.
    '''
    
    class output_refine_qn(BaseModel):
        Question_Stem: str
        Options: list[str]
        Correct_Option_Index: str
        Explanation: str
        Explanation_Other: list[str]
        
    def get_doi(self, input_paper):
        return f'''Below is a scientific article, enclosed in <input_paper> tags. \
        Please provide the DOI of the article. The doi format is typically in the form of "doi.org/xxxx", \
        e.g. "doi.org/10.1234/abcd.1234". 

        Please return your answer as a JSON object with the following format:
        {{
            "DOI": "doi.org/xxxx"
        }}

        <input_paper>
        {input_paper}
        </input_paper>
        '''
    
    class output_get_doi(BaseModel):
        DOI: str

# Example usage
prompts = TwoAQG_Prompts()