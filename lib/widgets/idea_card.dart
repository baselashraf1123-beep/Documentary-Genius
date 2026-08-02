import 'package:flutter/material.dart';

import '../models/idea.dart';
import '../theme.dart';

class IdeaCard extends StatelessWidget {
  final Idea idea;
  final VoidCallback onUse;

  const IdeaCard({super.key, required this.idea, required this.onUse});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Row(
              children: [
                if (idea.used)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 3,
                    ),
                    decoration: BoxDecoration(
                      color: AppColors.textMuted.withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: const Text(
                      'مستخدمة',
                      style: TextStyle(
                        color: AppColors.textMuted,
                        fontSize: 10,
                      ),
                    ),
                  ),
                const Spacer(),
                _mysteryStars(idea.mysteryLevel),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              idea.topic,
              textAlign: TextAlign.right,
              style: const TextStyle(
                color: AppColors.textLight,
                fontWeight: FontWeight.bold,
                fontSize: 15,
              ),
            ),
            if (idea.hookFact != null && idea.hookFact!.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(
                idea.hookFact!,
                textAlign: TextAlign.right,
                style: const TextStyle(
                  color: AppColors.textMuted,
                  fontSize: 12,
                ),
              ),
            ],
            if (idea.keywords.isNotEmpty) ...[
              const SizedBox(height: 8),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                alignment: WrapAlignment.end,
                children: idea.keywords
                    .take(5)
                    .map(
                      (k) => Chip(
                        label: Text(k, style: const TextStyle(fontSize: 10)),
                        padding: EdgeInsets.zero,
                        materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      ),
                    )
                    .toList(),
              ),
            ],
            const SizedBox(height: 10),
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton.icon(
                onPressed: idea.used ? null : onUse,
                icon: const Icon(Icons.arrow_forward, size: 16),
                label: const Text('استخدام هذه الفكرة'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _mysteryStars(int level) {
    final stars = (level / 2).clamp(0, 5).round();
    return Row(
      children: List.generate(
        5,
        (i) => Icon(
          i < stars ? Icons.star : Icons.star_border,
          size: 14,
          color: AppColors.gold,
        ),
      ),
    );
  }
}
