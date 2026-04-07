// app/src/screens/GoalsScreen.js
import React, { useState, useEffect } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, FlatList,
  StyleSheet, Alert, ActivityIndicator,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import useAuth from '../hooks/useAuth';
import { getGoals, addGoal, updateGoal, deleteGoal } from '../services/goals';
import { colors, radii, spacing } from '../theme';

export default function GoalsScreen({ navigation }) {
  const { user } = useAuth();
  const [goals, setGoals] = useState([]);
  const [newGoal, setNewGoal] = useState('');
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    try {
      const data = await getGoals(user.email);
      setGoals(data?.goals || []);
    } catch (e) { Alert.alert('Error', e.message); }
  };

  useEffect(() => { refresh(); }, []);

  const handleAdd = async () => {
    if (!newGoal.trim()) return;
    setLoading(true);
    try {
      await addGoal({ user_id: user.email, goal: newGoal.trim(), category: 'Global' });
      setNewGoal('');
      refresh();
    } catch (e) { Alert.alert('Error', e.message); }
    finally { setLoading(false); }
  };

  const handleToggle = async (goal) => {
    const nextProg = goal.progress >= 100 ? 0 : goal.progress + 25;
    try {
      await updateGoal({ goal_id: goal._id || goal.id, progress: nextProg });
      refresh();
    } catch (e) { Alert.alert('Error', e.message); }
  };

  return (
    <View style={s.root}>
      <LinearGradient colors={['#030712', '#0c1424']} style={StyleSheet.absoluteFill} />
      <View style={s.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Ionicons name="arrow-back" size={24} color={colors.accent} />
        </TouchableOpacity>
        <Text style={s.title}>🎯 Goals & Habits</Text>
      </View>

      <View style={s.addRow}>
        <TextInput
          style={s.input}
          value={newGoal}
          onChangeText={setNewGoal}
          placeholder="New habit or goal..."
          placeholderTextColor={colors.textMuted}
        />
        <TouchableOpacity style={s.addBtn} onPress={handleAdd} disabled={loading}>
          {loading ? <ActivityIndicator color="#fff" /> : <Ionicons name="add" size={24} color="#fff" />}
        </TouchableOpacity>
      </View>

      <FlatList
        data={goals}
        keyExtractor={(item, index) => item._id || index.toString()}
        contentContainerStyle={{ padding: spacing.md }}
        renderItem={({ item }) => (
          <TouchableOpacity style={s.card} onPress={() => handleToggle(item)}>
            <View style={{ flex: 1 }}>
              <Text style={s.goalText}>{item.goal}</Text>
              <View style={s.progressRow}>
                <View style={[s.progressBar, { width: `${item.progress}%` }]} />
              </View>
            </View>
            <Text style={s.percentText}>{item.progress}%</Text>
          </TouchableOpacity>
        )}
      />
    </View>
  );
}

const s = StyleSheet.create({
  root:     { flex: 1 },
  header:   { flexDirection: 'row', alignItems: 'center', gap: 12, paddingHorizontal: spacing.md, paddingTop: 54, paddingBottom: 12, borderBottomWidth: 1, borderBottomColor: colors.border },
  title:    { color: colors.text, fontSize: 20, fontWeight: '700' },
  addRow:   { flexDirection: 'row', padding: spacing.md, gap: 10 },
  input:    { flex: 1, backgroundColor: colors.bgInput, borderRadius: radii.md, padding: 14, color: colors.text, borderWidth: 1, borderColor: colors.border },
  addBtn:   { width: 48, height: 48, borderRadius: 24, backgroundColor: colors.accent, justifyContent: 'center', alignItems: 'center' },
  card:     { backgroundColor: colors.bgCard, borderRadius: radii.md, padding: 16, marginBottom: spacing.sm, borderWidth: 1, borderColor: colors.border, flexDirection: 'row', alignItems: 'center', gap: 12 },
  goalText: { color: colors.text, fontSize: 16, fontWeight: '600', marginBottom: 8 },
  progressRow: { height: 6, backgroundColor: colors.bgInput, borderRadius: 3, overflow: 'hidden' },
  progressBar: { height: '100%', backgroundColor: colors.accent },
  percentText: { color: colors.accent, fontWeight: '700', fontSize: 14 },
});
