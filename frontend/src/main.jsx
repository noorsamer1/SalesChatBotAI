import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import ChatUI from './chat-ui.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ChatUI />
  </StrictMode>,
)
