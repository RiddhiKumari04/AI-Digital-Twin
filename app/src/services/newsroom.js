// src/services/newsroom.js
// Newsroom API calls:
//   POST /morning_briefing

import api from './api';

/**
 * Get morning briefing:
 *   user_id: user's email
 *   mood: current mood string
 *   locations: array of location strings
 *   extra_topics: array of topic strings
 */
export const getMorningBriefing = ({ user_id, mood, locations = [], extra_topics = [] }) =>
  api
    .post('/morning_briefing', { user_id, mood, locations, extra_topics }, { timeout: 60000 })
    .then((r) => r.data);
