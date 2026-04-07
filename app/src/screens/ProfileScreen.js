// app/src/screens/ProfileScreen.js
import React, { useState, useEffect } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, ScrollView,
  StyleSheet, Alert, ActivityIndicator, Image,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import useAuth from '../hooks/useAuth';
import { getProfilePhoto, saveProfilePhoto } from '../services/auth';
import { colors, radii, spacing } from '../theme';

export default function ProfileScreen({ navigation }) {
  const { user, signOut } = useAuth();
  const [photo, setPhoto] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchPhoto = async () => {
    try {
      const resp = await getProfilePhoto(user.email);
      if (resp.pic_b64) setPhoto(`data:image/jpeg;base64,${resp.pic_b64}`);
    } catch (_) {}
  };

  useEffect(() => { fetchPhoto(); }, []);

  const handleLogout = () => {
    Alert.alert('Logout', 'Are you sure you want to log out?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Logout', style: 'destructive', onPress: signOut },
    ]);
  };

  return (
    <View style={s.root}>
      <LinearGradient colors={['#030712', '#0c1424']} style={StyleSheet.absoluteFill} />
      <View style={s.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Ionicons name="arrow-back" size={24} color={colors.accent} />
        </TouchableOpacity>
        <Text style={s.title}>👤 Profile</Text>
      </View>

      <ScrollView contentContainerStyle={s.content}>
        <View style={s.profileHeader}>
          <View style={s.avatarBox}>
            {photo ? (
              <Image source={{ uri: photo }} style={s.avatar} />
            ) : (
              <Text style={s.avatarInitial}>{user?.name ? user.name[0] : 'U'}</Text>
            )}
            <TouchableOpacity style={s.editBtn}>
              <Ionicons name="camera" size={20} color="#fff" />
            </TouchableOpacity>
          </View>
          <Text style={s.userName}>{user?.name}</Text>
          <Text style={s.userEmail}>{user?.email}</Text>
        </View>

        <View style={s.section}>
          <Text style={s.sectionTitle}>Account Settings</Text>
          <SettingsItem icon="notifications-outline" label="Push Notifications" value="On" />
          <SettingsItem icon="cloud-upload-outline" label="Sync Memories" value="Auto" />
          <SettingsItem icon="lock-closed-outline" label="Password & Security" />
        </View>

        <View style={s.section}>
          <Text style={s.sectionTitle}>Support</Text>
          <SettingsItem icon="help-circle-outline" label="Help Center" />
          <SettingsItem icon="document-text-outline" label="Privacy Policy" />
        </View>

        <TouchableOpacity style={s.logoutBtn} onPress={handleLogout}>
          <Text style={s.logoutBtnText}>Logout from Device</Text>
        </TouchableOpacity>
      </ScrollView>
    </View>
  );
}

function SettingsItem({ icon, label, value }) {
  return (
    <TouchableOpacity style={s.item}>
      <Ionicons name={icon} size={22} color={colors.accent} />
      <Text style={s.itemLabel}>{label}</Text>
      {value ? <Text style={s.itemValue}>{value}</Text> : null}
      <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
    </TouchableOpacity>
  );
}

const s = StyleSheet.create({
  root:     { flex: 1 },
  header:   { flexDirection: 'row', alignItems: 'center', gap: 12, paddingHorizontal: spacing.md, paddingTop: 54, paddingBottom: 12, borderBottomWidth: 1, borderBottomColor: colors.border },
  title:    { color: colors.text, fontSize: 20, fontWeight: '700' },
  content:  { padding: spacing.md },
  profileHeader: { alignItems: 'center', marginVertical: spacing.xl },
  avatarBox: { width: 100, height: 100, borderRadius: 50, backgroundColor: colors.accent, justifyContent: 'center', alignItems: 'center', marginBottom: 16 },
  avatar: { width: 100, height: 100, borderRadius: 50 },
  avatarInitial: { color: '#fff', fontSize: 36, fontWeight: '800' },
  editBtn: { position: 'absolute', bottom: 0, right: 0, backgroundColor: colors.accent, width: 32, height: 32, borderRadius: 16, justifyContent: 'center', alignItems: 'center', borderWidth: 2, borderColor: colors.bg },
  userName: { color: colors.text, fontSize: 22, fontWeight: '700' },
  userEmail: { color: colors.textDim, fontSize: 14, marginTop: 4 },
  section: { marginTop: spacing.xl },
  sectionTitle: { color: colors.textMuted, fontSize: 13, textTransform: 'uppercase', fontWeight: '700', marginLeft: 4, marginBottom: 12 },
  item: { flexDirection: 'row', alignItems: 'center', backgroundColor: colors.bgCard, padding: 16, borderRadius: radii.md, marginBottom: 8, borderWidth: 1, borderColor: colors.border },
  itemLabel: { flex: 1, color: colors.text, marginLeft: 12, fontSize: 15 },
  itemValue: { color: colors.textDim, marginRight: 8, fontSize: 14 },
  logoutBtn: { marginTop: 40, borderTopWidth: 1, borderTopColor: colors.border, paddingVertical: 20, alignItems: 'center' },
  logoutBtnText: { color: colors.danger, fontWeight: '700', fontSize: 16 },
});
