// src/screens/HomeScreen.js
// Main chat screen with SSE streaming, voice, nav drawer
import React, { useState, useRef, useCallback } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, FlatList,
  StyleSheet, ActivityIndicator, KeyboardAvoidingView, Platform,
  ScrollView,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import * as Speech from 'expo-speech';
import useAuth from '../hooks/useAuth';
import { askStream } from '../services/twin';
import { saveSession } from '../services/chat';
import { colors, radii, spacing } from '../theme';
import 'react-native-get-random-values';
import { v4 as uuid } from 'uuid';
import NavDrawer from '../components/NavDrawer';

export default function HomeScreen({ navigation }) {
  const { user, signOut }       = useAuth();
  const [messages, setMessages] = useState([]);
  const [input, setInput]       = useState('');
  const [streaming, setStreaming] = useState(false);
  const [drawerOpen, setDrawer] = useState(false);
  const [voiceEnabled, setVoice] = useState(true);
  const [sessionId]             = useState(uuid());
  const listRef = useRef(null);

  const sendMessage = useCallback(async () => {
    const q = input.trim();
    if (!q || streaming) return;
    setInput('');
    const userMsg = { id: uuid(), role: 'user',      content: q,  ts: Date.now() };
    const botMsg  = { id: uuid(), role: 'assistant',  content: '', ts: Date.now() };
    setMessages((prev) => [...prev, userMsg, botMsg]);
    setStreaming(true);

    let fullResponse = '';
    await askStream({
      user_id: user.email,
      question: q,
      onChunk: (chunk) => {
        fullResponse += chunk;
        setMessages((prev) =>
          prev.map((m) => (m.id === botMsg.id ? { ...m, content: fullResponse } : m))
        );
      },
      onDone: async () => {
        setStreaming(false);
        if (voiceEnabled) {
          Speech.speak(fullResponse, { language: 'en-US', rate: 0.95 });
        }
        // Auto-save session
        try {
          const hist = [...messages, userMsg, { ...botMsg, content: fullResponse }];
          await saveSession({
            user_id: user.email,
            session_id: sessionId,
            messages: hist.map((m) => ({ role: m.role, content: m.content })),
            timestamps: hist.map((m) => m.ts),
            title: q.slice(0, 48),
          });
        } catch (_) {}
      },
      onError: (err) => {
        setStreaming(false);
        setMessages((prev) =>
          prev.map((m) => (m.id === botMsg.id ? { ...m, content: `⚠️ ${err.message}` } : m))
        );
      },
    });
  }, [input, streaming, user, voiceEnabled, messages, sessionId]);

  const renderMsg = ({ item }) => (
    <View style={[s.bubble, item.role === 'user' ? s.bubbleUser : s.bubbleBot]}>
      {item.role === 'assistant' && <Text style={s.botLabel}>🧠 TwinX</Text>}
      <Text style={s.bubbleText}>{item.content || (streaming ? '▌' : '')}</Text>
    </View>
  );

  return (
    <View style={s.root}>
      <LinearGradient colors={['#030712', '#0c1424']} style={StyleSheet.absoluteFill} />

      {/* Header */}
      <View style={s.header}>
        <TouchableOpacity onPress={() => setDrawer(true)} style={s.headerBtn}>
          <Ionicons name="menu" size={24} color={colors.accent} />
        </TouchableOpacity>
        <Text style={s.headerTitle}>🧠 TwinX</Text>
        <TouchableOpacity onPress={() => { setVoice((v) => !v); }} style={s.headerBtn}>
          <Ionicons name={voiceEnabled ? 'volume-high' : 'volume-mute'} size={22} color={voiceEnabled ? colors.accent : colors.textMuted} />
        </TouchableOpacity>
      </View>

      {/* Messages */}
      <FlatList
        ref={listRef}
        data={messages}
        keyExtractor={(m) => m.id}
        renderItem={renderMsg}
        contentContainerStyle={s.msgList}
        onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: true })}
        ListEmptyComponent={
          <View style={s.emptyBox}>
            <Text style={s.emptyTitle}>Hi, {user?.name?.split(' ')[0]}! 👋</Text>
            <Text style={s.emptySubtitle}>Ask your digital twin anything…</Text>
          </View>
        }
      />

      {/* Input */}
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <View style={s.inputRow}>
          <TextInput
            style={s.input}
            value={input}
            onChangeText={setInput}
            placeholder="Message your twin…"
            placeholderTextColor={colors.textMuted}
            multiline
            onSubmitEditing={sendMessage}
          />
          <TouchableOpacity style={s.sendBtn} onPress={sendMessage} disabled={streaming}>
            {streaming
              ? <ActivityIndicator size="small" color="#fff" />
              : <Ionicons name="send" size={20} color="#fff" />}
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>

      {/* Nav Drawer */}
      <NavDrawer open={drawerOpen} onClose={() => setDrawer(false)} navigation={navigation} user={user} onLogout={signOut} />
    </View>
  );
}

const s = StyleSheet.create({
  root:       { flex: 1 },
  header:     { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: spacing.md, paddingTop: 54, paddingBottom: 12, borderBottomWidth: 1, borderBottomColor: colors.border },
  headerTitle: { color: colors.text, fontSize: 18, fontWeight: '700' },
  headerBtn:  { padding: 8 },
  msgList:    { padding: spacing.md, paddingBottom: 20, flexGrow: 1 },
  emptyBox:   { flex: 1, alignItems: 'center', justifyContent: 'center', marginTop: 100 },
  emptyTitle: { color: colors.text, fontSize: 24, fontWeight: '700' },
  emptySubtitle: { color: colors.textDim, marginTop: 8 },
  bubble:     { maxWidth: '85%', padding: 14, borderRadius: radii.md, marginBottom: spacing.sm },
  bubbleUser: { alignSelf: 'flex-end', backgroundColor: colors.accentDim, borderWidth: 1, borderColor: colors.borderAccent },
  bubbleBot:  { alignSelf: 'flex-start', backgroundColor: colors.bgCard, borderWidth: 1, borderColor: colors.border },
  botLabel:   { color: colors.accent, fontSize: 11, fontWeight: '700', marginBottom: 4 },
  bubbleText: { color: colors.text, fontSize: 15, lineHeight: 22 },
  inputRow:   { flexDirection: 'row', alignItems: 'flex-end', padding: spacing.md, borderTopWidth: 1, borderTopColor: colors.border, gap: 10 },
  input:      { flex: 1, backgroundColor: colors.bgInput, borderRadius: radii.md, padding: 14, color: colors.text, fontSize: 15, maxHeight: 120, borderWidth: 1, borderColor: colors.border },
  sendBtn:    { width: 48, height: 48, borderRadius: 24, backgroundColor: colors.accent, justifyContent: 'center', alignItems: 'center' },
});
