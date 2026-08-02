import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/episode.dart';
import '../providers/app_provider.dart';
import '../theme.dart';
import '../widgets/error_retry.dart';
import '../widgets/media_player_widget.dart';

class EpisodeDetailScreen extends StatefulWidget {
  final int? episodeId;
  final EpisodeDetail? preloaded;

  const EpisodeDetailScreen({super.key, this.episodeId, this.preloaded})
    : assert(episodeId != null || preloaded != null);

  @override
  State<EpisodeDetailScreen> createState() => _EpisodeDetailScreenState();
}

class _EpisodeDetailScreenState extends State<EpisodeDetailScreen> {
  EpisodeDetail? _detail;
  String? _error;
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    if (widget.preloaded != null) {
      _detail = widget.preloaded;
    } else {
      WidgetsBinding.instance.addPostFrameCallback((_) => _load());
    }
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    final app = context.read<AppProvider>();
    try {
      final d = await app.api.getPackageDetail(widget.episodeId!);
      if (!mounted) return;
      setState(() => _detail = d);
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final detail = _detail;
    return Scaffold(
      appBar: AppBar(
        title: Text(
          detail?.title ?? 'تفاصيل الحلقة',
          overflow: TextOverflow.ellipsis,
        ),
      ),
      body: _loading && detail == null
          ? const Center(child: CircularProgressIndicator())
          : detail == null
          ? ErrorRetry(message: _error ?? 'تعذّر تحميل الحلقة', onRetry: _load)
          : _buildBody(context, detail),
    );
  }

  Widget _buildBody(BuildContext context, EpisodeDetail detail) {
    final app = context.read<AppProvider>();
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(
          detail.topic,
          style: const TextStyle(color: AppColors.textMuted, fontSize: 13),
        ),
        const SizedBox(height: 14),
        if (detail.videoFile != null)
          FutureBuilder<String>(
            future: app.api.mediaUrl('videos', detail.videoFile),
            builder: (context, snap) {
              if (!snap.hasData) {
                return const SizedBox(
                  height: 200,
                  child: Center(child: CircularProgressIndicator()),
                );
              }
              return MediaPlayerWidget(url: snap.data!, isVideo: true);
            },
          )
        else if (detail.audioFile != null)
          FutureBuilder<String>(
            future: app.api.mediaUrl('audio', detail.audioFile),
            builder: (context, snap) {
              if (!snap.hasData) {
                return const SizedBox(
                  height: 70,
                  child: Center(child: CircularProgressIndicator()),
                );
              }
              return MediaPlayerWidget(url: snap.data!, isVideo: false);
            },
          )
        else if (detail.thumbnailFile != null)
          FutureBuilder<String>(
            future: app.api.mediaUrl('thumbnails', detail.thumbnailFile),
            builder: (context, snap) {
              if (!snap.hasData) return const SizedBox();
              return ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Image.network(
                  snap.data!,
                  errorBuilder: (_, __, ___) => const SizedBox(),
                ),
              );
            },
          ),
        const SizedBox(height: 20),
        _infoChips(detail),
        const SizedBox(height: 20),
        _section(
          'السكريبت الكامل',
          Icons.article_outlined,
          detail.fullScript.isNotEmpty ? detail.fullScript : 'لا يوجد نص',
        ),
        if (detail.seo['titles'] != null ||
            detail.seo['description'] != null) ...[
          const SizedBox(height: 16),
          _seoSection(detail),
        ],
        if (detail.imagesCount > 0) ...[
          const SizedBox(height: 16),
          Text(
            'لقطات المشهد (${detail.imagesCount})',
            style: const TextStyle(
              color: AppColors.textLight,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 10),
          SizedBox(
            height: 110,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: detail.images.length,
              separatorBuilder: (_, __) => const SizedBox(width: 8),
              itemBuilder: (context, i) => FutureBuilder<String>(
                future: app.api.mediaUrl('images', detail.images[i]),
                builder: (context, snap) {
                  if (!snap.hasData) return const SizedBox(width: 100);
                  return ClipRRect(
                    borderRadius: BorderRadius.circular(10),
                    child: Image.network(
                      snap.data!,
                      width: 150,
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) =>
                          Container(width: 150, color: AppColors.navyLight),
                    ),
                  );
                },
              ),
            ),
          ),
        ],
        const SizedBox(height: 24),
      ],
    );
  }

  Widget _infoChips(EpisodeDetail detail) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      alignment: WrapAlignment.end,
      children: [
        _chip(Icons.timer_outlined, '${detail.durationMin} دقيقة'),
        _chip(Icons.style_outlined, detail.style),
        _chip(Icons.record_voice_over_outlined, detail.voice),
        if (detail.elapsedSec > 0)
          _chip(Icons.speed_outlined, '${detail.elapsedSec.round()} ث إنتاج'),
      ],
    );
  }

  Widget _chip(IconData icon, String label) {
    return Chip(
      backgroundColor: AppColors.navyCard,
      side: const BorderSide(color: AppColors.navyLight),
      avatar: Icon(icon, size: 16, color: AppColors.gold),
      label: Text(
        label,
        style: const TextStyle(color: AppColors.textLight, fontSize: 12),
      ),
    );
  }

  Widget _section(String title, IconData icon, String content) {
    return ExpansionTile(
      initiallyExpanded: false,
      leading: Icon(icon, color: AppColors.gold),
      title: Text(
        title,
        style: const TextStyle(
          color: AppColors.textLight,
          fontWeight: FontWeight.bold,
        ),
      ),
      children: [
        Padding(
          padding: const EdgeInsets.all(12),
          child: Text(
            content,
            style: const TextStyle(color: AppColors.textMuted, height: 1.6),
            textAlign: TextAlign.right,
          ),
        ),
      ],
    );
  }

  Widget _seoSection(EpisodeDetail detail) {
    final seo = detail.seo;
    final tags =
        (seo['tags'] as List?)?.map((e) => e.toString()).toList() ?? [];
    final titles =
        (seo['titles'] as List?)?.map((e) => e.toString()).toList() ?? [];
    final suggestedTitle = titles.isNotEmpty ? titles.first : null;
    return ExpansionTile(
      leading: const Icon(Icons.tag, color: AppColors.gold),
      title: const Text(
        'بيانات SEO',
        style: TextStyle(
          color: AppColors.textLight,
          fontWeight: FontWeight.bold,
        ),
      ),
      children: [
        Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              if (suggestedTitle != null)
                Text(
                  suggestedTitle,
                  style: const TextStyle(
                    color: AppColors.textLight,
                    fontWeight: FontWeight.bold,
                  ),
                  textAlign: TextAlign.right,
                ),
              if (seo['description'] != null) ...[
                const SizedBox(height: 6),
                Text(
                  '${seo['description']}',
                  style: const TextStyle(color: AppColors.textMuted),
                  textAlign: TextAlign.right,
                ),
              ],
              if (tags.isNotEmpty) ...[
                const SizedBox(height: 10),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  alignment: WrapAlignment.end,
                  children: tags
                      .map(
                        (t) => Chip(
                          label: Text(t, style: const TextStyle(fontSize: 11)),
                        ),
                      )
                      .toList(),
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }
}
