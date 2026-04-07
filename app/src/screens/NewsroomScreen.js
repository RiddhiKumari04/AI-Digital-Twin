// app/src/screens/NewsroomScreen.js
import React, { useState } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity,
  StyleSheet, Alert, ActivityIndicator,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import useAuth from '../hooks/useAuth';
import { getMorningBriefing } from '../services/newsroom';
import { colors, radii, spacing } from '../theme';

export default function NewsroomScreen({ navigation }) {
  const { user } = useAuth();
  const [briefing, setBriefing] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchBriefing = async () => {
    setLoading(true);
    setBriefing('');
    try {
      const data = await getMorningBriefing({
        user_id: user.email,
        mood: 'optimistic',
        locations: ['London', 'San Francisco'],
        extra_topics: ['AI Technology', 'Space Exploration']
      });
      setBriefing(data.briefing || 'No briefing available.');
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
        <Text style={s.title}>📰 Newsroom</Text>
      </View>

      <ScrollView contentContainerStyle={s.content}>
        <TouchableOpacity style={s.briefBtn} onPress={fetchBriefing} disabled={loading}>
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <>
              <Ionicons name="sunny-outline" size={20} color="#fff" />
              <Text style={s.briefBtnText}>Get Morning Briefing</Text>
            </>
          )}
        </TouchableOpacity>

        {briefing ? (
          <View style={s.briefBox}>
            <Text style={s.briefTitle}>Your Personalized Morning Briefing</Text>
            <Text style={s.briefText}>{briefing}</Text>
          </View>
        ) : !loading && (
          <View style={s.emptyBox}>
            <Ionicons name="newspaper-outline" size={60} color={colors.textMuted} />
            <Text style={s.emptyText}>Tap Above for your AI Morning Briefing</Text>
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const s = StyleSheet.create({
  root:     { flex: 1 },
  header:   { flexDirection: 'row', alignItems: 'center', gap: 12, paddingHorizontal: spacing.md, paddingTop: 54, paddingBottom: 12, borderBottomWidth: 1, borderBottomColor: colors.border },
  title:    { color: colors.text, fontSize: 20, fontWeight: '700' },
  content:  { padding: spacing.md },
  briefBtn: {
    backgroundColor: colors.accent,
    borderRadius: radii.md,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    marginBottom: spacing.lg,
  },
  briefBtnText: { color: '#fff', fontWeight: '700', fontSize: 16 },
  briefBox: {
    backgroundColor: colors.bgCard,
    borderRadius: radii.md,
    padding: 20,
    borderWidth: 1,
    borderColor: colors.borderAccent,
  },
  briefTitle: { color: colors.accent, fontWeight: '700', marginBottom: 12, fontSize: 16 },
  briefText: { color: colors.text, fontSize: 15, lineHeight: 24 },
  emptyBox: { alignItems: 'center', marginTop: 100 },
  emptyText: { color: colors.textDim, marginTop: 12, fontSize: 14, textAlign: 'center' },
});
