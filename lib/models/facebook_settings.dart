/// نموذج إعدادات صفحة فيسبوك (Page ID + حالة رمز الوصول)
class FacebookSettings {
  final String pageId;
  final bool tokenConfigured;
  final String tokenPreview;

  FacebookSettings({
    required this.pageId,
    required this.tokenConfigured,
    required this.tokenPreview,
  });

  factory FacebookSettings.fromJson(Map<String, dynamic> json) {
    return FacebookSettings(
      pageId: json['page_id'] as String? ?? '',
      tokenConfigured: json['token_configured'] as bool? ?? false,
      tokenPreview: json['token_preview'] as String? ?? '',
    );
  }
}
