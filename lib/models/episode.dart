/// نموذج ملخّص الحلقة (يُستخدم في قائمة الأرشيف /api/packages)
class EpisodeSummary {
  final int id;
  final String topic;
  final String title;
  final String date;
  final int duration;
  final String style;
  final bool hasAudio;
  final bool hasVideo;
  final String? fbPostId;
  final String? fbPublishedAt;

  bool get isPublishedToFacebook => fbPostId != null && fbPostId!.isNotEmpty;

  EpisodeSummary({
    required this.id,
    required this.topic,
    required this.title,
    required this.date,
    required this.duration,
    required this.style,
    required this.hasAudio,
    required this.hasVideo,
    this.fbPostId,
    this.fbPublishedAt,
  });

  factory EpisodeSummary.fromJson(Map<String, dynamic> json) {
    return EpisodeSummary(
      id: (json['id'] as num?)?.toInt() ?? 0,
      topic: json['topic'] as String? ?? '',
      title: (json['title'] as String?)?.isNotEmpty == true
          ? json['title'] as String
          : (json['topic'] as String? ?? 'بدون عنوان'),
      date: json['date'] as String? ?? '',
      duration: (json['duration'] as num?)?.toInt() ?? 0,
      style: json['style'] as String? ?? '',
      hasAudio: json['has_audio'] as bool? ?? false,
      hasVideo: json['has_video'] as bool? ?? false,
      fbPostId: json['fb_post_id'] as String?,
      fbPublishedAt: json['fb_published_at'] as String?,
    );
  }
}

/// نموذج تفاصيل الحلقة الكاملة (من مسار packages أو نتيجة مهمة الإنتاج)
class EpisodeDetail {
  final int? id;
  final String channel;
  final String topic;
  final int durationMin;
  final String style;
  final String voice;
  final String generatedAt;
  final double elapsedSec;
  final Map<String, dynamic> script;
  final Map<String, dynamic> scenes;
  final Map<String, dynamic> seo;
  final String? audioFile;
  final String? videoFile;
  final String? thumbnailFile;
  final List<String> images;
  final int imagesCount;
  final String? fbPostId;
  final String? fbPublishedAt;
  final String? fbPublishError;

  EpisodeDetail({
    this.id,
    required this.channel,
    required this.topic,
    required this.durationMin,
    required this.style,
    required this.voice,
    required this.generatedAt,
    required this.elapsedSec,
    required this.script,
    required this.scenes,
    required this.seo,
    this.audioFile,
    this.videoFile,
    this.thumbnailFile,
    required this.images,
    required this.imagesCount,
    this.fbPostId,
    this.fbPublishedAt,
    this.fbPublishError,
  });

  String get fullScript => script['full_script'] as String? ?? '';
  String get title => script['title'] as String? ?? topic;
  bool get isPublishedToFacebook => fbPostId != null && fbPostId!.isNotEmpty;

  factory EpisodeDetail.fromJson(Map<String, dynamic> json) {
    final rawId = json['episode_id'] ?? json['id'];
    return EpisodeDetail(
      id: rawId is num ? rawId.toInt() : null,
      channel: json['channel'] as String? ?? '',
      topic: json['topic'] as String? ?? '',
      durationMin: (json['duration_min'] as num?)?.toInt() ?? 0,
      style: json['style'] as String? ?? '',
      voice: json['voice'] as String? ?? '',
      generatedAt: json['generated_at'] as String? ?? '',
      elapsedSec: (json['elapsed_sec'] as num?)?.toDouble() ?? 0,
      script: (json['script'] as Map?)?.cast<String, dynamic>() ?? {},
      scenes: (json['scenes'] as Map?)?.cast<String, dynamic>() ?? {},
      seo: (json['seo'] as Map?)?.cast<String, dynamic>() ?? {},
      audioFile: json['audio_file'] as String?,
      videoFile: json['video_file'] as String?,
      thumbnailFile: json['thumbnail_file'] as String?,
      images:
          (json['images'] as List?)?.map((e) => e.toString()).toList() ?? [],
      imagesCount: (json['images_count'] as num?)?.toInt() ?? 0,
      fbPostId: json['fb_post_id'] as String?,
      fbPublishedAt: json['fb_published_at'] as String?,
      fbPublishError: json['fb_publish_error'] as String?,
    );
  }
}
