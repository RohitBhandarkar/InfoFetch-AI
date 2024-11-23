# -*- coding: utf-8 -*-
"""main.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1D9i2py0A1Q09b8QzDymus_vWfL5HpW_o
"""

!nvidia-smi

"""# Get content"""

!pip install faiss-cpu -q
!pip install beautifulsoup4 -q

from bs4 import BeautifulSoup
import requests

query = "What is a RAG system?"
query = query.replace(' ', '+')

url = f"https://www.google.com/search?q={query}"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
}

response = requests.get(url, headers=headers)

if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    urls = []
    gfg = 0
    for g in soup.find_all('a'):
        href = g.get('href')
        if href and "/url?esrc=s&q=&rct=j&sa=U&url=" in href:
            link = href.split("/url?esrc=s&q=&rct=j&sa=U&url=")[1].split("&")[0]
            #print(link)
            #if (link.split("https://")[1].split(".")[0] != "scholar"):
            urls.append(link)
else:
    print("Failed to fetch results")

len(urls)

urls

texts = []
final_urls = []
total = 0
for url in urls:
    success = False
    while not success:
        try:
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                for tag in soup(['script', 'style', 'header', 'footer', 'nav']):
                    tag.decompose()

                page_text = ' '.join(tag.get_text() for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'li']))
                texts.append(page_text)
                success = True
                total += 1
                final_urls.append(url)
            else:
                print(f"Failed to fetch {url}: {response.status_code}")
                break
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            break

    if (total == 3):
        break

final_urls

texts

len(texts)

len(texts[0]), len(texts[1]), len(texts[2])

"""# Cleaning/Preprocessing"""

import re

def clean_text(text):
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

texts[0] = clean_text(texts[0])
texts[1] = clean_text(texts[1])
texts[2] = clean_text(texts[2])

texts

len(texts[0]), len(texts[1]), len(texts[2])

final_text = " ".join(texts)
final_text

len(final_text)



"""# Knowledge base using sentence embenddings"""

from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
import faiss # Facebook AI Similarity Seacrh
import numpy as np

model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(final_text)

n_clusters = 50
clustering = KMeans(n_clusters)
clusters = clustering.fit_predict(embeddings.reshape(-1, 1))

chunks = {i: [] for i in range(50)}
for sentence, cluster in zip(final_text, clusters):
    chunks[cluster].append(sentence)
chunks.values()

chunks

chunks = [final_text[i:i+1500] for i in range(0, len(final_text), 1500)] # chunking
embeddings = model.encode(chunks) # embeddings for each chunk
# embeddings array of the form (N,D) where N = no. of chunks and D = dim of embeddings vec

dimension = embeddings.shape[1] # extract D
index = faiss.IndexFlatL2(dimension) # initialize L2 eucidean distance for similarity b/w vecs; saying it has dimension number of dimensions for the vectors
index.add(np.array(embeddings)) # add embeddings to FAISS index; FAISS build internal struct for optimal search
print(f"Indexed {len(chunks)} chunks.")

"""# RAG pipeline

## Retrieval (3 nearest clusters using similarity search)
"""

user_query = query

query_embedding = model.encode([user_query]) # embeddings for query
D, I = index.search(query_embedding, k=3)  # top 10 closest

relevant_passages = [chunks[i] for i in I[0]]

relevant_passages_str = ''.join(relevant_passages)

relevant_passages_str

len(relevant_passages_str)

"""## Augmented generation (with RAG)"""

from transformers import AutoModelForCausalLM, AutoTokenizer

model_name = "Qwen/Qwen2.5-Coder-0.5B-Instruct"

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype="auto",
    device_map="auto"
)
tokenizer = AutoTokenizer.from_pretrained(model_name)


messages = [
    {"role": "system", "content": final_text},
    {"role": "user", "content": user_query}
]
text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True
)
model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

generated_ids = model.generate(
    **model_inputs,
    max_new_tokens=512
)
generated_ids = [
    output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
]

response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

print(response)
print("\nSources: \n")
for url in final_urls:
  print(url)



"""## Control data (same prompt without RAG)"""

from transformers import AutoModelForCausalLM, AutoTokenizer

model_name = "Qwen/Qwen2.5-Coder-0.5B-Instruct"

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype="auto",
    device_map="auto"
)
tokenizer = AutoTokenizer.from_pretrained(model_name)


messages = [
    {"role": "system", "content": "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."},
    {"role": "user", "content": user_query}
]
text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True
)
model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

generated_ids = model.generate(
    **model_inputs,
    max_new_tokens=512
)
generated_ids = [
    output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
]

response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

print(response)
