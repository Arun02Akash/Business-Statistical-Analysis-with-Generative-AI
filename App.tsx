import * as React from 'react';
import { useState } from 'react'
import { API_URL } from './api_props.json';


const NewSessionForm = ({ setSession }: { setSession: (session: Session) => void }) => {
  const [formData, setFormData] = useState<{ model: string, csvFile: null | File }>({
    model: 'gpt3.5',
    csvFile: null,
  });

  const handleModelChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setFormData({ ...formData, model: e.target.value });
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    let csvFile = e.target.files ? e.target.files[0] : null;
    setFormData({ ...formData, csvFile });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.csvFile) {
      alert("Select a file");
      return;
    }
    const formDataForApi = new FormData();
    formDataForApi.append('csv_file', formData.csvFile);

    const response = fetch(`${API_URL}/new_session?model=${formData.model}`, {
      method: 'POST',
      body: formDataForApi,
    });

    response.then(res => res.json()).then(sessionId => setSession({ sessionId, model: formData.model, fileName: formData.csvFile?.name! }))

  };

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '10px', flexDirection: 'column' }}>
      <div>
        <label htmlFor="model">Select Model:</label>
        <select id="model" name="model" value={formData.model} onChange={handleModelChange}>
          <option value="llama">Llama</option>
          <option value="gpt3.5">GPT-3.5</option>
        </select>
      </div>

      <div>
        <label htmlFor="csvFile">Upload CSV File:</label>
        <input
          type="file"
          id="csvFile"
          name="csvFile"
          accept=".csv"
          onChange={handleFileChange}
        />
      </div>

      <div>
        <button type="submit">Submit</button>
      </div>
    </form>
  );
};

interface Session {
  sessionId: string;
  model: string;
  fileName: string;
}

const Answer = (props: { sessionId: string, query: string }) => {
  const [answer, setAnswer] = useState<string | null>(null);
  React.useEffect(() => {
    let url = new URL(`${API_URL}/answer_query`)
    url.searchParams.append('session_id', props.sessionId)
    url.searchParams.append('query', props.query)
    console.log('Calling API');
    fetch(url, { method: 'POST' }).then(res => res.json()).then(ans => setAnswer(ans));
  }, [])
  if (answer == null) {
    return <div style={{ backgroundColor: 'lightgreen' }}>Loading...</div>
  } else {
    return <div style={{ backgroundColor: 'lightgreen', whiteSpace: "pre-line" }}>
      {answer}
    </div>
  }
}

const Chat = (props: { sessionId: string }) => {
  const [messages, setMessages] = useState<string[]>([]);
  const [input, setInput] = useState('');

  const handleMessageSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (input.trim() === '') return;

    setMessages([...messages, input]);

    setInput('');
  };

  return (
    <div style={{ marginTop: '10px' }}>
      <div>
        {messages.map((query, index) => (
          <div key={index} style={{ marginTop: '10px' }}>
            <span style={{ backgroundColor: 'lightblue' }}>{query}</span>
            <Answer sessionId={props.sessionId} query={query} />
          </div>
        ))}
      </div>
      <form onSubmit={handleMessageSubmit} style={{ marginTop: '10px' }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a question..."
        />
        <button type="submit">Ask</button>
      </form>
    </div>
  );
};

function App() {
  const [session, setSession] = useState<Session | null>(null)

  if (session) {
    return <div>
      Model : {session.model} <br />
      File : {session.fileName} <br />
      <Chat sessionId={session.sessionId} />
    </div>
  } else {
    return <NewSessionForm setSession={setSession} />
  }
}

export default App
