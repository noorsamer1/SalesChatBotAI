<<<<<<< HEAD
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import ChatUI from './chat-ui.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ChatUI />
  </StrictMode>,
)
=======
import React, { useState } from 'react';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';

import ChatUI from './components/chat-ui.jsx';
import Login from './components/Login.jsx';

// Main app component with login logic
function MainApp() {
  // User state, saved in localStorage for persistence
  const [user, setUser] = useState(() => localStorage.getItem("futuretec_user") || null);

  function handleLogin({ username, token }) {
  setUser(username);
  localStorage.setItem("futuretec_user", username);
  localStorage.setItem("futuretec_token", token);
}

  function handleLogout() {
  setUser(null);
  localStorage.removeItem("futuretec_user");
  localStorage.removeItem("futuretec_token");
}

  return (
    <>
      {!user ? (
        <Login onLogin={handleLogin} />
      ) : (
        <ChatUI user={user} onLogout={handleLogout} />
      )}
    </>
  );
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <MainApp />
  </StrictMode>
);
>>>>>>> master
