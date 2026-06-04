/* App — 全局状态、Tab 切换、初始化 */

let currentTab = 'chat';

function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelector(`[data-tab="${tab}"]`)?.classList.add('active');

  document.getElementById('chatPanel').classList.add('hidden');
  document.getElementById('mapPanel').classList.add('hidden');
  document.getElementById('knowledgePanel').classList.add('hidden');

  if (tab === 'chat') {
    document.getElementById('chatPanel').classList.remove('hidden');
  } else if (tab === 'map') {
    document.getElementById('mapPanel').classList.remove('hidden');
    setTimeout(() => { initMap(); }, 100);
    if (window._lastMapData) {
      setTimeout(() => { renderMap(window._lastMapData); }, 200);
    }
  } else if (tab === 'knowledge') {
    document.getElementById('knowledgePanel').classList.remove('hidden');
    refreshKnowledge();
  }
}

function updateNavBadge(text) {
  const badge = document.getElementById('navBadge');
  badge.textContent = text;
  if (text === '就绪') badge.style.color = '#34C759';
  else if (text === '规划中...') badge.style.color = '#FF9500';
  else if (text === '出错' || text === '离线') badge.style.color = '#FF3B30';
  else badge.style.color = '#8E8E93';
}

// 更新时间
function updateTime() {
  const now = new Date();
  document.getElementById('statusTime').textContent =
    now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
  updateTime();
  setInterval(updateTime, 30000);

  // 健康检查
  fetch(`${API_BASE}/api/health`)
    .then(r => r.json())
    .then(d => {
      if (d.status === 'ok') updateNavBadge('就绪');
      else updateNavBadge('异常');
    })
    .catch(() => updateNavBadge('离线'));

  refreshKnowledge();
});
