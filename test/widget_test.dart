// Basic smoke test for Documentary Genius app.
//
// Verifies the app boots to the splash screen without throwing.

import 'package:flutter_test/flutter_test.dart';

import 'package:documentary_genius/main.dart';

void main() {
  testWidgets('App boots and shows splash screen', (WidgetTester tester) async {
    await tester.pumpWidget(const DocumentaryGeniusApp());

    // Allow the first frame to settle without waiting for network calls.
    await tester.pump();

    // The splash screen should show the app's Arabic subtitle.
    expect(find.text('أسرار ما وراء الأفق'), findsOneWidget);
  });
}
