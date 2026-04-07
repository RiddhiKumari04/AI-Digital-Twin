// src/screens/LoginScreen.js
import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  ScrollView, ActivityIndicator, Alert, KeyboardAvoidingView, Platform,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import useAuth from '../hooks/useAuth';
import * as authService from '../services/auth';
import { colors, radii, spacing } from '../theme';

const TABS = ['Login', 'Register', 'OTP Login', 'Forgot'];

export default function LoginScreen() {
  const { signIn } = useAuth();
  const [tab, setTab]       = useState('Login');
  const [loading, setLoading] = useState(false);

  // Login fields
  const [email, setEmail]     = useState('');
  const [password, setPass]   = useState('');
  // Register
  const [name, setName]       = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPass, setRegPass] = useState('');
  // OTP Login
  const [otpEmail, setOtpEmail] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [otpSent, setOtpSent] = useState(false);
  // Forgot
  const [fpEmail, setFpEmail] = useState('');
  const [fpOtp, setFpOtp]     = useState('');
  const [fpNew, setFpNew]     = useState('');
  const [fpStep, setFpStep]   = useState(1);

  const handle = async (fn) => {
    setLoading(true);
    try { await fn(); }
    catch (e) { Alert.alert('Error', e.message); }
    finally { setLoading(false); }
  };

  const doLogin = () => handle(async () => {
    const data = await authService.login({ email, password });
    if (data.status === 'success') await signIn({ email, name: data.name });
  });

  const doRegister = () => handle(async () => {
    await authService.register({ name, email: regEmail, password: regPass });
    Alert.alert('Success', 'Account created! Please log in.');
    setTab('Login');
  });

  const doSendOtp = () => handle(async () => {
    await authService.sendLoginOtp(otpEmail);
    setOtpSent(true);
  });

  const doVerifyOtp = () => handle(async () => {
    const data = await authService.verifyLoginOtp({ email: otpEmail, otp: otpCode });
    if (data.status === 'success') await signIn({ email: otpEmail, name: data.name });
  });

  const doFpSend = () => handle(async () => {
    await authService.sendForgotOtp(fpEmail);
    setFpStep(2);
  });

  const doFpVerify = () => handle(async () => {
    await authService.verifyForgotOtp({ email: fpEmail, otp: fpOtp });
    setFpStep(3);
  });

  const doFpReset = () => handle(async () => {
    await authService.resetPassword({ email: fpEmail, otp: fpOtp, new_password: fpNew });
    Alert.alert('Success', 'Password reset! Please log in.');
    setTab('Login');
    setFpStep(1);
  });

  return (
    <LinearGradient colors={['#030712', '#0c1424']} style={s.root}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={s.scroll} keyboardShouldPersistTaps="handled">
          {/* Header */}
          <View style={s.header}>
            <Text style={s.logo}>🧠 TwinX</Text>
            <Text style={s.subtitle}>Your AI Digital Twin</Text>
          </View>

          {/* Tabs */}
          <View style={s.tabs}>
            {TABS.map((t) => (
              <TouchableOpacity key={t} style={[s.tab, tab === t && s.tabActive]} onPress={() => setTab(t)}>
                <Text style={[s.tabText, tab === t && s.tabTextActive]}>{t}</Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Content */}
          <View style={s.card}>
            {tab === 'Login' && (
              <>
                <Field label="Email" value={email} onChangeText={setEmail} keyboardType="email-address" />
                <Field label="Password" value={password} onChangeText={setPass} secure />
                <Btn label="Login" onPress={doLogin} loading={loading} />
              </>
            )}

            {tab === 'Register' && (
              <>
                <Field label="Full Name" value={name} onChangeText={setName} />
                <Field label="Email" value={regEmail} onChangeText={setRegEmail} keyboardType="email-address" />
                <Field label="Password" value={regPass} onChangeText={setRegPass} secure />
                <Btn label="Create Account" onPress={doRegister} loading={loading} />
              </>
            )}

            {tab === 'OTP Login' && (
              <>
                <Field label="Email" value={otpEmail} onChangeText={setOtpEmail} keyboardType="email-address" />
                {otpSent && <Field label="OTP Code" value={otpCode} onChangeText={setOtpCode} keyboardType="number-pad" />}
                <Btn
                  label={otpSent ? 'Verify OTP' : 'Send OTP'}
                  onPress={otpSent ? doVerifyOtp : doSendOtp}
                  loading={loading}
                />
              </>
            )}

            {tab === 'Forgot' && (
              <>
                {fpStep >= 1 && <Field label="Email" value={fpEmail} onChangeText={setFpEmail} keyboardType="email-address" editable={fpStep === 1} />}
                {fpStep >= 2 && <Field label="OTP Code" value={fpOtp} onChangeText={setFpOtp} keyboardType="number-pad" editable={fpStep === 2} />}
                {fpStep === 3 && <Field label="New Password" value={fpNew} onChangeText={setFpNew} secure />}
                <Btn
                  label={fpStep === 1 ? 'Send OTP' : fpStep === 2 ? 'Verify OTP' : 'Reset Password'}
                  onPress={fpStep === 1 ? doFpSend : fpStep === 2 ? doFpVerify : doFpReset}
                  loading={loading}
                />
              </>
            )}
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </LinearGradient>
  );
}

function Field({ label, value, onChangeText, secure, keyboardType, editable = true }) {
  return (
    <View style={{ marginBottom: spacing.md }}>
      <Text style={s.label}>{label}</Text>
      <TextInput
        style={[s.input, !editable && { opacity: 0.5 }]}
        value={value}
        onChangeText={onChangeText}
        secureTextEntry={secure}
        keyboardType={keyboardType}
        placeholderTextColor={colors.textMuted}
        editable={editable}
        autoCapitalize="none"
      />
    </View>
  );
}

function Btn({ label, onPress, loading }) {
  return (
    <TouchableOpacity style={s.btn} onPress={onPress} disabled={loading}>
      {loading
        ? <ActivityIndicator color="#fff" />
        : <Text style={s.btnText}>{label}</Text>}
    </TouchableOpacity>
  );
}

const s = StyleSheet.create({
  root:   { flex: 1 },
  scroll: { flexGrow: 1, justifyContent: 'center', padding: spacing.lg },
  header: { alignItems: 'center', marginBottom: spacing.xl },
  logo:   { fontSize: 42, fontWeight: '800', color: colors.text, letterSpacing: -1 },
  subtitle: { color: colors.textDim, fontSize: 16, marginTop: 4 },
  tabs:   { flexDirection: 'row', marginBottom: spacing.md, backgroundColor: colors.bgCard, borderRadius: radii.md, padding: 4 },
  tab:    { flex: 1, paddingVertical: 8, alignItems: 'center', borderRadius: radii.sm },
  tabActive: { backgroundColor: colors.accent },
  tabText:   { color: colors.textDim, fontSize: 12, fontWeight: '600' },
  tabTextActive: { color: '#fff' },
  card:   { backgroundColor: colors.bgCard, borderRadius: radii.lg, padding: spacing.lg, borderWidth: 1, borderColor: colors.border },
  label:  { color: colors.textDim, fontSize: 13, marginBottom: 6, fontWeight: '600' },
  input:  { backgroundColor: colors.bgInput, borderRadius: radii.sm, padding: 14, color: colors.text, fontSize: 15, borderWidth: 1, borderColor: colors.border },
  btn:    { backgroundColor: colors.accent, borderRadius: radii.md, padding: 16, alignItems: 'center', marginTop: spacing.md },
  btnText: { color: '#fff', fontWeight: '700', fontSize: 16 },
});
