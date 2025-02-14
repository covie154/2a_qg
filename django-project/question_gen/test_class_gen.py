#%%
import class_gen
import pkg_resources
from langchain.document_loaders import PyPDFLoader

# Load the document using PyPDFLoader
loader = PyPDFLoader("./docs_rag/document.pdf")
documents = loader.load()

# Get the text of the document
doc_text = [x.page_content for x in documents]
doc_text_1 = '\n'.join(doc_text)

# Instantiate the TwoAQG class
TwoAQG = class_gen.TwoAQG()
TwoAQG.log_level = 1

# Set the input paper
TwoAQG.setInputPaper(doc_text_1)

# Get DOI
doi = TwoAQG.getDOI()
print(f'DOI: {doi}')
# Get facts
ten_facts = TwoAQG.generateFacts()
print(ten_facts)

# Generate three questions
three_qns = TwoAQG.generateQuestion(3)

# Print the questions
print('\n\n######################################################################################\n\n')
for i, qn in enumerate(three_qns):
    print(f'Question {i+1}:\n{TwoAQG.displayPlaintextQuestion(qn)}\n\n')

# %%

# Generate a requirements.txt file
with open('requirements.txt', 'w') as f:
    for dist in pkg_resources.working_set:
        f.write(f"{dist.project_name}=={dist.version}\n")
# %%
