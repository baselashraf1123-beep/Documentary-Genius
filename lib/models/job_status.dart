import 'episode.dart';

enum JobState { running, done, error, unknown }

class JobStatus {
  final JobState status;
  final int progress;
  final String message;
  final EpisodeDetail? data;
  final String? error;

  JobStatus({
    required this.status,
    required this.progress,
    required this.message,
    this.data,
    this.error,
  });

  factory JobStatus.fromJson(Map<String, dynamic> json) {
    JobState state;
    switch (json['status']) {
      case 'running':
        state = JobState.running;
        break;
      case 'done':
        state = JobState.done;
        break;
      case 'error':
        state = JobState.error;
        break;
      default:
        state = JobState.unknown;
    }
    return JobStatus(
      status: state,
      progress: (json['progress'] as num?)?.toInt() ?? 0,
      message: json['message'] as String? ?? '',
      data: json['data'] != null
          ? EpisodeDetail.fromJson(
              (json['data'] as Map).cast<String, dynamic>(),
            )
          : null,
      error: json['error'] as String?,
    );
  }
}
