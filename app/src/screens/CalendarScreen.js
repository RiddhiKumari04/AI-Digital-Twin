// app/src/screens/CalendarScreen.js
import React, { useState, useEffect } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, FlatList,
  StyleSheet, Alert, ActivityIndicator,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import useAuth from '../hooks/useAuth';
import { getEvents, addEvent, deleteEvent } from '../services/calendar';
import { colors, radii, spacing } from '../theme';

export default function CalendarScreen({ navigation }) {
  const { user } = useAuth();
  const [events, setEvents] = useState([]);
  const [title, setTitle] = useState('');
  const [date, setDate] = useState('');
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    try {
      const data = await getEvents(user.email);
      setEvents(data?.events || []);
    } catch (e) { Alert.alert('Error', e.message); }
  };

  useEffect(() => { refresh(); }, []);

  const handleAdd = async () => {
    if (!title.trim() || !date.trim()) return;
    setLoading(true);
    try {
      await addEvent({ user_id: user.email, title: title.trim(), date: date.trim() });
      setTitle('');
      setDate('');
      refresh();
    } catch (e) { Alert.alert('Error', e.message); }
    finally { setLoading(false); }
  };

  return (
    <View style={s.root}>
      <LinearGradient colors={['#030712', '#0c1424']} style={StyleSheet.absoluteFill} />
      <View style={s.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Ionicons name="arrow-back" size={24} color={colors.accent} />
        </TouchableOpacity>
        <Text style={s.title}>📅 Calendar</Text>
      </View>

      <View style={s.inputContainer}>
        <TextInput
          style={s.input}
          value={title}
          onChangeText={setTitle}
          placeholder="What's the plan?"
          placeholderTextColor={colors.textMuted}
        />
        <TextInput
          style={s.input}
          value={date}
          onChangeText={setDate}
          placeholder="YS-MM-DD"
          placeholderTextColor={colors.textMuted}
        />
        <TouchableOpacity style={s.addBtn} onPress={handleAdd} disabled={loading}>
          {loading ? <ActivityIndicator color="#fff" /> : <Text style={s.addBtnText}>Add Event</Text>}
        </TouchableOpacity>
      </View>

      <FlatList
        data={events}
        keyExtractor={(item, index) => item._id || index.toString()}
        contentContainerStyle={{ padding: spacing.md }}
        renderItem={({ item }) => (
          <View style={s.card}>
            <View style={{ flex: 1 }}>
              <Text style={s.eventTitle}>{item.title}</Text>
              <Text style={s.eventDate}>{item.date}</Text>
            </View>
            <TouchableOpacity onPress={() => deleteEvent({ event_id: item._id || item.id, user_id: user.email })}>
              <Ionicons name="trash-outline" size={20} color={colors.danger} />
            </TouchableOpacity>
          </View>
        )}
      />
    </View>
  );
}

const s = StyleSheet.create({
  root:     { flex: 1 },
  header:   { flexDirection: 'row', alignItems: 'center', gap: 12, paddingHorizontal: spacing.md, paddingTop: 54, paddingBottom: 12, borderBottomWidth: 1, borderBottomColor: colors.border },
  title:    { color: colors.text, fontSize: 20, fontWeight: '700' },
  inputContainer: { padding: spacing.md, gap: 10 },
  input:    { backgroundColor: colors.bgInput, borderRadius: radii.md, padding: 14, color: colors.text, borderWidth: 1, borderColor: colors.border },
  addBtn:   { backgroundColor: colors.accent, borderRadius: radii.md, padding: 16, alignItems: 'center' },
  addBtnText: { color: '#fff', fontWeight: '700' },
  card:     { backgroundColor: colors.bgCard, borderRadius: radii.md, padding: 16, marginBottom: spacing.sm, borderWidth: 1, borderColor: colors.border, flexDirection: 'row', alignItems: 'center' },
  eventTitle: { color: colors.text, fontSize: 16, fontWeight: '600' },
  eventDate: { color: colors.textDim, fontSize: 13, marginTop: 4 },
});
