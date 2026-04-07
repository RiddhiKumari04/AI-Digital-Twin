// src/services/goals.js
// Goals & Habits API calls:
//   POST   /goals/add
//   GET    /goals
//   POST   /goals/update
//   DELETE /goals/:goal_id

import api from './api';

/** Add a new goal */
export const addGoal = ({ user_id, goal, category }) =>
  api.post('/goals/add', { user_id, goal, category }).then((r) => r.data);

/** List all goals for a user */
export const getGoals = (user_id) =>
  api.get('/goals', { params: { user_id } }).then((r) => r.data);

/** Update goal progress */
export const updateGoal = ({ goal_id, progress, note }) =>
  api.post('/goals/update', { goal_id, progress, note }).then((r) => r.data);

/** Delete a goal */
export const deleteGoal = ({ goal_id, user_id }) =>
  api
    .delete(`/goals/${goal_id}`, { params: { user_id } })
    .then((r) => r.data);
