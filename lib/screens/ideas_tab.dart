import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/idea.dart';
import '../providers/app_provider.dart';
import '../providers/nav_controller.dart';
import '../theme.dart';
import '../widgets/error_retry.dart';
import '../widgets/idea_card.dart';

class IdeasTab extends StatefulWidget {
  const IdeasTab({super.key});

  @override
  State<IdeasTab> createState() => _IdeasTabState();
}

class _IdeasTabState extends State<IdeasTab> {
  List<Idea>? _ideas;
  String? _error;
  bool _loading = true;
  bool _generating = false;

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
      final ideas = await app.api.getStoredIdeas();
      if (!mounted) return;
      setState(() => _ideas = ideas);
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _generateNew() async {
    final app = context.read<AppProvider>();
    setState(() => _generating = true);
    try {
      await app.api.generateIdeas(count: 6);
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('فشل توليد الأفكار: $e')));
    } finally {
      if (mounted) setState(() => _generating = false);
    }
  }

  Future<void> _useIdea(Idea idea) async {
    final app = context.read<AppProvider>();
    try {
      await app.api.useIdea(idea.id);
    } catch (_) {}
    app.setPendingTopic(idea.topic);
    if (!mounted) return;
    context.read<NavController>().goTo(1);
    _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('مولّد الأفكار'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _load),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(14),
            child: ElevatedButton.icon(
              onPressed: _generating ? null : _generateNew,
              icon: _generating
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: AppColors.navy,
                      ),
                    )
                  : const Icon(Icons.auto_awesome),
              label: Text(
                _generating
                    ? 'جارِ توليد أفكار جديدة...'
                    : 'توليد أفكار جديدة بالذكاء الاصطناعي',
              ),
            ),
          ),
          Expanded(
            child: RefreshIndicator(
              onRefresh: _load,
              child: _loading && _ideas == null
                  ? const Center(child: CircularProgressIndicator())
                  : _error != null && _ideas == null
                  ? ErrorRetry(message: _error!, onRetry: _load)
                  : (_ideas == null || _ideas!.isEmpty)
                  ? ListView(
                      children: const [
                        SizedBox(height: 100),
                        Center(
                          child: Text(
                            'لا توجد أفكار مخزّنة — جرّب توليد أفكار جديدة',
                            style: TextStyle(color: AppColors.textMuted),
                          ),
                        ),
                      ],
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.symmetric(horizontal: 14),
                      itemCount: _ideas!.length,
                      itemBuilder: (context, i) => IdeaCard(
                        idea: _ideas![i],
                        onUse: () => _useIdea(_ideas![i]),
                      ),
                    ),
            ),
          ),
        ],
      ),
    );
  }
}
