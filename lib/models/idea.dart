class Idea {
  final int id;
  final String topic;
  final String? hookFact;
  final int mysteryLevel;
  final String? potential;
  final String? estimatedAudience;
  final String? estimatedDuration;
  final List<String> keywords;
  final bool used;
  final String createdAt;

  Idea({
    required this.id,
    required this.topic,
    this.hookFact,
    required this.mysteryLevel,
    this.potential,
    this.estimatedAudience,
    this.estimatedDuration,
    required this.keywords,
    required this.used,
    required this.createdAt,
  });

  factory Idea.fromJson(Map<String, dynamic> json) {
    return Idea(
      id: (json['id'] as num?)?.toInt() ?? 0,
      topic: json['topic'] as String? ?? '',
      hookFact: json['hook_fact'] as String?,
      mysteryLevel: (json['mystery_level'] as num?)?.toInt() ?? 5,
      potential: json['potential'] as String?,
      estimatedAudience: json['estimated_audience'] as String?,
      estimatedDuration: json['estimated_duration'] as String?,
      keywords:
          (json['keywords'] as List?)?.map((e) => e.toString()).toList() ?? [],
      used: json['used'] == true || json['used'] == 1,
      createdAt: json['created_at'] as String? ?? '',
    );
  }
}
