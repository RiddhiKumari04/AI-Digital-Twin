// app/src/screens/DeveloperScreen.js
import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, ScrollView,
  StyleSheet, Alert, ActivityIndicator,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import useAuth from '../hooks/useAuth';
import { debugCode } from '../services/developer';
import { colors, radii, spacing, fonts } from '../theme';

export default function DeveloperScreen({ navigation }) {
  const { user } = useAuth();
  const [code, setCode] = useState('');
  const [result, setResult] = useState('');
  const [loading, setLoading] = useState(false);

  const handleDebug = async () => {
    if (!code.trim()) return;
    setLoading(true);
    setResult('');
    try {
      const data = await debugCode({
        user_id: user.email,
        code: code.trim(),
        language: 'python'
      });
      setResult(data.debug_report || data.explanation || 'No issues found.');
    } catch (e) {
      Alert.alert('Error', e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={s.root}>
      <LinearGradient colors={['#030712', '#0c1424']} style={StyleSheet.absoluteFill} />
      <View style={s.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Ionicons name="arrow-back" size={24} color={colors.accent} />
        </TouchableOpacity>
        <Text style={s.title}>👨‍💻 Shadow Developer</Text>
      </View>

      <ScrollView contentContainerStyle={s.content}>
        <Text style={s.label}>Paste your code here:</Text>
        <TextInput
          style={s.codeInput}
          value={code}
          onChangeText={setCode}
          placeholder="# Type or paste code..."
          placeholderTextColor={colors.textMuted}
          multiline
          autoCapitalize="none"
          autoCorrect={false}
        />

        <TouchableOpacity style={s.debugBtn} onPress={handleDebug} disabled={loading}>
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <>
              <Ionicons name="bug-outline" size={20} color="#fff" />
              <Text style={s.debugBtnText}>Analyze & Debug</Text>
            </>
          )}
        </TouchableOpacity>

        {result ? (
          <View style={s.resultBox}>
            <Text style={s.resultTitle}>Analysis Report</Text>
            <Text style={s.resultText}>{result}</Text>
          </View>
        ) : null}
      </ScrollView>
    </View>
  );
}

const s = StyleSheet.create({
  root:     { flex: 1 },
  header:   { flexDirection: 'row', alignItems: 'center', gap: 12, paddingHorizontal: spacing.md, paddingTop: 54, paddingBottom: 12, borderBottomWidth: 1, borderBottomColor: colors.border },
  title:    { color: colors.text, fontSize: 20, fontWeight: '700' },
  content:  { padding: spacing.md },
  label:    { color: colors.textDim, marginBottom: 12, fontSize: 14, fontWeight: '600' },
  codeInput: {
    backgroundColor: colors.bgInput,
    borderRadius: radii.md,
    padding: 16,
    color: colors.text,
    fontFamily: fonts.mono,
    fontSize: 14,
    minHeight: 200,
    textAlignVertical: 'top',
    borderWidth: 1,
    borderColor: colors.border,
  },
  debugBtn: {
    backgroundColor: colors.accent,
    borderRadius: radii.md,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    marginTop: spacing.md,
  },
  debugBtnText: { color: '#fff', fontWeight: '700', fontSize: 16 },
  resultBox: {
    marginTop: spacing.lg,
    backgroundColor: colors.bgCard,
    borderRadius: radii.md,
    padding: 16,
    borderWidth: 1,
    borderColor: colors.borderAccent,
  },
  resultTitle: { color: colors.accent, fontWeight: '700', marginBottom: 8, fontSize: 14, textTransform: 'uppercase' },
  resultText: { color: colors.text, fontSize: 14, lineHeight: 20 },
});
