import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/app_provider.dart';
import '../theme.dart';
import 'job_progress_screen.dart';

class ProduceTab extends StatefulWidget {
  const ProduceTab({super.key});

  @override
  State<ProduceTab> createState() => _ProduceTabState();
}

class _ProduceTabState extends State<ProduceTab> {
  final _topicCtrl = TextEditingController();
  double _duration = 2;
  String? _style;
  String? _voice;
  bool _audio = true;
  bool _generateVideo = false;
  bool _submitting = false;
  String? _error;

  @override
  void dispose() {
    _topicCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final topic = _topicCtrl.text.trim();
    if (topic.isEmpty) {
      setState(() => _error = 'يرجى إدخال موضوع الحلقة');
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
    });
    final app = context.read<AppProvider>();
    try {
      final jobId = await app.api.produce(
        topic: topic,
        duration: _duration.round(),
        style: _style ?? 'غامض_ومشوق',
        voice: _voice ?? 'أنتوني_رسمي',
        audio: _audio,
        generateVideo: _generateVideo,
      );
      if (!mounted) return;
      Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => JobProgressScreen(jobId: jobId, topic: topic),
        ),
      );
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppProvider>();
    final styles = app.status?.styles ?? {};
    final voices = app.status?.voices ?? {};
    _style ??= styles.keys.isNotEmpty ? styles.keys.first : null;
    _voice ??= voices.keys.isNotEmpty ? voices.keys.first : null;

    if (app.pendingTopic != null) {
      final pending = app.pendingTopic!;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        _topicCtrl.text = pending;
        context.read<AppProvider>().clearPendingTopic();
      });
    }

    return Scaffold(
      appBar: AppBar(title: const Text('إنتاج حلقة جديدة')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'موضوع الحلقة',
              style: TextStyle(
                color: AppColors.textLight,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _topicCtrl,
              textAlign: TextAlign.right,
              maxLines: 2,
              decoration: const InputDecoration(
                hintText: 'مثال: لغز اختفاء مدينة أطلانتس المفقودة',
              ),
            ),
            const SizedBox(height: 20),
            Text(
              'مدة الحلقة: ${_duration.round()} دقيقة',
              style: const TextStyle(
                color: AppColors.textLight,
                fontWeight: FontWeight.bold,
              ),
            ),
            Slider(
              value: _duration,
              min: 1,
              max: 15,
              divisions: 14,
              label: '${_duration.round()} د',
              onChanged: (v) => setState(() => _duration = v),
            ),
            const SizedBox(height: 12),
            if (styles.isNotEmpty)
              _buildDropdown(
                'نمط السرد',
                _style,
                styles,
                (v) => setState(() => _style = v),
              ),
            const SizedBox(height: 12),
            if (voices.isNotEmpty)
              _buildDropdown(
                'الصوت',
                _voice,
                voices,
                (v) => setState(() => _voice = v),
              ),
            const SizedBox(height: 8),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              value: _audio,
              onChanged: (v) => setState(() => _audio = v),
              title: const Text(
                'توليد التعليق الصوتي (TTS)',
                style: TextStyle(color: AppColors.textLight),
              ),
            ),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              value: _generateVideo,
              onChanged: _audio
                  ? (v) => setState(() => _generateVideo = v)
                  : null,
              title: const Text(
                'توليد الصور والفيديو النهائي',
                style: TextStyle(color: AppColors.textLight),
              ),
              subtitle: const Text(
                'يستغرق وقتاً أطول (صور Pollinations + دمج FFmpeg)',
                style: TextStyle(color: AppColors.textMuted, fontSize: 11),
              ),
            ),
            if (_error != null) ...[
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppColors.danger.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  _error!,
                  style: const TextStyle(color: AppColors.danger),
                ),
              ),
            ],
            const SizedBox(height: 20),
            ElevatedButton.icon(
              onPressed: _submitting ? null : _submit,
              icon: _submitting
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: AppColors.navy,
                      ),
                    )
                  : const Icon(Icons.play_arrow),
              label: Text(_submitting ? 'جارِ بدء الإنتاج...' : 'بدء الإنتاج'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDropdown(
    String label,
    String? value,
    Map<String, String> options,
    ValueChanged<String?> onChanged,
  ) {
    return DropdownButtonFormField<String>(
      initialValue: value,
      isExpanded: true,
      dropdownColor: AppColors.navyLight,
      decoration: InputDecoration(labelText: label),
      items: options.entries
          .map(
            (e) => DropdownMenuItem(
              value: e.key,
              child: Text(
                e.key,
                style: const TextStyle(color: AppColors.textLight),
                overflow: TextOverflow.ellipsis,
              ),
            ),
          )
          .toList(),
      onChanged: onChanged,
    );
  }
}
