import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/app_provider.dart';
import '../theme.dart';
import 'login_screen.dart';

class SettingsScreen extends StatefulWidget {
  final bool showAppBarBack;
  const SettingsScreen({super.key, this.showAppBarBack = false});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _urlCtrl = TextEditingController();
  bool _testing = false;
  String? _testResult;
  bool _testOk = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadUrl());
  }

  Future<void> _loadUrl() async {
    final app = context.read<AppProvider>();
    final url = await app.settings.getBaseUrl();
    if (!mounted) return;
    setState(() => _urlCtrl.text = url);
  }

  Future<void> _save() async {
    final app = context.read<AppProvider>();
    await app.settings.setBaseUrl(_urlCtrl.text);
    if (!mounted) return;
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(const SnackBar(content: Text('تم حفظ عنوان الخادم')));
    app.refreshStatus();
  }

  Future<void> _test() async {
    setState(() {
      _testing = true;
      _testResult = null;
    });
    final app = context.read<AppProvider>();
    await app.settings.setBaseUrl(_urlCtrl.text);
    try {
      final status = await app.api.getStatus();
      if (!mounted) return;
      setState(() {
        _testOk = true;
        _testResult = 'متصل بنجاح — القناة: ${status.channel}';
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _testOk = false;
        _testResult = 'فشل الاتصال: $e';
      });
    } finally {
      if (mounted) setState(() => _testing = false);
    }
  }

  Future<void> _logout() async {
    final app = context.read<AppProvider>();
    await app.logout();
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const LoginScreen()),
      (r) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppProvider>();
    return Scaffold(
      appBar: AppBar(
        title: const Text('الإعدادات'),
        automaticallyImplyLeading: widget.showAppBarBack,
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (app.username != null) ...[
            Card(
              child: ListTile(
                leading: const Icon(
                  Icons.account_circle,
                  color: AppColors.gold,
                  size: 34,
                ),
                title: Text(
                  app.username!,
                  style: const TextStyle(color: AppColors.textLight),
                ),
                subtitle: const Text(
                  'مسجّل الدخول',
                  style: TextStyle(color: AppColors.textMuted),
                ),
              ),
            ),
            const SizedBox(height: 20),
          ],
          const Text(
            'عنوان الخادم الخلفي (Backend API)',
            style: TextStyle(
              color: AppColors.textLight,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 6),
          const Text(
            'ملاحظة: عنوان معاينة الرمل الآلي مؤقت وقد يتغيّر بين الجلسات. عند نشر الخادم على استضافة دائمة، حدّث هذا العنوان.',
            style: TextStyle(color: AppColors.textMuted, fontSize: 11),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _urlCtrl,
            textAlign: TextAlign.left,
            decoration: const InputDecoration(
              hintText: 'https://your-backend-domain.com',
              prefixIcon: Icon(Icons.dns_outlined, color: AppColors.gold),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _testing ? null : _test,
                  icon: _testing
                      ? const SizedBox(
                          width: 14,
                          height: 14,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.wifi_tethering, size: 18),
                  label: const Text('اختبار الاتصال'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: _save,
                  icon: const Icon(Icons.save_outlined, size: 18),
                  label: const Text('حفظ'),
                ),
              ),
            ],
          ),
          if (_testResult != null) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: (_testOk ? AppColors.success : AppColors.danger)
                    .withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                _testResult!,
                style: TextStyle(
                  color: _testOk ? AppColors.success : AppColors.danger,
                ),
              ),
            ),
          ],
          const SizedBox(height: 32),
          if (app.username != null)
            OutlinedButton.icon(
              onPressed: _logout,
              style: OutlinedButton.styleFrom(
                foregroundColor: AppColors.danger,
                side: const BorderSide(color: AppColors.danger),
              ),
              icon: const Icon(Icons.logout),
              label: const Text('تسجيل الخروج'),
            ),
          const SizedBox(height: 24),
          const Center(
            child: Text(
              'Documentary Genius v1.0.0',
              style: TextStyle(color: AppColors.textMuted, fontSize: 11),
            ),
          ),
        ],
      ),
    );
  }
}
