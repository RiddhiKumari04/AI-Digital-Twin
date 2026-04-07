// src/services/auth.js
// Auth API calls:  /register  /login  /login_otp/*  /forgot_password/*
//                  /profile/*  /auth/google/start

import api from './api';

/** Register a new user */
export const register = ({ name, email, password }) =>
  api.post('/register', { name, email, password }).then((r) => r.data);

/** Standard email + password login */
export const login = ({ email, password }) =>
  api.get('/login', { params: { email, password } }).then((r) => r.data);

/** Send passwordless OTP to email */
export const sendLoginOtp = (email) =>
  api.post('/login_otp/send', null, { params: { email } }).then((r) => r.data);

/** Verify passwordless OTP */
export const verifyLoginOtp = ({ email, otp }) =>
  api
    .post('/login_otp/verify', null, { params: { email, otp } })
    .then((r) => r.data);

/** Forgot password — step 1: send OTP */
export const sendForgotOtp = (email) =>
  api
    .post('/forgot_password/send_otp', null, { params: { email } })
    .then((r) => r.data);

/** Forgot password — step 2: verify OTP (returns otp_valid) */
export const verifyForgotOtp = ({ email, otp }) =>
  api
    .post('/forgot_password/verify_otp', null, { params: { email, otp } })
    .then((r) => r.data);

/** Forgot password — step 3: reset password */
export const resetPassword = ({ email, otp, new_password }) =>
  api
    .post('/forgot_password/reset', { email, otp, new_password })
    .then((r) => r.data);

/** Get Google OAuth start URL */
export const getGoogleAuthUrl = () =>
  api.get('/auth/google/start').then((r) => r.data.url);

/** Save profile photo (base64 string or null to remove) */
export const saveProfilePhoto = ({ user_id, pic_b64 }) =>
  api
    .post('/profile/save_photo', { user_id, pic_b64 })
    .then((r) => r.data);

/** Get profile photo (returns { pic_b64 }) */
export const getProfilePhoto = (user_id) =>
  api
    .get('/profile/get_photo', { params: { user_id } })
    .then((r) => r.data);
