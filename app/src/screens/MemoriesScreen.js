// src/screens/MemoriesScreen.js
import React, { useState, useEffect } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, FlatList,
  StyleSheet, Alert, ActivityIndicator,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import useAuth from '../hooks/useAuth';
import { getMemories, deleteMemory, train } from '../services/twin';
import { colors, radii, spacing } from '../theme';

export default function MemoriesScreen({ navigation }) {
  const { user } = useAuth();
  const [memories, setMemories] = useState([]);
  const [fact, setFact]         = useState('');
  const [loading, setLoading]   = useState(false);

  const refresh = async () => {
    try {
      const data = await getMemories(user.email);
      setMemories(data?.memories || []);
    } catch (e) { Alert.alert('Error', e.message); }
  };

  useEffect(() => { refresh(); }, []);

  const addFact = async () => {
    if (!fact.trim()) return;
    setLoading(true);
    try {
      await train({ user_id: user.email, details: fact.trim() });
      setFact('');
      refresh();
    } catch (e) { Alert.alert('Error', e.message); }
    finally { setLoading(false); }
  };

  const remove = async (id) => {
    Alert.alert('Delete', 'Remove this memory?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: async () => {
        try { await deleteMemory({ memory_id: id, user_id: user.email }); refresh(); }
        catch (e) { Alert.alert('Error', e.message); }
      }},
    ]);
  };

  return (
    <View style={s.root}>
      <LinearGradient colors={['#030712', '#0c1424']} style={StyleSheet.absoluteFill} />
      <View style={s.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Ionicons name="arrow-back" size={24} color={colors.accent} />
        </TouchableOpacity>
        <Text style={s.title}>🧠 Memories</Text>
      </View>

      {/* Add fact */}
      <View style={s.addRow}>
        <TextInput
          style={s.input}
          value={fact}
          onChangeText={setFact}
          placeholder="Tell your twin something about you…"
          placeholderTextColor={colors.textMuted}
          multiline
        />
        <TouchableOpacity style={s.addBtn} onPress={addFact} disabled={loading}>
          {loading ? <ActivityIndicator color="#fff" size="small" /> : <Ionicons name="add" size={24} color="#fff" />}
        </TouchableOpacity>
      </View>

      <FlatList
        data={memories}
        keyExtractor={(m, i) => m.id || String(i)}
        contentContainerStyle={{ padding: spacing.md, paddingBottom: 80 }}
        renderItem={({ item }) => (
          <View style={s.card}>
            <Text style={s.cardText}>{item.document || item.text || JSON.stringify(item)}</Text>
            <TouchableOpacity onPress={() => remove(item.id)} style={s.deleteBtn}>
              <Ionicons name="trash-outline" size={18} color={colors.danger} />
            </TouchableOpacity>
          </View>
        )}
        ListEmptyComponent={<Text style={s.empty}>No memories yet. Train your twin above!</Text>}
      />
    </View>
  );
}

const s = StyleSheet.create({
  root:     { flex: 1 },
  header:   { flexDirection: 'row', alignItems: 'center', gap: 12, paddingHorizontal: spacing.md, paddingTop: 54, paddingBottom: 12, borderBottomWidth: 1, borderBottomColor: colors.border },
  title:    { color: colors.text, fontSize: 20, fontWeight: '700' },
  addRow:   { flexDirection: 'row', alignItems: 'flex-end', padding: spacing.md, gap: 10 },
  input:    { flex: 1, backgroundColor: colors.bgInput, borderRadius: radii.md, padding: 14, color: colors.text, fontSize: 15, minHeight: 50, borderWidth: 1, borderColor: colors.border },
  addBtn:   { width: 48, height: 48, borderRadius: 24, backgroundColor: colors.accent, justifyContent: 'center', alignItems: 'center' },
  card:     { backgroundColor: colors.bgCard, borderRadius: radii.md, padding: 16, marginBottom: spacing.sm, borderWidth: 1, borderColor: colors.border, flexDirection: 'row', alignItems: 'flex-start' },
  cardText: { flex: 1, color: colors.text, fontSize: 14, lineHeight: 20 },
  deleteBtn: { marginLeft: 10, padding: 4 },
  empty:    { color: colors.textDim, textAlign: 'center', marginTop: 80 },
});
