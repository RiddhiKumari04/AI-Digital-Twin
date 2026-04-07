// src/services/calendar.js
// Calendar API calls:
//   POST   /calendar/add
//   GET    /calendar/events
//   DELETE /calendar/event/:event_id

import api from './api';

/** Add a new calendar event */
export const addEvent = ({ user_id, title, date, time, description, color }) =>
  api
    .post('/calendar/add', { user_id, title, date, time, description, color })
    .then((r) => r.data);

/** Get all events for a user */
export const getEvents = (user_id) =>
  api
    .get('/calendar/events', { params: { user_id } })
    .then((r) => r.data);

/** Delete a calendar event */
export const deleteEvent = ({ event_id, user_id }) =>
  api
    .delete(`/calendar/event/${event_id}`, { params: { user_id } })
    .then((r) => r.data);
