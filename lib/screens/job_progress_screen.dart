import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/job_status.dart';
import '../providers/app_provider.dart';
import '../providers/nav_controller.dart';
import '../theme.dart';
import 'episode_detail_screen.dart';

class JobProgressScreen extends StatefulWidget {
  final String jobId;
  final String topic;

  const JobProgressScreen({
    super.key,
    required this.jobId,
    required this.topic,
  });

  @override
  State<JobProgressScreen> createState() => _JobProgressScreenState();
}

class _JobProgressScreenState extends State<JobProgressScreen> {
  Timer? _timer;
  JobStatus? _job;
  String? _error;

  @override
  void initState() {
    super.initState();
    _poll();
    _timer = Timer.periodic(const Duration(seconds: 3), (_) => _poll());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _poll() async {
    final app = context.read<AppProvider>();
    try {
      final job = await app.api.getJobStatus(widget.jobId);
      if (!mounted) return;
      setState(() {
        _job = job;
        _error = null;
      });
      if (job.status == JobState.done || job.status == JobState.error) {
        _timer?.cancel();
        if (job.status == JobState.done) {
          app.refreshStatus();
        }
      }
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    final job = _job;
    final isDone = job?.status == JobState.done;
    final isError = job?.status == JobState.error;

    return Scaffold(
      appBar: AppBar(
        title: const Text('جارِ الإنتاج'),
        automaticallyImplyLeading: !isDone && !isError,
        leading: (isDone || isError)
            ? IconButton(
                icon: const Icon(Icons.close),
                onPressed: () =>
                    Navigator.of(context).popUntil((r) => r.isFirst),
              )
            : null,
      ),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                widget.topic,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: AppColors.textLight,
                  fontSize: 17,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 28),
              if (isError) ...[
                const Icon(
                  Icons.error_outline,
                  color: AppColors.danger,
                  size: 56,
                ),
                const SizedBox(height: 16),
                Text(
                  job?.error ?? 'حدث خطأ غير معروف',
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: AppColors.danger),
                ),
                const SizedBox(height: 20),
                ElevatedButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('رجوع'),
                ),
              ] else if (isDone) ...[
                const Icon(
                  Icons.check_circle_outline,
                  color: AppColors.success,
                  size: 56,
                ),
                const SizedBox(height: 16),
                const Text(
                  'اكتمل الإنتاج بنجاح!',
                  style: TextStyle(
                    color: AppColors.success,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 24),
                ElevatedButton.icon(
                  onPressed: () {
                    if (job?.data != null) {
                      Navigator.of(context).pushReplacement(
                        MaterialPageRoute(
                          builder: (_) =>
                              EpisodeDetailScreen(preloaded: job!.data),
                        ),
                      );
                    }
                  },
                  icon: const Icon(Icons.visibility_outlined),
                  label: const Text('عرض الحلقة'),
                ),
                const SizedBox(height: 12),
                OutlinedButton(
                  onPressed: () {
                    context.read<NavController>().goTo(2);
                    Navigator.of(context).popUntil((r) => r.isFirst);
                  },
                  child: const Text('الذهاب إلى الأرشيف'),
                ),
              ] else ...[
                LinearProgressIndicator(
                  value: (job?.progress ?? 0) / 100,
                  minHeight: 8,
                  borderRadius: BorderRadius.circular(6),
                ),
                const SizedBox(height: 14),
                Text(
                  '${job?.progress ?? 0}%',
                  style: const TextStyle(
                    color: AppColors.gold,
                    fontSize: 22,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  job?.message ?? 'بدء الإنتاج...',
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: AppColors.textMuted),
                ),
                if (_error != null) ...[
                  const SizedBox(height: 10),
                  Text(
                    'تنبيه شبكة: $_error',
                    style: const TextStyle(
                      color: AppColors.danger,
                      fontSize: 11,
                    ),
                    textAlign: TextAlign.center,
                  ),
                ],
                const SizedBox(height: 20),
                const Text(
                  'يمكنك مغادرة هذه الشاشة، سيتم متابعة المهمة على الخادم',
                  style: TextStyle(color: AppColors.textMuted, fontSize: 11),
                  textAlign: TextAlign.center,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
