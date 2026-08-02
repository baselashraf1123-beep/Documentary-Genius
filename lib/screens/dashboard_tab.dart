import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/app_provider.dart';
import '../providers/nav_controller.dart';
import '../theme.dart';
import '../widgets/error_retry.dart';
import '../widgets/stat_card.dart';

class DashboardTab extends StatefulWidget {
  const DashboardTab({super.key});

  @override
  State<DashboardTab> createState() => _DashboardTabState();
}

class _DashboardTabState extends State<DashboardTab> {
  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppProvider>();
    final status = app.status;

    return Scaffold(
      appBar: AppBar(
        title: const Text('أسرار ما وراء الأفق'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => app.refreshStatus(),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => app.refreshStatus(),
        child: app.loadingStatus && status == null
            ? const Center(child: CircularProgressIndicator())
            : status == null
            ? ErrorRetry(
                message:
                    app.lastError ??
                    'تعذّر الاتصال بالخادم. تحقّق من عنوان الخادم في الإعدادات.',
                onRetry: () => app.refreshStatus(),
              )
            : _buildBody(context, app, status),
      ),
    );
  }

  Widget _buildBody(BuildContext context, AppProvider app, dynamic status) {
    final stats = status.stats;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(
          'مرحباً${app.username != null ? '، ${app.username}' : ''} 👋',
          style: const TextStyle(
            fontSize: 18,
            color: AppColors.textLight,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 4),
        const Text(
          'نظرة عامة على قناتك الوثائقية',
          style: TextStyle(color: AppColors.textMuted, fontSize: 13),
        ),
        const SizedBox(height: 20),
        GridView.count(
          crossAxisCount: 2,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 12,
          crossAxisSpacing: 12,
          childAspectRatio: 1.25,
          children: [
            StatCard(
              icon: Icons.video_library,
              label: 'إجمالي الحلقات',
              value: '${stats.episodes}',
            ),
            StatCard(
              icon: Icons.graphic_eq,
              label: 'بصوت مُنتَج',
              value: '${stats.withAudio}',
              accent: AppColors.success,
            ),
            StatCard(
              icon: Icons.movie,
              label: 'بفيديو كامل',
              value: '${stats.withVideo}',
              accent: AppColors.goldLight,
            ),
            StatCard(
              icon: Icons.lightbulb,
              label: 'أفكار غير مستخدمة',
              value: '${stats.unusedIdeas}',
              accent: AppColors.danger,
            ),
          ],
        ),
        const SizedBox(height: 24),
        const Text(
          'محرّكات النظام',
          style: TextStyle(
            color: AppColors.textLight,
            fontSize: 15,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 10),
        _engineRow(Icons.auto_awesome, 'الذكاء الاصطناعي', status.aiEngine),
        _engineRow(Icons.record_voice_over, 'الصوت', status.voiceEngine),
        _engineRow(Icons.image, 'الصور', status.imageEngine),
        _engineRow(Icons.videocam, 'الفيديو', status.videoEngine),
        const SizedBox(height: 28),
        ElevatedButton.icon(
          onPressed: () => context.read<NavController>().goTo(1),
          icon: const Icon(Icons.add_circle_outline),
          label: const Text('إنتاج حلقة جديدة'),
        ),
      ],
    );
  }

  Widget _engineRow(IconData icon, String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          Icon(icon, color: AppColors.gold, size: 18),
          const SizedBox(width: 10),
          Text(
            '$label: ',
            style: const TextStyle(color: AppColors.textMuted, fontSize: 13),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(color: AppColors.textLight, fontSize: 13),
              textAlign: TextAlign.right,
            ),
          ),
        ],
      ),
    );
  }
}
