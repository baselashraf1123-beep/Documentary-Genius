import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/nav_controller.dart';
import 'dashboard_tab.dart';
import 'episodes_tab.dart';
import 'ideas_tab.dart';
import 'produce_tab.dart';
import 'settings_screen.dart';

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  final _pages = const [
    DashboardTab(),
    ProduceTab(),
    EpisodesTab(),
    IdeasTab(),
    SettingsScreen(showAppBarBack: false),
  ];

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => NavController(),
      child: Consumer<NavController>(
        builder: (context, nav, _) => Scaffold(
          body: SafeArea(
            child: IndexedStack(index: nav.index, children: _pages),
          ),
          bottomNavigationBar: BottomNavigationBar(
            currentIndex: nav.index,
            onTap: (i) => nav.goTo(i),
            items: const [
              BottomNavigationBarItem(
                icon: Icon(Icons.dashboard_outlined),
                activeIcon: Icon(Icons.dashboard),
                label: 'الرئيسية',
              ),
              BottomNavigationBarItem(
                icon: Icon(Icons.movie_creation_outlined),
                activeIcon: Icon(Icons.movie_creation),
                label: 'إنتاج جديد',
              ),
              BottomNavigationBarItem(
                icon: Icon(Icons.video_library_outlined),
                activeIcon: Icon(Icons.video_library),
                label: 'الأرشيف',
              ),
              BottomNavigationBarItem(
                icon: Icon(Icons.lightbulb_outline),
                activeIcon: Icon(Icons.lightbulb),
                label: 'الأفكار',
              ),
              BottomNavigationBarItem(
                icon: Icon(Icons.settings_outlined),
                activeIcon: Icon(Icons.settings),
                label: 'الإعدادات',
              ),
            ],
          ),
        ),
      ),
    );
  }
}
