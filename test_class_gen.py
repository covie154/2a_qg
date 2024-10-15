#%%
from llama_index.core import SimpleDirectoryReader
import class_gen

# Load the documents using SimpleDirectoryReader
documents = SimpleDirectoryReader("./docs_rag").load_data()

# Get the text of the document
doc_text = [x.text for x in documents]
doc_text_1 = '\n'.join(doc_text)

# Instantiate the TwoAQG class
TwoAQG = class_gen.TwoAQG()
TwoAQG.log_level = 2

# Set the input paper
TwoAQG.setInputPaper(doc_text_1)
# Get facts
ten_facts = TwoAQG.generateFacts()
print(ten_facts)
# Generate three questions
three_qns = TwoAQG.generateQuestion(3)
# %%
