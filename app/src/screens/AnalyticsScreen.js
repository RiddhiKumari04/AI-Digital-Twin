// app/src/screens/AnalyticsScreen.js
import React, { useState, useEffect } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity,
  StyleSheet, Alert, ActivityIndicator,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import useAuth from '../hooks/useAuth';
import { getAnalytics } from '../services/twin';
import { colors, radii, spacing } from '../theme';

export default function AnalyticsScreen({ navigation }) {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const resp = await getAnalytics(user.email);
      setData(resp);
    } catch (e) { Alert.alert('Error', e.message); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchAnalytics(); }, []);

  return (
    <View style={s.root}>
      <LinearGradient colors={['#030712', '#0c1424']} style={StyleSheet.absoluteFill} />
      <View style={s.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Ionicons name="arrow-back" size={24} color={colors.accent} />
        </TouchableOpacity>
        <Text style={s.title}>📊 Analytics</Text>
      </View>

      <ScrollView contentContainerStyle={s.content}>
        {loading ? (
          <ActivityIndicator color={colors.accent} style={{ marginTop: 100 }} />
        ) : (
          <>
            <View style={s.statRow}>
              <StatCard label="Total Messages" value={data?.message_count || 0} icon="chatbubble-outline" />
              <StatCard label="Chat Sessions" value={data?.session_count || 0} icon="bookmarks-outline" />
            </View>
            <View style={s.statRow}>
              <StatCard label="Memories" value={data?.memory_count || 0} icon="brain-outline" />
              <StatCard label="Goal Progress" value={`${data?.avg_progress || 0}%`} icon="trending-up-outline" />
            </View>

            <View style={s.chartPlaceholder}>
              <Text style={s.chartTitle}>Recent Activity</Text>
              <View style={s.barRow}>
                {[40, 70, 45, 90, 65, 80, 50].map((h, i) => (
                  <View key={i} style={[s.bar, { height: h }]} />
                ))}
              </View>
              <View style={s.labelRow}>
                {['M', 'T', 'W', 'T', 'F', 'S', 'S'].map((l, i) => (
                  <Text key={i} style={s.label}>{l}</Text>
                ))}
              </View>
            </View>
          </>
        )}
      </ScrollView>
    </View>
  );
}

function StatCard({ label, value, icon }) {
  return (
    <View style={s.card}>
      <Ionicons name={icon} size={24} color={colors.accent} />
      <Text style={s.val}>{value}</Text>
      <Text style={s.lab}>{label}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  root:     { flex: 1 },
  header:   { flexDirection: 'row', alignItems: 'center', gap: 12, paddingHorizontal: spacing.md, paddingTop: 54, paddingBottom: 12, borderBottomWidth: 1, borderBottomColor: colors.border },
  title:    { color: colors.text, fontSize: 20, fontWeight: '700' },
  content:  { padding: spacing.md },
  statRow:  { flexDirection: 'row', gap: 12, marginBottom: 12 },
  card:     { flex: 1, backgroundColor: colors.bgCard, borderRadius: radii.md, padding: 16, borderWidth: 1, borderColor: colors.border, alignItems: 'center' },
  val:      { color: colors.text, fontSize: 24, fontWeight: '800', marginVertical: 4 },
  lab:      { color: colors.textDim, fontSize: 12 },
  chartPlaceholder: { marginTop: 20, backgroundColor: colors.bgCard, borderRadius: radii.lg, padding: 20, borderWidth: 1, borderColor: colors.border },
  chartTitle: { color: colors.text, fontWeight: '700', marginBottom: 20 },
  barRow:   { flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-between', height: 100 },
  bar:      { width: 12, backgroundColor: colors.accent, borderRadius: 6 },
  labelRow: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 10 },
  label:    { color: colors.textMuted, fontSize: 11, width: 12, textAlign: 'center' },
});
