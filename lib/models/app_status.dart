class ChannelStats {
  final int episodes;
  final int withAudio;
  final int withVideo;
  final int ideas;
  final int unusedIdeas;

  ChannelStats({
    required this.episodes,
    required this.withAudio,
    required this.withVideo,
    required this.ideas,
    required this.unusedIdeas,
  });

  factory ChannelStats.empty() => ChannelStats(
    episodes: 0,
    withAudio: 0,
    withVideo: 0,
    ideas: 0,
    unusedIdeas: 0,
  );

  factory ChannelStats.fromJson(Map<String, dynamic>? json) {
    if (json == null) return ChannelStats.empty();
    return ChannelStats(
      episodes: (json['episodes'] as num?)?.toInt() ?? 0,
      withAudio: (json['with_audio'] as num?)?.toInt() ?? 0,
      withVideo: (json['with_video'] as num?)?.toInt() ?? 0,
      ideas: (json['ideas'] as num?)?.toInt() ?? 0,
      unusedIdeas: (json['unused_ideas'] as num?)?.toInt() ?? 0,
    );
  }
}

class AppStatus {
  final String channel;
  final String aiEngine;
  final String voiceEngine;
  final String imageEngine;
  final String videoEngine;
  final Map<String, String> styles;
  final Map<String, String> voices;
  final ChannelStats stats;

  AppStatus({
    required this.channel,
    required this.aiEngine,
    required this.voiceEngine,
    required this.imageEngine,
    required this.videoEngine,
    required this.styles,
    required this.voices,
    required this.stats,
  });

  factory AppStatus.fromJson(Map<String, dynamic> json) {
    return AppStatus(
      channel: json['channel'] as String? ?? 'أسرار ما وراء الأفق',
      aiEngine: json['ai_engine'] as String? ?? '',
      voiceEngine: json['voice_engine'] as String? ?? '',
      imageEngine: json['image_engine'] as String? ?? '',
      videoEngine: json['video_engine'] as String? ?? '',
      styles:
          (json['styles'] as Map?)?.map(
            (k, v) => MapEntry(k.toString(), v.toString()),
          ) ??
          {},
      voices:
          (json['voices'] as Map?)?.map(
            (k, v) => MapEntry(k.toString(), v.toString()),
          ) ??
          {},
      stats: ChannelStats.fromJson(json['stats'] as Map<String, dynamic>?),
    );
  }
}
