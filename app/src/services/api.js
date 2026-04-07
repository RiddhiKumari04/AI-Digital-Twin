// src/services/api.js
// Base Axios client — all API calls go through here.
// Set BACKEND_URL to your deployed FastAPI backend.

import axios from 'axios';
import Constants from 'expo-constants';

// Read from app.json extra or fall back to localhost for dev
const BACKEND_URL =
  Constants.expoConfig?.extra?.BACKEND_URL ||
  process.env.EXPO_PUBLIC_BACKEND_URL ||
  'http://localhost:8000';

const api = axios.create({
  baseURL: BACKEND_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

// Intercept errors globally
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const message =
      err.response?.data?.detail || err.message || 'Network error';
    return Promise.reject(new Error(message));
  }
);

export { BACKEND_URL };
export default api;
