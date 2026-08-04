import 'dart:convert';
import 'package:http/http.dart' as http;

import '../models/app_status.dart';
import '../models/episode.dart';
import '../models/facebook_settings.dart';
import '../models/idea.dart';
import '../models/job_status.dart';
import 'settings_service.dart';

class ApiException implements Exception {
  final String message;
  final int? statusCode;
  ApiException(this.message, {this.statusCode});

  @override
  String toString() => message;
}

/// طبقة الاتصال بالخادم الخلفي (Documentary Genius Backend API)
/// تستخدم مصادقة Bearer Token (بدون الاعتماد على كوكيز الجلسة) لتجنّب
/// أي مشاكل عبر النطاقات (CORS) على الويب أو تطبيق الأندرويد.
class ApiService {
  final SettingsService settings;
  final http.Client _client = http.Client();

  ApiService(this.settings);

  Future<Map<String, String>> _headers({bool json = true}) async {
    final token = await settings.getToken();
    final headers = <String, String>{};
    if (json) headers['Content-Type'] = 'application/json';
    if (token != null && token.isNotEmpty) {
      headers['Authorization'] = 'Bearer $token';
    }
    return headers;
  }

  Future<Uri> _uri(String path, [Map<String, String>? query]) async {
    final base = await settings.getBaseUrl();
    return Uri.parse('$base$path').replace(queryParameters: query);
  }

  dynamic _decodeOrThrow(http.Response resp) {
    Map<String, dynamic> body;
    try {
      body = jsonDecode(resp.body) as Map<String, dynamic>;
    } catch (_) {
      body = {};
    }
    if (resp.statusCode >= 200 && resp.statusCode < 300) {
      return body;
    }
    final msg =
        body['error'] as String? ?? 'خطأ غير متوقع (${resp.statusCode})';
    throw ApiException(msg, statusCode: resp.statusCode);
  }

  // ══════════════════════════════════════════════
  // حالة النظام (لا تتطلب تسجيل دخول)
  // ══════════════════════════════════════════════
  Future<AppStatus> getStatus() async {
    final uri = await _uri('/api/status');
    final resp = await _client.get(uri).timeout(const Duration(seconds: 15));
    final body = _decodeOrThrow(resp) as Map<String, dynamic>;
    return AppStatus.fromJson(body);
  }

  // ══════════════════════════════════════════════
  // تسجيل الدخول / الخروج
  // ══════════════════════════════════════════════
  Future<String> login(String username, String password) async {
    final uri = await _uri('/api/login');
    final resp = await _client
        .post(
          uri,
          headers: await _headers(),
          body: jsonEncode({'username': username, 'password': password}),
        )
        .timeout(const Duration(seconds: 15));
    final body = _decodeOrThrow(resp) as Map<String, dynamic>;
    final token = body['token'] as String?;
    if (token == null) {
      throw ApiException('فشل تسجيل الدخول: لم يُستلم رمز جلسة صالح');
    }
    return token;
  }

  Future<void> logout() async {
    try {
      final uri = await _uri('/api/logout');
      await _client
          .post(uri, headers: await _headers())
          .timeout(const Duration(seconds: 10));
    } catch (_) {
      // نتجاهل أي خطأ شبكة أثناء تسجيل الخروج — سيتم مسح الرمز محلياً بأي حال
    }
  }

  Future<void> changePassword({
    required String currentPassword,
    required String newPassword,
  }) async {
    final uri = await _uri('/api/change-password');
    final resp = await _client
        .post(
          uri,
          headers: await _headers(),
          body: jsonEncode({
            'current_password': currentPassword,
            'new_password': newPassword,
          }),
        )
        .timeout(const Duration(seconds: 15));
    _decodeOrThrow(resp);
  }

  // ══════════════════════════════════════════════
  // الإنتاج
  // ══════════════════════════════════════════════
  Future<String> produce({
    required String topic,
    required int duration,
    required String style,
    required String voice,
    bool audio = true,
    bool generateVideo = false,
  }) async {
    final uri = await _uri('/api/produce');
    final resp = await _client
        .post(
          uri,
          headers: await _headers(),
          body: jsonEncode({
            'topic': topic,
            'duration': duration,
            'style': style,
            'voice': voice,
            'audio': audio,
            'generate_video': generateVideo,
          }),
        )
        .timeout(const Duration(seconds: 20));
    final body = _decodeOrThrow(resp) as Map<String, dynamic>;
    return body['job_id'] as String;
  }

  Future<JobStatus> getJobStatus(String jobId) async {
    final uri = await _uri('/api/produce/status/$jobId');
    final resp = await _client
        .get(uri, headers: await _headers())
        .timeout(const Duration(seconds: 15));
    Map<String, dynamic> body;
    try {
      body = jsonDecode(resp.body) as Map<String, dynamic>;
    } catch (_) {
      body = {};
    }
    if (resp.statusCode >= 200 && resp.statusCode < 300) {
      return JobStatus.fromJson(body);
    }
    throw ApiException(
      body['error'] as String? ?? 'تعذّر جلب حالة المهمة',
      statusCode: resp.statusCode,
    );
  }

  // ══════════════════════════════════════════════
  // الأفكار
  // ══════════════════════════════════════════════
  Future<List<Idea>> generateIdeas({
    int count = 9,
    String topicHint = '',
  }) async {
    final uri = await _uri('/api/ideas');
    final resp = await _client
        .post(
          uri,
          headers: await _headers(),
          body: jsonEncode({'count': count, 'topic_hint': topicHint}),
        )
        .timeout(const Duration(seconds: 180));
    final body = _decodeOrThrow(resp) as Map<String, dynamic>;
    final list = (body['ideas'] as List?) ?? [];
    return list
        .map((e) => Idea.fromJson((e as Map).cast<String, dynamic>()))
        .toList();
  }

  Future<List<Idea>> getStoredIdeas({bool unusedOnly = false}) async {
    final uri = await _uri('/api/ideas/stored', {
      'unused': unusedOnly.toString(),
    });
    final resp = await _client
        .get(uri, headers: await _headers())
        .timeout(const Duration(seconds: 15));
    final body = _decodeOrThrow(resp) as Map<String, dynamic>;
    final list = (body['ideas'] as List?) ?? [];
    return list
        .map((e) => Idea.fromJson((e as Map).cast<String, dynamic>()))
        .toList();
  }

  Future<void> useIdea(int ideaId) async {
    final uri = await _uri('/api/ideas/use/$ideaId');
    final resp = await _client
        .post(uri, headers: await _headers())
        .timeout(const Duration(seconds: 15));
    _decodeOrThrow(resp);
  }

  // ══════════════════════════════════════════════
  // الأرشيف
  // ══════════════════════════════════════════════
  Future<List<EpisodeSummary>> getPackages() async {
    final uri = await _uri('/api/packages');
    final resp = await _client
        .get(uri, headers: await _headers())
        .timeout(const Duration(seconds: 20));
    final body = _decodeOrThrow(resp) as Map<String, dynamic>;
    final list = (body['packages'] as List?) ?? [];
    return list
        .map((e) => EpisodeSummary.fromJson((e as Map).cast<String, dynamic>()))
        .toList();
  }

  Future<EpisodeDetail> getPackageDetail(int id) async {
    final uri = await _uri('/api/packages/$id');
    final resp = await _client
        .get(uri, headers: await _headers())
        .timeout(const Duration(seconds: 20));
    final body = _decodeOrThrow(resp) as Map<String, dynamic>;
    return EpisodeDetail.fromJson(
      (body['data'] as Map).cast<String, dynamic>(),
    );
  }

  Future<void> deletePackage(int id) async {
    final uri = await _uri('/api/packages/$id');
    final resp = await _client
        .delete(uri, headers: await _headers())
        .timeout(const Duration(seconds: 15));
    _decodeOrThrow(resp);
  }

  /// ينشر فيديو حلقة مُنتَجة مباشرة على صفحة فيسبوك المضبوطة في الإعدادات.
  /// يرجع معرّف المنشور عند النجاح.
  Future<String> publishToFacebook(int episodeId) async {
    final uri = await _uri('/api/packages/$episodeId/publish');
    final resp = await _client
        .post(uri, headers: await _headers())
        .timeout(const Duration(seconds: 300)); // رفع الفيديو قد يستغرق وقتاً
    final body = _decodeOrThrow(resp) as Map<String, dynamic>;
    return body['post_id'] as String? ?? '';
  }

  // ══════════════════════════════════════════════
  // إعدادات صفحة فيسبوك
  // ══════════════════════════════════════════════
  Future<FacebookSettings> getFacebookSettings() async {
    final uri = await _uri('/api/settings/facebook');
    final resp = await _client
        .get(uri, headers: await _headers())
        .timeout(const Duration(seconds: 15));
    final body = _decodeOrThrow(resp) as Map<String, dynamic>;
    return FacebookSettings.fromJson(body);
  }

  Future<void> saveFacebookSettings({
    String? pageId,
    String? accessToken,
  }) async {
    final uri = await _uri('/api/settings/facebook');
    final resp = await _client
        .post(
          uri,
          headers: await _headers(),
          body: jsonEncode({
            if (pageId != null) 'page_id': pageId,
            if (accessToken != null) 'access_token': accessToken,
          }),
        )
        .timeout(const Duration(seconds: 15));
    _decodeOrThrow(resp);
  }

  /// يتحقق من صلاحية إعدادات فيسبوك المحفوظة، ويرجع اسم الصفحة عند النجاح.
  Future<String> testFacebookSettings() async {
    final uri = await _uri('/api/settings/facebook/test');
    final resp = await _client
        .post(uri, headers: await _headers())
        .timeout(const Duration(seconds: 20));
    final body = _decodeOrThrow(resp) as Map<String, dynamic>;
    return body['page_name'] as String? ?? '';
  }

  // ══════════════════════════════════════════════
  // روابط الوسائط المباشرة (لا تتطلب تسجيل دخول)
  // ══════════════════════════════════════════════
  Future<String> mediaUrl(String subdir, String? filename) async {
    if (filename == null || filename.isEmpty) return '';
    final base = await settings.getBaseUrl();
    return '$base/api/media/$subdir/$filename';
  }
}
