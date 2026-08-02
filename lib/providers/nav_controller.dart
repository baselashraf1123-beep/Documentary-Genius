import 'package:flutter/foundation.dart';

/// وحدة تحكم مبسّطة للتنقل بين تبويبات الشاشة الرئيسية (HomeShell)
/// تسمح لأي تبويب فرعي (مثل لوحة التحكم) بالانتقال إلى تبويب آخر برمجياً
class NavController extends ChangeNotifier {
  int index = 0;

  void goTo(int i) {
    index = i;
    notifyListeners();
  }
}
