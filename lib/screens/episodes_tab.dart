import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/episode.dart';
import '../providers/app_provider.dart';
import '../widgets/episode_card.dart';
import '../widgets/error_retry.dart';
import 'episode_detail_screen.dart';

class EpisodesTab extends StatefulWidget {
  const EpisodesTab({super.key});

  @override
  State<EpisodesTab> createState() => _EpisodesTabState();
}

class _EpisodesTabState extends State<EpisodesTab> {
  List<EpisodeSummary>? _episodes;
  String? _error;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    final app = context.read<AppProvider>();
    try {
      final eps = await app.api.getPackages();
      if (!mounted) return;
      setState(() => _episodes = eps);
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _delete(EpisodeSummary ep) async {
    final app = context.read<AppProvider>();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('حذف الحلقة'),
        content: Text('هل تريد حذف "${ep.title}" نهائياً؟'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('إلغاء'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('حذف'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await app.api.deletePackage(ep.id);
      _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('فشل الحذف: $e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('أرشيف الحلقات'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _load),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: _loading && _episodes == null
            ? const Center(child: CircularProgressIndicator())
            : _error != null && _episodes == null
            ? ErrorRetry(message: _error!, onRetry: _load)
            : (_episodes == null || _episodes!.isEmpty)
            ? ListView(
                children: const [
                  SizedBox(height: 120),
                  Center(
                    child: Text(
                      'لا توجد حلقات منتجة بعد',
                      style: TextStyle(color: Colors.white54),
                    ),
                  ),
                ],
              )
            : ListView.builder(
                padding: const EdgeInsets.all(14),
                itemCount: _episodes!.length,
                itemBuilder: (context, i) {
                  final ep = _episodes![i];
                  return EpisodeCard(
                    episode: ep,
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => EpisodeDetailScreen(episodeId: ep.id),
                      ),
                    ),
                    onDelete: () => _delete(ep),
                  );
                },
              ),
      ),
    );
  }
}
