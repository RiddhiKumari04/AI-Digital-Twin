// src/services/twin.js
// Twin Core API calls:
//   GET /ask            — standard AI response
//   GET /ask_stream     — SSE streaming response
//   POST /train         — store a fact in memory
//   GET /memories       — list memories
//   DELETE /memories/:id
//   POST /style_mirror  — fashion grading
//   POST /analyze_image — image analysis
//   GET /export         — export CSV
//   GET /analytics      — usage stats
//   POST /translate

import api, { BACKEND_URL } from './api';

/** Standard non-streaming ask */
export const ask = ({ user_id, question, mood = 'neutral', language = 'English', twin_mood = 'Natural' }) =>
  api
    .get('/ask', { params: { user_id, question, mood, language, twin_mood } })
    .then((r) => r.data);

/**
 * Streaming SSE ask — calls onChunk(text) for each chunk, onDone() when finished.
 * Uses fetch() directly since native EventSource has limitations.
 */
export const askStream = async ({ user_id, question, mood = 'neutral', language = 'English', twin_mood = 'Natural', onChunk, onDone, onError }) => {
  const params = new URLSearchParams({ user_id, question, mood, language, twin_mood });
  const url = `${BACKEND_URL}/ask_stream?${params.toString()}`;
  try {
    const response = await fetch(url);
    if (!response.ok || !response.body) {
      throw new Error(`HTTP ${response.status}`);
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6).trim();
          if (data === '[DONE]') { onDone?.(); return; }
          if (data) onChunk?.(data);
        }
      }
    }
    onDone?.();
  } catch (err) {
    onError?.(err);
  }
};

/** Train (store a fact about the user) */
export const train = ({ user_id, details }) =>
  api.post('/train', null, { params: { user_id, details } }).then((r) => r.data);

/** Get all memories for a user */
export const getMemories = (user_id) =>
  api.get('/memories', { params: { user_id } }).then((r) => r.data);

/** Delete a specific memory */
export const deleteMemory = ({ memory_id, user_id }) =>
  api
    .delete(`/memories/${memory_id}`, { params: { user_id } })
    .then((r) => r.data);

/** Style mirror — fashion grading via Gemini Vision (multipart form) */
export const styleMirror = ({ user_id, imageUri }) => {
  const form = new FormData();
  form.append('user_id', user_id);
  form.append('file', { uri: imageUri, name: 'photo.jpg', type: 'image/jpeg' });
  return api.post('/style_mirror', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then((r) => r.data);
};

/** Analyze image with optional question */
export const analyzeImage = ({ user_id, imageUri, question = '' }) => {
  const form = new FormData();
  form.append('user_id', user_id);
  form.append('question', question);
  form.append('file', { uri: imageUri, name: 'image.jpg', type: 'image/jpeg' });
  return api.post('/analyze_image', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then((r) => r.data);
};

/** Export chat/memory data as CSV blob URL */
export const exportData = (user_id) =>
  api.get('/export', { params: { user_id }, responseType: 'blob' }).then((r) => r.data);

/** Get analytics (message counts, session counts) */
export const getAnalytics = (user_id) =>
  api.get('/analytics', { params: { user_id } }).then((r) => r.data);

/** Translate text */
export const translate = ({ text, target_language }) =>
  api.post('/translate', { text, target_language }).then((r) => r.data);
