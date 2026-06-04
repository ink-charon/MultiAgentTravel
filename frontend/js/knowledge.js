/* Knowledge Panel — 统计、清理、检索 */

async function refreshKnowledge() {
  try {
    const resp = await fetch(`${API_BASE}/api/knowledge/stats`);
    const data = await resp.json();
    document.getElementById('kbChatCount').textContent = data.chat_history || 0;
    document.getElementById('kbDocCount').textContent = data.travel_docs || 0;
  } catch (e) {
    // 静默失败
  }
}

async function cleanupKnowledge() {
  if (!confirm('确定要清理过期的知识库数据吗？\n\n系统会执行三级衰减策略：\n1. 衰减长期未访问的文档\n2. 压缩低分文档\n3. 删除过期压缩文档')) return;

  const btn = document.getElementById('cleanupBtn');
  btn.disabled = true;
  btn.textContent = '清理中...';

  try {
    const resp = await fetch(`${API_BASE}/api/knowledge/cleanup`, { method: 'POST' });
    const data = await resp.json();
    const s = data.stats || {};
    showToast(`清理完成：衰减${s.decayed || 0} 压缩${s.compressed || 0} 删除${s.deleted || 0}`);
    refreshKnowledge();
  } catch (e) {
    showToast('清理失败: ' + e.message);
  }

  btn.disabled = false;
  btn.textContent = '🗑️ 手动清理过期数据';
}

async function searchKnowledge() {
  const input = document.getElementById('kbSearchInput');
  const query = input.value.trim();
  if (!query) return;

  const container = document.getElementById('kbResults');
  container.innerHTML = '<p style="color:#8E8E93;text-align:center;padding:20px;">搜索中...</p>';

  try {
    const resp = await fetch(`${API_BASE}/api/knowledge/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, top_k: 5 }),
    });
    const data = await resp.json();
    const results = data.results || [];

    if (results.length === 0) {
      container.innerHTML = '<p style="color:#8E8E93;text-align:center;padding:20px;">没有找到相关结果</p>';
      return;
    }

    container.innerHTML = results.map((r, i) => `
      <div class="kb-result-item" style="cursor:pointer;" onclick="this.classList.toggle('expanded')">
        <div class="kb-result-score">相似度: ${(r.score || 0).toFixed(3)} | 点击展开</div>
        <div class="kb-result-text preview">${(r.content || '').substring(0, 150)}...</div>
        <div class="kb-result-text full" style="display:none;">${r.content || ''}</div>
      </div>
    `).join('');

    // 添加展开/收起样式
    document.querySelectorAll('.kb-result-item').forEach(item => {
      item.addEventListener('click', function() {
        const preview = this.querySelector('.preview');
        const full = this.querySelector('.full');
        const score = this.querySelector('.kb-result-score');
        if (full.style.display === 'none') {
          preview.style.display = 'none';
          full.style.display = 'block';
          score.textContent = score.textContent.replace('点击展开', '点击收起');
        } else {
          preview.style.display = 'block';
          full.style.display = 'none';
          score.textContent = score.textContent.replace('点击收起', '点击展开');
        }
      });
    });
  } catch (e) {
    container.innerHTML = `<p style="color:#FF3B30;text-align:center;padding:20px;">搜索失败: ${e.message}</p>`;
  }
}
