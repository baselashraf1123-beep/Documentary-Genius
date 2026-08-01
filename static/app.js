// ══════════════════════════════════════════════════════════════
// نظام إنتاج الوثائقيات الذكي — الجافاسكريبت الكامل (v4.0 مجاني)
// ══════════════════════════════════════════════════════════════
let currentData = null;
let currentTab = 'script';
let isLoggedIn = false;
let pollTimer = null;

// ══════════════════════════════════════════════════════════════
// Login / Logout
// ══════════════════════════════════════════════════════════════
async function doLogin() {
  const username = document.getElementById('login-username').value.trim();
  const password = document.getElementById('login-password').value;
  try {
    const res = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    const data = await res.json();
    if (data.success) {
      isLoggedIn = true;
      document.getElementById('login-modal').classList.remove('active');
      document.getElementById('logout-btn').classList.remove('hidden');
      showToast('تم تسجيل الدخول بنجاح');
      checkStatus();
    } else {
      showToast(data.error || 'فشل تسجيل الدخول', 'error');
    }
  } catch (e) {
    showToast('خطأ في الاتصال', 'error');
  }
}

async function doLogout() {
  try {
    await fetch('/api/logout', { method: 'POST' });
    isLoggedIn = false;
    document.getElementById('login-modal').classList.add('active');
    document.getElementById('logout-btn').classList.add('hidden');
    showToast('تم تسجيل الخروج');
  } catch (e) {}
}

document.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && document.getElementById('login-modal').classList.contains('active')) {
    doLogin();
  }
});

// ══════════════════════════════════════════════════════════════
// Status Check
// ══════════════════════════════════════════════════════════════
async function checkStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    const indicator = document.getElementById('status-indicator');
    const text = document.getElementById('status-text');
    indicator.className = 'flex items-center gap-2 px-3 py-1.5 rounded-full bg-green-900/30 border border-green-700';
    text.className = 'text-xs font-bold text-green-400';
    text.textContent = '✅ جاهز — نظام مجاني بالكامل';
    if (data.logged_in) {
      isLoggedIn = true;
      document.getElementById('login-modal').classList.remove('active');
      document.getElementById('logout-btn').classList.remove('hidden');
    }
  } catch (e) {
    document.getElementById('status-text').textContent = 'الخادم غير متصل';
  }
}
checkStatus();

// ══════════════════════════════════════════════════════════════
// Utilities
// ══════════════════════════════════════════════════════════════
function showToast(msg, type) {
  const toast = document.getElementById('toast');
  toast.textContent = msg;
  if (type === 'error') { toast.style.borderColor = '#ef4444'; toast.style.color = '#ef4444'; }
  else { toast.style.borderColor = 'var(--gold)'; toast.style.color = 'var(--gold)'; }
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 3000);
}

function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function copyText(el) {
  const text = el.parentElement.querySelector('p')?.textContent || '';
  navigator.clipboard.writeText(text).then(() => showToast('تم النسخ!'));
}

function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
  document.querySelector('[data-tab="' + tab + '"]').classList.add('active');
  document.getElementById('tab-' + tab).classList.remove('hidden');
}

function downloadJSON(data, filename) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click();
  document.body.removeChild(a); URL.revokeObjectURL(url);
}

// ══════════════════════════════════════════════════════════════
// Production (Async Job + Real Progress Polling)
// ══════════════════════════════════════════════════════════════
async function produceEpisode() {
  const topic = document.getElementById('topic-input').value.trim();
  if (!topic) { showToast('الرجاء إدخال موضوع الحلقة', 'error'); return; }
  const btn = document.getElementById('produce-btn');
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner" style="width:20px;height:20px;border-width:2px;"></div> <span>جاري الإنتاج...</span>';

  const progressSection = document.getElementById('progress-section');
  const progressBar = document.getElementById('progress-bar');
  const progressPercent = document.getElementById('progress-percent');
  const progressLog = document.getElementById('progress-log');
  const progressTitle = document.getElementById('progress-title');

  progressSection.classList.remove('hidden');
  document.getElementById('results-section').classList.add('hidden');
  document.getElementById('ideas-section').classList.add('hidden');
  document.getElementById('packages-section').classList.add('hidden');

  progressBar.style.width = '0%';
  progressPercent.textContent = '0%';
  progressTitle.textContent = 'بدء الإنتاج...';
  progressLog.innerHTML = '';

  const logs = [];
  let lastPct = -1;
  function addLog(msg) {
    if (logs.length && logs[logs.length - 1] === msg) return;
    logs.push(msg);
    progressLog.innerHTML = logs.slice(-10).map(l => '<div class="text-gray-400">→ ' + l + '</div>').join('');
    progressLog.scrollTop = progressLog.scrollHeight;
  }

  const generateVideo = document.getElementById('video-toggle').checked;

  try {
    const res = await fetch('/api/produce', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        topic: topic,
        duration: parseInt(document.getElementById('duration-select').value),
        style: document.getElementById('style-select').value,
        voice: document.getElementById('voice-select').value,
        audio: document.getElementById('audio-toggle').checked,
        generate_video: generateVideo
      })
    });
    const startData = await res.json();
    if (!startData.success) throw new Error(startData.error || 'فشل بدء الإنتاج');

    const jobId = startData.job_id;

    await new Promise((resolve, reject) => {
      pollTimer = setInterval(async () => {
        try {
          const sres = await fetch('/api/produce/status/' + jobId);
          const sdata = await sres.json();
          if (sdata.progress !== undefined && sdata.progress !== lastPct) {
            lastPct = sdata.progress;
            progressBar.style.width = sdata.progress + '%';
            progressPercent.textContent = sdata.progress + '%';
            progressTitle.textContent = sdata.message || 'جاري الإنتاج...';
            addLog(sdata.message || '...');
          }
          if (sdata.status === 'done') {
            clearInterval(pollTimer);
            currentData = sdata.data;
            progressTitle.textContent = 'اكتمل الإنتاج بنجاح!';
            addLog('الحزمة الإنتاجية اكتملت في ' + (currentData.elapsed_sec || '?') + ' ثانية');
            setTimeout(() => {
              progressSection.classList.add('hidden');
              renderResults();
              document.getElementById('results-section').classList.remove('hidden');
              showToast('تم إنتاج الحلقة بنجاح!');
              resolve();
            }, 1200);
          } else if (sdata.status === 'error') {
            clearInterval(pollTimer);
            reject(new Error(sdata.error || 'خطأ غير معروف في الإنتاج'));
          }
        } catch (e) {
          clearInterval(pollTimer);
          reject(e);
        }
      }, 1500);
    });

  } catch (err) {
    if (pollTimer) clearInterval(pollTimer);
    progressTitle.textContent = 'فشل الإنتاج';
    addLog('خطأ: ' + err.message);
    showToast('فشل الإنتاج: ' + err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-rocket"></i><span>🚀 إنتاج الحلقة الكاملة</span>';
  }
}

// ══════════════════════════════════════════════════════════════
// Render Results
// ══════════════════════════════════════════════════════════════
function renderResults() {
  if (!currentData) return;
  renderScript();
  renderScenes();
  renderSEO();
  renderAudio();
  renderVideo();
  renderPackage();
  switchTab('script');
}

function renderScript() {
  const sc = currentData.script || {};
  let html = '<div class="space-y-4">';
  html += '<div class="glass-gold rounded-xl p-5">';
  html += '<h4 class="text-xl font-black text-gold mb-2">' + escapeHtml(sc.title || 'بدون عنوان') + '</h4>';
  html += '<p class="text-gray-400">' + escapeHtml(sc.subtitle || '') + '</p>';
  html += '<div class="flex flex-wrap gap-2 mt-3 text-sm">';
  html += '<span class="px-3 py-1 rounded-full bg-yellow-900/30 text-yellow-400 border border-yellow-700/50">⏱️ ' + currentData.duration_min + ' دقائق</span>';
  html += '<span class="px-3 py-1 rounded-full bg-purple-900/30 text-purple-400 border border-purple-700/50">🎨 ' + (sc.sections ? sc.sections.length : 0) + ' أقسام</span>';
  html += '<span class="px-3 py-1 rounded-full bg-blue-900/30 text-blue-400 border border-blue-700/50">🤖 محرك مجاني</span>';
  html += '</div></div>';
  if (sc.hook) {
    html += '<div class="section-card"><h4>🔥 Hook الافتتاحي</h4><p class="text-gray-300 leading-relaxed text-lg">' + escapeHtml(sc.hook) + '</p></div>';
  }
  (sc.sections || []).forEach((sec, i) => {
    html += '<div class="section-card hover-lift">';
    html += '<div class="flex justify-between items-start mb-2">';
    html += '<h4>القسم ' + (sec.id || i+1) + ': ' + escapeHtml(sec.name || '') + '</h4>';
    html += '<span class="text-xs px-2 py-1 rounded bg-gray-800 text-gray-400">' + (sec.duration_seconds || 30) + ' ث</span>';
    html += '</div>';
    html += '<p class="text-gray-300 leading-relaxed mb-3">' + escapeHtml(sec.script || '') + '</p>';
    html += '<div class="flex flex-wrap gap-2 text-xs">';
    if (sec.tone) html += '<span class="px-2 py-1 rounded bg-purple-900/30 text-purple-400 border border-purple-700/30">🎭 ' + escapeHtml(sec.tone) + '</span>';
    if (sec.key_visual) html += '<span class="px-2 py-1 rounded bg-blue-900/30 text-blue-400 border border-blue-700/30">🎬 ' + escapeHtml(sec.key_visual) + '</span>';
    html += '</div></div>';
  });
  if (sc.key_facts && sc.key_facts.length) {
    html += '<div class="section-card"><h4>📊 حقائق علمية</h4><ul class="space-y-2">';
    sc.key_facts.forEach(f => { html += '<li class="text-gray-300 flex items-start gap-2"><span class="text-gold">✓</span>' + escapeHtml(f) + '</li>'; });
    html += '</ul></div>';
  }
  if (sc.closing_question) {
    html += '<div class="section-card glass-gold"><h4>❓ السؤال الختامي</h4><p class="text-xl text-gray-200 font-bold leading-relaxed">' + escapeHtml(sc.closing_question) + '</p></div>';
  }
  if (sc.full_script) {
    html += '<div class="section-card"><h4>📄 النص الكامل</h4><div class="bg-gray-900/50 rounded-lg p-4 max-h-96 overflow-y-auto"><p class="text-gray-300 leading-loose whitespace-pre-wrap">' + escapeHtml(sc.full_script) + '</p></div></div>';
  }
  html += '</div>';
  document.getElementById('script-content').innerHTML = html;
}

function renderScenes() {
  const sc = currentData.scenes || {};
  let html = '<div class="space-y-4">';
  html += '<div class="glass-gold rounded-xl p-5">';
  html += '<div class="grid grid-cols-1 md:grid-cols-3 gap-4">';
  html += '<div><span class="text-gray-500 text-sm">التوجيه اللوني</span><p class="text-gold font-bold">' + escapeHtml(sc.color_grade || '') + '</p></div>';
  html += '<div><span class="text-gray-500 text-sm">الموضوع الموسيقي</span><p class="text-gold font-bold">' + escapeHtml(sc.music_theme || '') + '</p></div>';
  html += '<div><span class="text-gray-500 text-sm">الخط المقترح</span><p class="text-gold font-bold">' + escapeHtml(sc.font_recommendation || '') + '</p></div>';
  html += '</div></div>';
  (sc.sections || []).forEach((sec, i) => {
    html += '<div class="section-card hover-lift">';
    html += '<div class="flex justify-between items-start mb-3">';
    html += '<h4>مشهد ' + (sec.section_id || i+1) + ': ' + escapeHtml(sec.shot_type || '') + '</h4>';
    html += '<span class="text-xs px-2 py-1 rounded bg-gray-800 text-gray-400">' + (sec.duration_seconds || 30) + ' ث</span>';
    html += '</div>';
    if (sec.veo3_prompt) {
      html += '<div class="mb-3"><span class="text-xs text-purple-400 font-bold">🎬 Veo 3 Prompt:</span>';
      html += '<div class="bg-gray-900/50 rounded-lg p-3 mt-1"><p class="text-gray-300 text-sm font-mono">' + escapeHtml(sec.veo3_prompt) + '</p></div></div>';
    }
    if (sec.midjourney_prompt) {
      html += '<div class="mb-3"><span class="text-xs text-blue-400 font-bold">🖼️ Midjourney Prompt:</span>';
      html += '<div class="bg-gray-900/50 rounded-lg p-3 mt-1"><p class="text-gray-300 text-sm font-mono">' + escapeHtml(sec.midjourney_prompt) + '</p></div></div>';
    }
    html += '<div class="grid grid-cols-2 gap-2 text-sm">';
    if (sec.lighting) html += '<div class="bg-gray-800/50 rounded-lg p-2"><span class="text-gray-500 text-xs">💡 إضاءة:</span><p class="text-gray-300">' + escapeHtml(sec.lighting) + '</p></div>';
    if (sec.music_mood) html += '<div class="bg-gray-800/50 rounded-lg p-2"><span class="text-gray-500 text-xs">🎵 موسيقى:</span><p class="text-gray-300">' + escapeHtml(sec.music_mood) + '</p></div>';
    html += '</div>';
    if (sec.broll_ideas && sec.broll_ideas.length) {
      html += '<div class="mt-3"><span class="text-xs text-gray-500">🎥 B-Roll:</span><div class="flex flex-wrap gap-2 mt-1">';
      sec.broll_ideas.forEach(b => { html += '<span class="px-2 py-1 rounded-full bg-gray-800 text-gray-300 text-xs">' + escapeHtml(b) + '</span>'; });
      html += '</div></div>';
    }
    if (sec.sfx && sec.sfx.length) {
      html += '<div class="mt-2"><span class="text-xs text-gray-500">🔊 SFX:</span><div class="flex flex-wrap gap-2 mt-1">';
      sec.sfx.forEach(s => { html += '<span class="px-2 py-1 rounded-full bg-gray-800 text-gray-300 text-xs">' + escapeHtml(s) + '</span>'; });
      html += '</div></div>';
    }
    if (sec.overlay_text) {
      html += '<div class="mt-2 bg-yellow-900/20 border border-yellow-700/30 rounded-lg p-2"><span class="text-xs text-yellow-500">📝 نص الشاشة:</span><p class="text-yellow-300 text-sm">' + escapeHtml(sec.overlay_text) + '</p></div>';
    }
    html += '</div>';
  });
  if (sc.thumbnail_prompt) {
    html += '<div class="section-card glass-gold"><h4>🖼️ Thumbnail Prompt</h4><p class="text-gray-300 text-sm font-mono">' + escapeHtml(sc.thumbnail_prompt) + '</p></div>';
  }
  html += '</div>';
  document.getElementById('scenes-content').innerHTML = html;
}

function renderSEO() {
  const seo = currentData.seo || {};
  let html = '<div class="space-y-4">';
  if (seo.titles && seo.titles.length) {
    html += '<div class="section-card"><h4>🎯 عناوين مقترحة</h4><div class="space-y-2">';
    seo.titles.forEach((t, i) => {
      html += '<div class="flex items-center gap-3 bg-gray-900/50 rounded-lg p-3">';
      html += '<span class="w-8 h-8 rounded-full bg-gold text-black flex items-center justify-center font-bold text-sm">' + (i+1) + '</span>';
      html += '<p class="text-gray-200 font-bold flex-1">' + escapeHtml(t) + '</p>';
      html += '<button onclick="copyText(this)" class="text-gold hover:text-white transition" title="نسخ"><i class="fas fa-copy"></i></button>';
      html += '</div>';
    });
    html += '</div></div>';
  }
  if (seo.description) {
    html += '<div class="section-card"><h4>📝 وصف YouTube</h4><div class="bg-gray-900/50 rounded-lg p-4"><p class="text-gray-300 leading-relaxed whitespace-pre-wrap">' + escapeHtml(seo.description) + '</p></div></div>';
  }
  if (seo.tags && seo.tags.length) {
    html += '<div class="section-card"><h4>🏷️ الوسوم (' + seo.tags.length + ')</h4><div class="flex flex-wrap gap-2">';
    seo.tags.forEach(t => { html += '<span class="px-3 py-1.5 rounded-full bg-blue-900/30 text-blue-300 border border-blue-700/30 text-sm">' + escapeHtml(t) + '</span>'; });
    html += '</div></div>';
  }
  if (seo.hashtags && seo.hashtags.length) {
    html += '<div class="section-card"><h4>🔥 الهاشتاقات (' + seo.hashtags.length + ')</h4><div class="flex flex-wrap gap-2">';
    seo.hashtags.forEach(h => { html += '<span class="px-3 py-1.5 rounded-full bg-purple-900/30 text-purple-300 border border-purple-700/30 text-sm">' + escapeHtml(h) + '</span>'; });
    html += '</div></div>';
  }
  if (seo.chapters && seo.chapters.length) {
    html += '<div class="section-card"><h4>📑 شابترز الفيديو</h4><div class="space-y-2">';
    seo.chapters.forEach(c => {
      html += '<div class="flex items-center gap-3 bg-gray-900/50 rounded-lg p-3">';
      html += '<span class="px-2 py-1 rounded bg-gold text-black font-bold text-xs">' + c.time + '</span>';
      html += '<p class="text-gray-300">' + escapeHtml(c.title) + '</p>';
      html += '</div>';
    });
    html += '</div></div>';
  }
  if (seo.thumbnail_text) {
    html += '<div class="section-card glass-gold"><h4>🖼️ نص الثمبنيل</h4><p class="text-2xl text-gold font-black">' + escapeHtml(seo.thumbnail_text) + '</p></div>';
  }
  if (seo.thumbnail_style) {
    html += '<div class="section-card"><h4>🎨 توجيه تصميم الثمبنيل</h4><p class="text-gray-300">' + escapeHtml(seo.thumbnail_style) + '</p></div>';
  }
  if (seo.primary_keywords && seo.primary_keywords.length) {
    html += '<div class="section-card"><h4>🔑 الكلمات المفتاحية</h4><div class="flex flex-wrap gap-2">';
    seo.primary_keywords.forEach(k => { html += '<span class="px-3 py-1.5 rounded-full bg-green-900/30 text-green-300 border border-green-700/30 text-sm">' + escapeHtml(k) + '</span>'; });
    html += '</div></div>';
  }
  if (seo.call_to_action) {
    html += '<div class="section-card"><h4>📢 Call to Action</h4><p class="text-gray-300 font-bold">' + escapeHtml(seo.call_to_action) + '</p></div>';
  }
  if (seo.best_upload_day || seo.best_upload_time) {
    html += '<div class="section-card"><h4>📅 أفضل وقت للرفع</h4><div class="flex gap-4">';
    if (seo.best_upload_day) html += '<span class="px-3 py-1 rounded-full bg-gray-800 text-gray-300">📆 ' + escapeHtml(seo.best_upload_day) + '</span>';
    if (seo.best_upload_time) html += '<span class="px-3 py-1 rounded-full bg-gray-800 text-gray-300">🕐 ' + escapeHtml(seo.best_upload_time) + '</span>';
    html += '</div></div>';
  }
  if (seo.community_post_text) {
    html += '<div class="section-card"><h4>💬 Community Post</h4><div class="bg-gray-900/50 rounded-lg p-4"><p class="text-gray-300 leading-relaxed">' + escapeHtml(seo.community_post_text) + '</p></div></div>';
  }
  html += '</div>';
  document.getElementById('seo-content').innerHTML = html;
}

function renderAudio() {
  const audioFile = currentData.audio_file;
  let html = '<div class="space-y-4">';
  if (audioFile) {
    html += '<div class="section-card glass-gold text-center py-8">';
    html += '<div class="text-6xl mb-4">🎙️</div>';
    html += '<h4 class="text-xl font-black text-gold mb-2">التعليق الصوتي جاهز</h4>';
    html += '<p class="text-gray-400 mb-4">تم توليد الملف الصوتي مجاناً عبر محرك Edge-TTS العربي</p>';
    html += '<audio controls class="w-full rounded-xl" style="background:#1a1a2e;">';
    html += '<source src="/api/media/audio/' + audioFile + '" type="audio/mpeg">متصفحك لا يدعم تشغيل الصوت';
    html += '</audio>';
    html += '<div class="flex justify-center gap-3 mt-4">';
    html += '<a href="/api/download/audio/' + audioFile + '" download class="btn-outline px-4 py-2 rounded-lg text-sm inline-flex items-center gap-2"><i class="fas fa-download"></i> تحميل MP3</a>';
    html += '</div></div>';
  } else {
    html += '<div class="section-card text-center py-12"><div class="text-5xl mb-4 text-gray-600">🔇</div><h4 class="text-lg font-bold text-gray-400">لم يتم توليد الصوت</h4><p class="text-gray-500 text-sm mt-2">فعّل خيار "صوت" عند الإنتاج للحصول على تعليق صوتي عربي مجاني</p></div>';
  }
  html += '</div>';
  document.getElementById('audio-content').innerHTML = html;
}

function renderVideo() {
  const videoFile = currentData.video_file;
  let html = '<div class="space-y-4">';
  if (videoFile) {
    html += '<div class="section-card glass-gold text-center py-8">';
    html += '<div class="text-6xl mb-4">🎥</div>';
    html += '<h4 class="text-xl font-black text-gold mb-2">الفيديو النهائي جاهز</h4>';
    html += '<p class="text-gray-400 mb-4">تم دمج الصور والصوت مجاناً باستخدام FFmpeg</p>';
    html += '<video controls class="w-full rounded-xl" style="max-height:500px;">';
    html += '<source src="/api/media/videos/' + videoFile + '" type="video/mp4">متصفحك لا يدعم تشغيل الفيديو';
    html += '</video>';
    html += '<div class="flex justify-center gap-3 mt-4">';
    html += '<a href="/api/download/videos/' + videoFile + '" download class="btn-gold px-6 py-3 rounded-lg inline-flex items-center gap-2"><i class="fas fa-download"></i> تحميل MP4</a>';
    html += '</div></div>';
  } else {
    html += '<div class="section-card text-center py-12"><div class="text-5xl mb-4 text-gray-600">🎬</div><h4 class="text-lg font-bold text-gray-400">لم يتم توليد الفيديو</h4><p class="text-gray-500 text-sm mt-2">فعّل خيار "فيديو" لإنشاء فيديو كامل من الصور والصوت مجاناً</p></div>';
  }
  html += '</div>';
  document.getElementById('video-content').innerHTML = html;
}

function renderPackage() {
  const pkg = currentData;
  let html = '<div class="space-y-4">';
  html += '<div class="glass-gold rounded-xl p-6 text-center">';
  html += '<div class="text-5xl mb-3">📦</div>';
  html += '<h4 class="text-2xl font-black text-gold mb-2">الحزمة الإنتاجية الكاملة</h4>';
  html += '<p class="text-gray-400">جميع عناصر الإنتاج في ملف JSON واحد</p>';
  html += '<div class="grid grid-cols-2 md:grid-cols-5 gap-3 mt-4">';
  html += '<div class="bg-gray-900/50 rounded-lg p-3"><div class="text-2xl">📝</div><div class="text-gold font-bold">' + (pkg.script && pkg.script.sections ? pkg.script.sections.length : 0) + '</div><div class="text-xs text-gray-500">أقسام</div></div>';
  html += '<div class="bg-gray-900/50 rounded-lg p-3"><div class="text-2xl">🎬</div><div class="text-gold font-bold">' + (pkg.scenes && pkg.scenes.sections ? pkg.scenes.sections.length : 0) + '</div><div class="text-xs text-gray-500">مشاهد</div></div>';
  html += '<div class="bg-gray-900/50 rounded-lg p-3"><div class="text-2xl">🏷️</div><div class="text-gold font-bold">' + (pkg.seo && pkg.seo.tags ? pkg.seo.tags.length : 0) + '</div><div class="text-xs text-gray-500">وسوم</div></div>';
  html += '<div class="bg-gray-900/50 rounded-lg p-3"><div class="text-2xl">🖼️</div><div class="text-gold font-bold">' + (pkg.images_count || 0) + '</div><div class="text-xs text-gray-500">صور</div></div>';
  html += '<div class="bg-gray-900/50 rounded-lg p-3"><div class="text-2xl">⏱️</div><div class="text-gold font-bold">' + pkg.elapsed_sec + 'ث</div><div class="text-xs text-gray-500">الوقت</div></div>';
  html += '</div></div>';
  html += '<div class="section-card"><h4>📄 JSON الكامل</h4><div class="bg-gray-900 rounded-lg p-4 max-h-96 overflow-y-auto"><pre class="text-xs text-gray-300 font-mono whitespace-pre-wrap">' + escapeHtml(JSON.stringify(pkg, null, 2)) + '</pre></div></div>';
  html += '</div>';
  document.getElementById('package-content').innerHTML = html;
}

// ══════════════════════════════════════════════════════════════
// Download Functions
// ══════════════════════════════════════════════════════════════
function copyScript() { if (currentData && currentData.script) navigator.clipboard.writeText(JSON.stringify(currentData.script, null, 2)).then(() => showToast('تم نسخ السكريبت!')); }
function downloadScript() { if (currentData && currentData.script) downloadJSON(currentData.script, 'script_' + (currentData.script.title || 'episode') + '.json'); }
function copyScenes() { if (currentData && currentData.scenes) navigator.clipboard.writeText(JSON.stringify(currentData.scenes, null, 2)).then(() => showToast('تم نسخ المشاهد!')); }
function downloadScenes() { if (currentData && currentData.scenes) downloadJSON(currentData.scenes, 'scenes_' + (currentData.script?.title || 'episode') + '.json'); }
function copySEO() { if (currentData && currentData.seo) navigator.clipboard.writeText(JSON.stringify(currentData.seo, null, 2)).then(() => showToast('تم نسخ SEO!')); }
function downloadSEO() { if (currentData && currentData.seo) downloadJSON(currentData.seo, 'seo_' + (currentData.script?.title || 'episode') + '.json'); }
function downloadPackage() { if (currentData) downloadJSON(currentData, 'production_package_' + (currentData.script?.title || 'episode') + '.json'); }

// ══════════════════════════════════════════════════════════════
// Ideas Generator
// ══════════════════════════════════════════════════════════════
async function generateIdeas() {
  document.getElementById('results-section').classList.add('hidden');
  document.getElementById('packages-section').classList.add('hidden');
  const section = document.getElementById('ideas-section');
  section.classList.remove('hidden');
  const grid = document.getElementById('ideas-grid');
  grid.innerHTML = '<div class="col-span-full text-center py-12"><div class="spinner mx-auto mb-4"></div><p class="text-gray-400">جاري توليد الأفكار...</p></div>';
  try {
    const res = await fetch('/api/ideas', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ count: 9, topic_hint: document.getElementById('topic-input').value })
    });
    const data = await res.json();
    if (data.success) {
      renderIdeasGrid(data.ideas);
    } else {
      throw new Error(data.error);
    }
  } catch (err) {
    grid.innerHTML = '<div class="col-span-full text-center py-8 text-red-400"><i class="fas fa-exclamation-triangle text-3xl mb-2"></i><p>خطأ: ' + err.message + '</p></div>';
  }
}

async function loadStoredIdeas() {
  document.getElementById('results-section').classList.add('hidden');
  document.getElementById('packages-section').classList.add('hidden');
  const section = document.getElementById('ideas-section');
  section.classList.remove('hidden');
  const grid = document.getElementById('ideas-grid');
  grid.innerHTML = '<div class="col-span-full text-center py-12"><div class="spinner mx-auto mb-4"></div><p class="text-gray-400">جاري تحميل الأفكار المخزنة...</p></div>';
  try {
    const res = await fetch('/api/ideas/stored?unused=true');
    const data = await res.json();
    if (data.success) {
      renderIdeasGrid(data.ideas, true);
    } else {
      throw new Error(data.error);
    }
  } catch (err) {
    grid.innerHTML = '<div class="col-span-full text-center py-8 text-red-400"><p>خطأ: ' + err.message + '</p></div>';
  }
}

function renderIdeasGrid(ideas, stored = false) {
  const grid = document.getElementById('ideas-grid');
  if (!ideas || ideas.length === 0) {
    grid.innerHTML = '<div class="col-span-full text-center py-8 text-gray-500"><p>لا توجد أفكار</p></div>';
    return;
  }
  grid.innerHTML = '';
  ideas.forEach(idea => {
    const stars = '⭐'.repeat(Math.floor((idea.mystery_level || 5) / 2));
    const potentialColor = idea.potential === 'عالي' ? 'text-green-400' : idea.potential === 'متوسط' ? 'text-yellow-400' : 'text-gray-400';
    const ideaId = idea.id || '';
    grid.innerHTML += '<div class="idea-card" onclick="useIdea(this)" data-topic="' + escapeHtml(idea.topic) + '"' + (stored ? ' data-id="' + ideaId + '"' : '') + '>' +
      '<div class="flex justify-between items-start mb-2">' +
      '<h4 class="text-lg font-bold text-gold">' + escapeHtml(idea.topic) + '</h4>' +
      '<span class="text-xs px-2 py-1 rounded bg-gray-800 ' + potentialColor + '">' + (idea.potential || '') + '</span>' +
      '</div>' +
      '<p class="text-gray-400 text-sm mb-3 leading-relaxed">' + escapeHtml(idea.hook_fact || '') + '</p>' +
      '<div class="flex justify-between items-center">' +
      '<span class="mystery-stars text-sm">' + stars + '</span>' +
      '<span class="text-xs text-gray-500">غموض: ' + (idea.mystery_level || 5) + '/10</span>' +
      '</div>' +
      (idea.estimated_duration ? '<div class="mt-2 text-xs text-gray-500">⏱️ ' + escapeHtml(idea.estimated_duration) + '</div>' : '') +
      '</div>';
  });
}

function useIdea(el) {
  const title = el.getAttribute('data-topic');
  const ideaId = el.getAttribute('data-id');
  document.getElementById('topic-input').value = title;
  if (ideaId) {
    fetch('/api/ideas/use/' + ideaId, { method: 'POST' }).catch(() => {});
  }
  showToast('تم نقل الفكرة إلى حقل الموضوع');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ══════════════════════════════════════════════════════════════
// Packages Archive
// ══════════════════════════════════════════════════════════════
async function loadPackages() {
  document.getElementById('results-section').classList.add('hidden');
  document.getElementById('ideas-section').classList.add('hidden');
  const section = document.getElementById('packages-section');
  section.classList.remove('hidden');
  const list = document.getElementById('packages-list');
  list.innerHTML = '<div class="text-center py-12"><div class="spinner mx-auto mb-4"></div><p class="text-gray-400">جاري تحميل الأرشيف...</p></div>';
  try {
    const res = await fetch('/api/packages');
    const data = await res.json();
    if (data.packages && data.packages.length) {
      list.innerHTML = '<div class="space-y-3">';
      data.packages.forEach(pkg => {
        list.innerHTML += '<div class="section-card hover-lift flex items-center justify-between cursor-pointer" onclick="loadPackageDetail(' + pkg.id + ')">' +
          '<div class="flex items-center gap-4">' +
          '<div class="w-12 h-12 rounded-xl bg-gradient-to-br from-yellow-600 to-amber-800 flex items-center justify-center text-xl">📦</div>' +
          '<div>' +
          '<h4 class="font-bold text-gold">' + escapeHtml(pkg.title || pkg.topic) + '</h4>' +
          '<p class="text-sm text-gray-400">' + escapeHtml(pkg.topic) + ' · ' + pkg.duration + ' دقائق · ' + (pkg.has_video ? '🎥 فيديو' : pkg.has_audio ? '🎙️ صوت' : '🔇 نص فقط') + '</p>' +
          '</div></div>' +
          '<div class="text-left flex items-center gap-3">' +
          '<p class="text-xs text-gray-500">' + (pkg.date ? pkg.date.split('T')[0] : '') + '</p>' +
          '<button onclick="event.stopPropagation(); deletePackage(' + pkg.id + ')" class="text-red-400 hover:text-red-300 transition" title="حذف"><i class="fas fa-trash"></i></button>' +
          '</div>' +
          '</div>';
      });
      list.innerHTML += '</div>';
    } else {
      list.innerHTML = '<div class="text-center py-12 text-gray-500"><i class="fas fa-inbox text-4xl mb-3"></i><p>لا توجد حلقات في الأرشيف بعد</p></div>';
    }
  } catch (err) {
    list.innerHTML = '<div class="text-center py-8 text-red-400"><p>خطأ في تحميل الأرشيف</p></div>';
  }
}

async function loadPackageDetail(epId) {
  showToast('جاري تحميل الحلقة...');
  try {
    const res = await fetch('/api/packages/' + epId);
    const data = await res.json();
    if (data.success) {
      currentData = data.data;
      document.getElementById('packages-section').classList.add('hidden');
      renderResults();
      document.getElementById('results-section').classList.remove('hidden');
      showToast('تم تحميل الحلقة بنجاح');
    }
  } catch (e) {
    showToast('فشل تحميل الحلقة', 'error');
  }
}

async function deletePackage(epId) {
  if (!confirm('هل تريد حذف هذه الحلقة نهائياً؟')) return;
  try {
    await fetch('/api/packages/' + epId, { method: 'DELETE' });
    showToast('تم حذف الحلقة');
    loadPackages();
  } catch (e) {
    showToast('فشل حذف الحلقة', 'error');
  }
}

// ══════════════════════════════════════════════════════════════
// Keyboard Shortcuts
// ══════════════════════════════════════════════════════════════
document.addEventListener('keydown', (e) => {
  if (e.ctrlKey && e.key === 'Enter') produceEpisode();
});
