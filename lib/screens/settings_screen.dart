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

  // إعدادات صفحة فيسبوك
  final _fbPageIdCtrl = TextEditingController();
  final _fbTokenCtrl = TextEditingController();
  bool _fbLoading = false;
  bool _fbSaving = false;
  bool _fbTesting = false;
  String? _fbTestResult;
  bool _fbTestOk = false;
  bool _fbTokenConfigured = false;
  String _fbTokenPreview = '';

  // تغيير كلمة المرور
  final _curPassCtrl = TextEditingController();
  final _newPassCtrl = TextEditingController();
  final _confirmPassCtrl = TextEditingController();
  bool _changingPass = false;
  String? _passResult;
  bool _passOk = false;
  bool _obscurePass = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadUrl();
      _loadFacebookSettings();
    });
  }

  @override
  void dispose() {
    _urlCtrl.dispose();
    _fbPageIdCtrl.dispose();
    _fbTokenCtrl.dispose();
    _curPassCtrl.dispose();
    _newPassCtrl.dispose();
    _confirmPassCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadUrl() async {
    final app = context.read<AppProvider>();
    final url = await app.settings.getBaseUrl();
    if (!mounted) return;
    setState(() => _urlCtrl.text = url);
  }

  Future<void> _loadFacebookSettings() async {
    setState(() => _fbLoading = true);
    final app = context.read<AppProvider>();
    try {
      final fb = await app.api.getFacebookSettings();
      if (!mounted) return;
      setState(() {
        _fbPageIdCtrl.text = fb.pageId;
        _fbTokenConfigured = fb.tokenConfigured;
        _fbTokenPreview = fb.tokenPreview;
      });
    } catch (_) {
      // لا مشكلة إن فشل التحميل (مثلاً الخادم غير مضبوط بعد) — الحقول تبقى فارغة
    } finally {
      if (mounted) setState(() => _fbLoading = false);
    }
  }

  Future<void> _saveFacebookSettings() async {
    setState(() {
      _fbSaving = true;
      _fbTestResult = null;
    });
    final app = context.read<AppProvider>();
    try {
      await app.api.saveFacebookSettings(
        pageId: _fbPageIdCtrl.text.trim(),
        accessToken: _fbTokenCtrl.text.trim().isEmpty
            ? null
            : _fbTokenCtrl.text.trim(),
      );
      if (!mounted) return;
      _fbTokenCtrl.clear();
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('تم حفظ إعدادات فيسبوك')));
      await _loadFacebookSettings();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('فشل الحفظ: $e')));
    } finally {
      if (mounted) setState(() => _fbSaving = false);
    }
  }

  Future<void> _testFacebook() async {
    setState(() {
      _fbTesting = true;
      _fbTestResult = null;
    });
    final app = context.read<AppProvider>();
    try {
      final pageName = await app.api.testFacebookSettings();
      if (!mounted) return;
      setState(() {
        _fbTestOk = true;
        _fbTestResult = 'متصل بنجاح بصفحة: $pageName';
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _fbTestOk = false;
        _fbTestResult = 'فشل الاتصال: $e';
      });
    } finally {
      if (mounted) setState(() => _fbTesting = false);
    }
  }

  Future<void> _changePassword() async {
    if (_newPassCtrl.text != _confirmPassCtrl.text) {
      setState(() {
        _passOk = false;
        _passResult = 'كلمة المرور الجديدة وتأكيدها غير متطابقين';
      });
      return;
    }
    if (_newPassCtrl.text.length < 8) {
      setState(() {
        _passOk = false;
        _passResult = 'كلمة المرور الجديدة يجب أن تكون 8 أحرف على الأقل';
      });
      return;
    }
    setState(() {
      _changingPass = true;
      _passResult = null;
    });
    final app = context.read<AppProvider>();
    try {
      await app.api.changePassword(
        currentPassword: _curPassCtrl.text,
        newPassword: _newPassCtrl.text,
      );
      if (!mounted) return;
      setState(() {
        _passOk = true;
        _passResult = 'تم تغيير كلمة المرور بنجاح';
      });
      _curPassCtrl.clear();
      _newPassCtrl.clear();
      _confirmPassCtrl.clear();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _passOk = false;
        _passResult = 'فشل التغيير: $e';
      });
    } finally {
      if (mounted) setState(() => _changingPass = false);
    }
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

          const SizedBox(height: 28),
          const Divider(),
          const SizedBox(height: 12),
          Row(
            children: [
              const Icon(Icons.facebook, color: AppColors.gold, size: 20),
              const SizedBox(width: 8),
              const Text(
                'صفحة فيسبوك (للنشر التلقائي)',
                style: TextStyle(
                  color: AppColors.textLight,
                  fontWeight: FontWeight.bold,
                ),
              ),
              if (_fbLoading) ...[
                const SizedBox(width: 10),
                const SizedBox(
                  width: 12,
                  height: 12,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
              ],
            ],
          ),
          const SizedBox(height: 6),
          const Text(
            'أدخل معرّف الصفحة (Page ID) ورمز وصول الصفحة (Page Access Token) '
            'حتى يمكنك نشر كل حلقة تُنتجها مباشرة من التطبيق. اترك حقل الرمز '
            'فارغاً إن كنت لا تريد تغيير الرمز المحفوظ حالياً.',
            style: TextStyle(color: AppColors.textMuted, fontSize: 11),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _fbPageIdCtrl,
            textAlign: TextAlign.left,
            decoration: const InputDecoration(
              labelText: 'Page ID',
              prefixIcon: Icon(Icons.tag, color: AppColors.gold),
            ),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _fbTokenCtrl,
            textAlign: TextAlign.left,
            obscureText: true,
            decoration: InputDecoration(
              labelText: 'Page Access Token',
              hintText: _fbTokenConfigured
                  ? 'محفوظ حالياً: $_fbTokenPreview'
                  : 'لم يتم ضبطه بعد',
              prefixIcon: const Icon(Icons.key, color: AppColors.gold),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _fbTesting ? null : _testFacebook,
                  icon: _fbTesting
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
                  onPressed: _fbSaving ? null : _saveFacebookSettings,
                  icon: const Icon(Icons.save_outlined, size: 18),
                  label: const Text('حفظ'),
                ),
              ),
            ],
          ),
          if (_fbTestResult != null) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: (_fbTestOk ? AppColors.success : AppColors.danger)
                    .withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                _fbTestResult!,
                style: TextStyle(
                  color: _fbTestOk ? AppColors.success : AppColors.danger,
                ),
              ),
            ),
          ],

          const SizedBox(height: 28),
          const Divider(),
          const SizedBox(height: 12),
          const Text(
            'تغيير كلمة المرور',
            style: TextStyle(
              color: AppColors.textLight,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _curPassCtrl,
            obscureText: _obscurePass,
            decoration: const InputDecoration(labelText: 'كلمة المرور الحالية'),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _newPassCtrl,
            obscureText: _obscurePass,
            decoration: const InputDecoration(labelText: 'كلمة المرور الجديدة'),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _confirmPassCtrl,
            obscureText: _obscurePass,
            decoration: InputDecoration(
              labelText: 'تأكيد كلمة المرور الجديدة',
              suffixIcon: IconButton(
                icon: Icon(
                  _obscurePass ? Icons.visibility_off : Icons.visibility,
                  color: AppColors.textMuted,
                  size: 20,
                ),
                onPressed: () =>
                    setState(() => _obscurePass = !_obscurePass),
              ),
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _changingPass ? null : _changePassword,
              icon: _changingPass
                  ? const SizedBox(
                      width: 14,
                      height: 14,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.lock_reset, size: 18),
              label: const Text('تغيير كلمة المرور'),
            ),
          ),
          if (_passResult != null) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: (_passOk ? AppColors.success : AppColors.danger)
                    .withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                _passResult!,
                style: TextStyle(
                  color: _passOk ? AppColors.success : AppColors.danger,
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
