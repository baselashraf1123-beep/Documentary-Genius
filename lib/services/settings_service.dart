import 'package:shared_preferences/shared_preferences.dart';

/// خدمة إدارة الإعدادات المحفوظة محلياً: عنوان الخادم الخلفي، رمز الجلسة (token)
class SettingsService {
  static const _kBaseUrl = 'backend_base_url';
  static const _kToken = 'auth_token';
  static const _kUsername = 'auth_username';

  // عنوان افتراضي للخادم الخلفي — يمكن تغييره من شاشة الإعدادات
  static const String defaultBaseUrl =
      'https://5001-i6v3psnop7m9j9e7u51g2-5c13a017.sandbox.novita.ai';

  Future<String> getBaseUrl() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_kBaseUrl) ?? defaultBaseUrl;
  }

  Future<void> setBaseUrl(String url) async {
    final prefs = await SharedPreferences.getInstance();
    // إزالة الشرطة المائلة الأخيرة إن وجدت لتفادي مسارات مكررة //
    final clean = url.trim().endsWith('/')
        ? url.trim().substring(0, url.trim().length - 1)
        : url.trim();
    await prefs.setString(_kBaseUrl, clean);
  }

  Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_kToken);
  }

  Future<void> setToken(String? token) async {
    final prefs = await SharedPreferences.getInstance();
    if (token == null) {
      await prefs.remove(_kToken);
    } else {
      await prefs.setString(_kToken, token);
    }
  }

  Future<String?> getUsername() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_kUsername);
  }

  Future<void> setUsername(String? username) async {
    final prefs = await SharedPreferences.getInstance();
    if (username == null) {
      await prefs.remove(_kUsername);
    } else {
      await prefs.setString(_kUsername, username);
    }
  }

  Future<void> clearSession() async {
    await setToken(null);
    await setUsername(null);
  }
}
