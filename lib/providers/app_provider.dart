import 'package:flutter/foundation.dart';

import '../models/app_status.dart';
import '../services/api_service.dart';
import '../services/settings_service.dart';

enum AuthState { unknown, loggedOut, loggedIn }

/// حالة التطبيق العامة: المصادقة + حالة النظام (المحرّكات/الإحصائيات)
class AppProvider extends ChangeNotifier {
  final SettingsService settings = SettingsService();
  late final ApiService api = ApiService(settings);

  AuthState authState = AuthState.unknown;
  String? username;
  AppStatus? status;
  String? lastError;
  bool loadingStatus = false;

  /// موضوع مُعلَّق يُمرَّر من تبويب "الأفكار" إلى تبويب "إنتاج جديد"
  /// عند استخدام فكرة مخزّنة (جسر حالة بسيط بين التبويبات)
  String? pendingTopic;

  void setPendingTopic(String topic) {
    pendingTopic = topic;
    notifyListeners();
  }

  void clearPendingTopic() {
    pendingTopic = null;
    notifyListeners();
  }

  Future<void> bootstrap() async {
    final token = await settings.getToken();
    username = await settings.getUsername();
    authState = (token != null && token.isNotEmpty)
        ? AuthState.loggedIn
        : AuthState.loggedOut;
    notifyListeners();
    await refreshStatus();
  }

  Future<void> refreshStatus() async {
    loadingStatus = true;
    notifyListeners();
    try {
      status = await api.getStatus();
      lastError = null;
    } catch (e) {
      lastError = e.toString();
    } finally {
      loadingStatus = false;
      notifyListeners();
    }
  }

  Future<bool> login(String user, String pass) async {
    try {
      final token = await api.login(user, pass);
      await settings.setToken(token);
      await settings.setUsername(user);
      username = user;
      authState = AuthState.loggedIn;
      lastError = null;
      notifyListeners();
      await refreshStatus();
      return true;
    } catch (e) {
      lastError = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<void> logout() async {
    try {
      await api.logout();
    } catch (_) {}
    await settings.clearSession();
    username = null;
    authState = AuthState.loggedOut;
    notifyListeners();
  }
}
