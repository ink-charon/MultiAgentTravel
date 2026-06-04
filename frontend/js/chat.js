/* Chat Panel — 消息渲染、发送、Markdown 显示 */

let isSending = false;

function addMessage(content, role) {
  const container = document.getElementById('chatMessages');
  // 移除欢迎卡片
  const welcome = container.querySelector('.welcome-card');
  if (welcome) welcome.remove();

  const row = document.createElement('div');
  row.className = `msg-row ${role}`;

  const avatar = document.createElement('div');
  avatar.className = `msg-avatar ${role}`;
  avatar.textContent = role === 'user' ? '👤' : '🤖';

  const bubble = document.createElement('div');
  bubble.className = `msg-bubble ${role}`;

  if (role === 'assistant') {
    bubble.innerHTML = renderMarkdown(content);
    // 路线图链接点击 → 切换到地图 Tab
    bubble.querySelectorAll('a[href*="/static/route"]').forEach(a => {
      a.addEventListener('click', e => {
        e.preventDefault();
        switchTab('map');
      });
    });
  } else {
    bubble.textContent = content;
  }

  row.appendChild(avatar);
  row.appendChild(bubble);
  container.appendChild(row);
  container.scrollTop = container.scrollHeight;
}

function showTyping() {
  const container = document.getElementById('chatMessages');
  const welcome = container.querySelector('.welcome-card');
  if (welcome) welcome.remove();

  const row = document.createElement('div');
  row.className = 'msg-row assistant';
  row.id = 'typingRow';

  const avatar = document.createElement('div');
  avatar.className = 'msg-avatar assistant';
  avatar.textContent = '🤖';

  const dots = document.createElement('div');
  dots.className = 'typing-dots';
  dots.innerHTML = '<span></span><span></span><span></span>';

  row.appendChild(avatar);
  row.appendChild(dots);
  container.appendChild(row);
  container.scrollTop = container.scrollHeight;
}

function hideTyping() {
  const row = document.getElementById('typingRow');
  if (row) row.remove();
}

function quickAsk(text) {
  document.getElementById('chatInput').value = text;
  sendMessage();
}

async function sendMessage() {
  if (isSending) return;
  const input = document.getElementById('chatInput');
  const text = input.value.trim();
  if (!text) return;

  isSending = true;
  document.getElementById('sendBtn').disabled = true;
  input.value = '';

  addMessage(text, 'user');
  addStatusMsg('🔍 正在检索知识库...');
  updateNavBadge('检索中');

  try {
    const resp = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
    });
    const data = await resp.json();
    hideTyping();
    removeLastStatus();

    if (data.error) {
      addMessage(`❌ ${data.error}`, 'assistant');
      updateNavBadge('出错');
    } else if (data.plan) {
      addMessage(data.plan, 'assistant');

      if (data.map_json && data.map_json.spots && data.map_json.spots.length > 0) {
        window._lastMapData = data.map_json;
        // 立即渲染地图（如果地图面板可见）
        if (!document.getElementById('mapPanel').classList.contains('hidden')) {
          initMap();
          renderMap(data.map_json);
        }
        addStatusMsg(`🗺️ 路线图已生成 (${data.map_json.spots.length} 个节点)，切换至地图面板查看`);
      }
      updateNavBadge('就绪');
    } else if (data.need_input) {
      addMessage('请补充更多信息：目的地和日期是必需的哦～', 'assistant');
      updateNavBadge('待补充');
    }

    if (typeof refreshKnowledge === 'function') refreshKnowledge();
  } catch (e) {
    hideTyping();
    removeLastStatus();
    addMessage(`网络错误: ${e.message}`, 'assistant');
    updateNavBadge('离线');
  }

  isSending = false;
  document.getElementById('sendBtn').disabled = false;
}

function addStatusMsg(msg) {
  const container = document.getElementById('chatMessages');
  const welcome = container.querySelector('.welcome-card');
  if (welcome) welcome.remove();

  const div = document.createElement('div');
  div.className = 'status-msg';
  div.id = 'lastStatus';
  div.style.cssText = 'text-align:center;padding:6px;font-size:13px;color:#8E8E93;';
  div.textContent = msg;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function removeLastStatus() {
  const el = document.getElementById('lastStatus');
  if (el) el.remove();
}

// Enter 发送
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('chatInput').addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
});
