import os
from typing import Dict, List, Union
import pandas
from uuid import uuid4

DEBUG = os.getenv('DEBUG')

def generate_data_description(csv_path:str, df:pandas.DataFrame):
    dataset_descr = f'The dataset is loaded from a CSV file named "{os.path.basename(csv_path)}" and has the following fields\n'
    for column in df.columns:
        dataset_descr+=f'* {column}\n'
    return dataset_descr

def extract_code(answer:str):
    code = '';code_started=False
    for line in answer.split('\n'):
        if code_started==True:
            if '```' in line:
                return code
            code+=(line+'\n')
        else:
            if '```' in line:
                code_started=True
    return None

class ExecutionEnv:
    env={}
    result=''

    def store_result(self,*args):
        self.result += ' '.join(map(str,args)) + '\n'

    def __init__(self):
        exec('',self.env)
        self.env['print']=self.store_result

    def store(self,name:str,var:any):
        self.env[name]=var

    def exec(self,code:str):
        if DEBUG:
            print('The code is', code)
        self.result = ''
        exec(code,self.env)
        return self.result

class GPTBackend:
    system_prompt="""
You are an assistant used for business statistical analysis. 
For every user question, generate python code to answer the question.
Use print statements to give the answer. Always print complete sentences instead of just printing the result value alone.
Put the python code within triple backticks. Give python code alone and do NOT give any explanation.
Generate python code that operates on a pandas dataset stored in the global variable "df".
""".replace('\t','')
    messages=[]

    def generate_initial_prompt(self,csv_path:str, df:pandas.DataFrame):
        inital_prompt=self.system_prompt+generate_data_description(csv_path, df)
        if DEBUG:
            print('Initial prompt is')
            print(inital_prompt)
        self.messages.append({
            "role": "system",
            "content": inital_prompt
        })

    def generate_few_shot_prompt(self,examples):
        for example in examples:
            self.messages.append({
                "role": "user",
                "content" : example['question']
            })
            self.messages.append({
                "role": "assistant",
                "content": example['answer']
            })
    
    def answer(self,question:str,exec_env:ExecutionEnv):
        import openai
        self.messages.append({
            "role": "user",
            "content":question
        })
        response = openai.ChatCompletion.create(
            messages=self.messages,
            model = "gpt-3.5-turbo",
        )
        answer_message = response['choices'][0]['message']
        self.messages.append(answer_message)
        code = extract_code(answer_message['content'])
        if code is not None:
            exec_env.exec(code)
            return exec_env.result
        else:
            return answer_message['content']+'\n'

    

class LLamaBackend:
    system_prompt="""
A chat between a human and an assistant used for business statistical analysis. 
For every user question, it generates python code to answer the question.
The assistant uses print statements to give the answer.
The python code operates on a pandas dataset stored in the global variable "df".
"""
    prompt=''

    def generate_initial_prompt(self,csv_path:str, df:pandas.DataFrame):
        self.prompt = self.system_prompt+generate_data_description(csv_path, df)
        if DEBUG:
            print('Initial prompt is')
            print(self.prompt)

    def generate_few_shot_prompt(self,examples):
        self.prompt+='\n'
        for example in examples:
            self.prompt+='Human: '+example['question']+'\n'
            self.prompt+='Assistant:'+'\n'+example['answer']+'\n'
    
    def answer(self,question:str,exec_env:ExecutionEnv):
        import requests
        import json
        self.prompt+='Human: '+question+'\n'+'Assistant:\n'
        response = requests.post("http://127.0.0.1:8080/completion",
                                 data=json.dumps({
                                     "prompt":self.prompt,
                                     "stop":["Human"]
                                 })
                                )
        assert response.status_code==200
        answer_message = response.json()['content']
        self.prompt+=answer_message
        code = extract_code(answer_message)
        if code is not None:
            exec_env.exec(code)
            return exec_env.result
        else:
            return answer_message+'\n'

examples = [
{
"question": "What are the columns of the dataset?",
"answer":
'''```
print('The column names are')
for col in df.columns:
    print(col)
```
'''
},
{
"question": "How many rows are there?",
"answer":
'''```
print('There are {} rows'.format(df.shape[0]))
```
'''
},
]

class Session:
    def __init__(self, backend:Union[LLamaBackend,GPTBackend], df:pandas.DataFrame):
        self.env = ExecutionEnv()
        self.env.store('df',df)
        self.backend = backend

sessions:Dict[str,Session] = {}

from fastapi import FastAPI, HTTPException,UploadFile
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/new_session")
def new_session(model: str, csv_file:UploadFile) -> str:
    if model == 'llama':
        backend = LLamaBackend()
    else:
        backend = GPTBackend()
    
    try:
        df = pandas.read_csv(csv_file.file)
    except:
        raise HTTPException(status_code=400, detail="Invalid CSV file")
    finally:
        csv_file.file.close()
    
    backend.generate_initial_prompt(csv_file.filename,df)
    backend.generate_few_shot_prompt(examples)
    
    session_id = str(uuid4())
    sessions[session_id]=Session(backend,df)
    return session_id

@app.post("/answer_query")
def answer_query(session_id: str, query:str) -> str:
    if session_id in sessions:
        session = sessions[session_id]
        return session.backend.answer(query, session.env)
    else:
        raise HTTPException(status_code=400, detail="Invalid Session ID")

@app.post("/delete_session")
def delete_session(session_id: str):
    del sessions[session_id]
