// src/services/health.js
// Health Check API calls:
//   GET /health/ping  — fast liveness check
//   GET /health       — full service status

import api from './api';

/** Ultra-fast liveness probe */
export const ping = () =>
  api.get('/health/ping', { timeout: 3000 }).then((r) => r.data);

/** Full health report — DB, AI providers, email */
export const getHealth = () =>
  api.get('/health', { timeout: 8000 }).then((r) => r.data);
