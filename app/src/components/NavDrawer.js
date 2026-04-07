// src/components/NavDrawer.js
// Slide-over navigation drawer — mirrors the Streamlit sidebar
import React from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, Modal,
  Pressable, ScrollView,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { colors, spacing, radii } from '../theme';

const NAV_ITEMS = [
  { label: '💬 Chat',          screen: 'Home' },
  { label: '🧠 Memories',      screen: 'Memories' },
  { label: '🎯 Goals',         screen: 'Goals' },
  { label: '📅 Calendar',      screen: 'Calendar' },
  { label: '👨‍💻 Developer',     screen: 'Developer' },
  { label: '📰 Newsroom',      screen: 'Newsroom' },
  { label: '📊 Analytics',     screen: 'Analytics' },
  { label: '👤 Profile',       screen: 'Profile' },
];

export default function NavDrawer({ open, onClose, navigation, user, onLogout }) {
  return (
    <Modal transparent visible={open} animationType="slide" onRequestClose={onClose}>
      <View style={s.overlay}>
        <Pressable style={s.backdrop} onPress={onClose} />
        <LinearGradient colors={['#0c1424', '#030712']} style={s.drawer}>
          {/* Profile */}
          <View style={s.profile}>
            <View style={s.avatar}>
              <Text style={s.avatarText}>
                {user?.name ? user.name[0].toUpperCase() : 'U'}
              </Text>
            </View>
            <View style={{ flex: 1 }}>
              <Text style={s.name}>{user?.name || 'User'}</Text>
              <Text style={s.email}>{user?.email || ''}</Text>
            </View>
            <TouchableOpacity onPress={onClose}>
              <Ionicons name="close" size={22} color={colors.textDim} />
            </TouchableOpacity>
          </View>

          <View style={s.divider} />

          {/* Nav Items */}
          <ScrollView style={{ flex: 1 }}>
            {NAV_ITEMS.map((item) => (
              <TouchableOpacity
                key={item.screen}
                style={s.navItem}
                onPress={() => { onClose(); navigation.navigate(item.screen); }}
              >
                <Text style={s.navLabel}>{item.label}</Text>
                <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
              </TouchableOpacity>
            ))}
          </ScrollView>

          <View style={s.divider} />

          {/* Logout */}
          <TouchableOpacity style={s.logoutBtn} onPress={onLogout}>
            <Ionicons name="log-out-outline" size={20} color={colors.danger} />
            <Text style={s.logoutText}>Logout</Text>
          </TouchableOpacity>
        </LinearGradient>
      </View>
    </Modal>
  );
}

const s = StyleSheet.create({
  overlay:    { flex: 1, flexDirection: 'row' },
  backdrop:   { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)' },
  drawer:     { width: 280, paddingTop: 54, paddingBottom: spacing.xl },
  profile:    { flexDirection: 'row', alignItems: 'center', paddingHorizontal: spacing.md, gap: 12, marginBottom: spacing.md },
  avatar:     { width: 44, height: 44, borderRadius: 22, backgroundColor: colors.accent, justifyContent: 'center', alignItems: 'center' },
  avatarText: { color: '#fff', fontWeight: '700', fontSize: 18 },
  name:       { color: colors.text, fontWeight: '700', fontSize: 15 },
  email:      { color: colors.textDim, fontSize: 12 },
  divider:    { height: 1, backgroundColor: colors.border, marginVertical: spacing.sm },
  navItem:    { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: spacing.md, paddingVertical: 14 },
  navLabel:   { color: colors.text, fontSize: 15, fontWeight: '500' },
  logoutBtn:  { flexDirection: 'row', alignItems: 'center', gap: 10, paddingHorizontal: spacing.md, paddingTop: spacing.md },
  logoutText: { color: colors.danger, fontWeight: '700', fontSize: 15 },
});
