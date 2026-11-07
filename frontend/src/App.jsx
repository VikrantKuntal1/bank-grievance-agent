import { useState, useRef } from 'react'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

function App() {
  const [messages, setMessages] = useState([])
  const [history, setHistory] = useState([])
  const [status, setStatus] = useState('idle')
  const [reasoning, setReasoning] = useState(null)
  const [showReasoning, setShowReasoning] = useState(false)
  const [isRecording, setIsRecording] = useState(false)

  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const mediaRecorder = new MediaRecorder(stream)
    mediaRecorderRef.current = mediaRecorder
    audioChunksRef.current = []

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) {
        audioChunksRef.current.push(e.data)
      }
    }

    mediaRecorder.onstop = async () => {
      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
      await processAudio(audioBlob)
      stream.getTracks().forEach(track => track.stop())
    }

    mediaRecorder.start()
    setIsRecording(true)
    setStatus('listening')
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      setStatus('processing')
    }
  }

  const processAudio = async (audioBlob) => {
    try {
      const formData = new FormData()
      formData.append('audio', audioBlob, 'audio.webm')
      const transcribeRes = await axios.post(`${API_BASE}/transcribe`, formData)
      const userText = transcribeRes.data.text

      if (!userText.trim()) {
        setStatus('idle')
        return
      }

      setMessages(prev => [...prev, { role: 'user', text: userText }])

      const chatRes = await axios.post(`${API_BASE}/chat`, {
        message: userText,
        session_id: 'demo-session',
        history: history,
      })

      const { reply, reasoning: newReasoning, history: newHistory } = chatRes.data
      setReasoning(newReasoning)
      setHistory(newHistory)
      setMessages(prev => [...prev, { role: 'bot', text: reply }])

      setStatus('speaking')
      const speakRes = await axios.post(
        `${API_BASE}/speak`,
        { text: reply },
        { responseType: 'arraybuffer' }
      )
      const audioUrl = URL.createObjectURL(
        new Blob([speakRes.data], { type: 'audio/mpeg' })
      )
      const audio = new Audio(audioUrl)
      audio.onended = () => setStatus('idle')
      audio.play()

    } catch (err) {
      console.error('Error:', err)
      setStatus('idle')
    }
  }

  return (
    <div className="app">
      <header>
        <h1>Bank Grievance Agent</h1>
        <p className="subtitle">Voice helpline demo</p>
      </header>

      <div className="conversation">
        {messages.length === 0 && (
          <div className="empty-state">
            <p>Hold the speak button to begin</p>
          </div>
        )}
        {messages.map((msg, idx) => (
          <div key={idx} className={`bubble ${msg.role}`}>
            <span>{msg.text}</span>
          </div>
        ))}
      </div>

      <div className="controls">
        <div className="status">
          {status === 'idle' ? 'Hold to speak' :
           status === 'listening' ? 'Listening' :
           status === 'processing' ? 'Processing' :
           status === 'speaking' ? 'Responding' : ''}
        </div>

        <button
          className={`mic-button ${isRecording ? 'recording' : ''}`}
          onMouseDown={startRecording}
          onMouseUp={stopRecording}
          onTouchStart={startRecording}
          onTouchEnd={stopRecording}
        >
          SPEAK
        </button>

        <button
          className="toggle-reasoning"
          onClick={() => setShowReasoning(prev => !prev)}
        >
          {showReasoning ? 'Hide' : 'Show'} Agent Diagnostics
        </button>
      </div>

      {showReasoning && reasoning && (
        <div className="reasoning-panel">
          <h3>Agent Diagnostics</h3>
          <div className="reasoning-grid">
            <span>Intent</span><span>{reasoning.intent}</span>
            <span>Confidence</span><span>{(reasoning.confidence * 100).toFixed(0)}%</span>
            <span>Urgency</span><span>{reasoning.urgency}</span>
            <span>Sentiment</span><span>{reasoning.sentiment_score?.toFixed(2)}</span>
            <span>Escalated</span><span>{reasoning.should_escalate ? 'Yes' : 'No'}</span>
            {reasoning.escalation_reason && (
              <>
                <span>Reason</span><span>{reasoning.escalation_reason}</span>
              </>
            )}
          </div>
          {reasoning.retrieved_context?.length > 0 && (
            <div className="retrieved-docs">
              <h4>Retrieved Policy Context</h4>
              {reasoning.retrieved_context.map((ctx, i) => (
                <p key={i} className="doc-snippet">{ctx}</p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default App