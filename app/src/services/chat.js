// src/services/chat.js
// Persistent chat session API calls:
//   POST /chat/save
//   GET  /chat/sessions
//   GET  /chat/load
//   DELETE /chat/session/:session_id

import api from './api';

/** Save or update a chat session */
export const saveSession = ({ user_id, session_id, messages, timestamps, title }) =>
  api
    .post('/chat/save', { user_id, session_id, messages, timestamps, title })
    .then((r) => r.data);

/** List all sessions for a user */
export const getSessions = (user_id) =>
  api
    .get('/chat/sessions', { params: { user_id } })
    .then((r) => r.data);

/** Load a specific session's messages */
export const loadSession = ({ user_id, session_id }) =>
  api
    .get('/chat/load', { params: { user_id, session_id } })
    .then((r) => r.data);

/** Delete a session */
export const deleteSession = ({ session_id, user_id }) =>
  api
    .delete(`/chat/session/${session_id}`, { params: { user_id } })
    .then((r) => r.data);
