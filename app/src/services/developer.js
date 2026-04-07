// src/services/developer.js
// Shadow Developer API calls:
//   POST /debug_code
//   GET  /repo_files

import api from './api';

/**
 * Debug code using AI:
 *   code: source code string
 *   language: 'python' | 'javascript' etc.
 *   context: optional extra instructions
 */
export const debugCode = ({ user_id, code, language, context = '' }) =>
  api
    .post('/debug_code', { user_id, code, language, context })
    .then((r) => r.data);

/**
 * Browse local repo or clone a GitHub URL:
 *   path: local directory path (optional)
 *   github_url: GitHub repo URL to clone (optional)
 *   user_id: user's email
 */
export const getRepoFiles = ({ user_id, path = '', github_url = '' }) =>
  api
    .get('/repo_files', { params: { user_id, path, github_url } })
    .then((r) => r.data);
