#%%
import class_gen
import pkg_resources
from langchain.document_loaders import PyPDFLoader

# Load the document using PyPDFLoader
loader = PyPDFLoader(r"C:\Users\Covie\Downloads\fragoso-et-al-2017-imaging-of-creutzfeldt-jakob-disease-imaging-patterns-and-their-differential-diagnosis.pdf")
documents = loader.load()

# Get the text of the document
doc_text = [x.page_content for x in documents]
doc_text_1 = '\n'.join(doc_text)

# Instantiate the TwoAQG class
TwoAQG = class_gen.TwoAQG()
TwoAQG.log_level = 2

# Get DOI
# doi = TwoAQG.getDOI(doc_text_1)
# print(f'DOI: {doi}')

# Get facts
# ten_facts = TwoAQG.generateFacts(doc_text_1)
# print(ten_facts)

# Generate three questions
#three_qns = TwoAQG.generateQuestion(3)

n_qns = []
dx_lst = TwoAQG.generateDx(doc_text_1)
for dx in dx_lst:
    qn_stem = TwoAQG.generateStem(dx, dx['Diagnosis'])
    qn_options = TwoAQG.generateOptions(doc_text_1, dx['Diagnosis'])
    initial_qn = TwoAQG.completeQuestion(qn_stem, qn_options)
    final_qn = TwoAQG.refineQuestionCOT(doc_text_1, initial_qn)
    n_qns.append(final_qn)

# Print the questions
print('\n\n######################################################################################\n\n')
for i, qn in enumerate(n_qns):
    print(f'Question {i+1}:\n{TwoAQG.displayPlaintextQuestion(qn)}\n\n')

# %%

# Generate a requirements.txt file
with open('requirements.txt', 'w') as f:
    for dist in pkg_resources.working_set:
        f.write(f"{dist.project_name}=={dist.version}\n")
# %%
